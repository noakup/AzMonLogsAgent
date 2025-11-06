"""Unified schema & table caching for Azure Log Analytics workspaces.

Responsibilities:
  - Single source of truth for: table list, manifest resource types, enrichment timestamps
  - Retrieve tables via official Log Analytics REST API (management endpoint) when possible
  - Fallback to union enumeration query if REST API unavailable or fails
  - TTL-based refresh to avoid repeated expensive calls

Environment variables:
  LOG_SUBSCRIPTION_ID   Subscription GUID for the workspace
  LOG_RESOURCE_GROUP    Resource group name containing the workspace
  LOG_WORKSPACE_NAME    Workspace resource name (NOT the workspace ID GUID)
  SCHEMA_TTL_MINUTES    (optional) TTL for cache refresh (default: 20)

Public API:
  SchemaManager.get().get_workspace_schema(workspace_id: str) -> dict
    Returns dict with keys: tables, count, manifest, retrieved_at, source, refreshed(bool)

NOTE: workspace_id (GUID used for query operations) is still required for union fallback queries.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover - requests may not yet be installed
    requests = None  # type: ignore

_credential_creation_lock = threading.Lock()
_azure_credential = None

_MANAGER_SINGLETON: "SchemaManager" | None = None

def _get_azure_credential():
    """Get or create shared Azure credential (thread-safe, created only once)."""
    global _azure_credential
    if _azure_credential is not None:
        return _azure_credential
    
    with _credential_creation_lock:
        # Double-check after acquiring lock
        if _azure_credential is not None:
            return _azure_credential
        
        if DefaultAzureCredential is None:
            return None
        
        print("[Credential] Creating Azure credential (will trigger az login if needed)...")
        _azure_credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
        print(f"[Credential] Credential created: {type(_azure_credential).__name__}")
        return _azure_credential

@dataclass
class WorkspaceSchemaCache:
    tables: List[Dict[str, Any]] = field(default_factory=list)
    manifest: Dict[str, Any] = field(default_factory=dict)
    retrieved_at: str = ""
    source: str = ""
    expires_at: float = 0.0

class SchemaManager:
    def __init__(self):
        self._cache: Dict[str, WorkspaceSchemaCache] = {}
        # Manifest cached globally; TTL aligned with table TTL
        self._manifest_cache: Dict[str, Any] = {}
        self._manifest_last_fetch: float = 0.0
        self._ttl_minutes = int(os.environ.get("SCHEMA_TTL_MINUTES", "20"))
        # Global refresh lock: ensures only one enumeration/refresh runs at a time.
        # This prevents duplicate union enumeration prints and redundant REST calls
        # when multiple threads request the schema simultaneously on cold start.
        self._refresh_lock = threading.Lock()

    @staticmethod
    def get() -> "SchemaManager":
        global _MANAGER_SINGLETON
        if _MANAGER_SINGLETON is None:
            _MANAGER_SINGLETON = SchemaManager()
        return _MANAGER_SINGLETON

    # ----------------- Public ----------------- #
    def get_workspace_schema(self, workspace_id: str) -> Dict[str, Any]:
        if not workspace_id:
            return {"error": "workspace_id required"}
        # Fast path without lock if cache is warm
        now = time.time()
        ttl_seconds = self._ttl_minutes * 60
        cache = self._cache.get(workspace_id)
        if cache and cache.expires_at > now:
            print(f"[SchemaManager] Cache hit workspace={workspace_id} age_ms={int((time.time()-cache.expires_at+ttl_seconds)*1000)}")
            self._ensure_manifest(ttl_seconds)
            return {
                "tables": cache.tables,
                "count": len(cache.tables),
                "manifest": self._manifest_cache,
                "retrieved_at": cache.retrieved_at,
                "source": cache.source,
                "refreshed": False,
            }

        # Slow path: acquire lock and re-check to avoid duplicate work
        with self._refresh_lock:
            now = time.time()
            cache = self._cache.get(workspace_id)
            if cache and cache.expires_at > now:
                print(f"[SchemaManager] Cache hit-after-lock workspace={workspace_id} age_ms={int((time.time()-cache.expires_at+ttl_seconds)*1000)}")
                self._ensure_manifest(ttl_seconds)
                return {
                    "tables": cache.tables,
                    "count": len(cache.tables),
                    "manifest": self._manifest_cache,
                    "retrieved_at": cache.retrieved_at,
                    "source": cache.source,
                    "refreshed": False,
                }
            # Retrieve fresh data (single thread only)
            t_refresh_start = time.time()
            print(f"[SchemaManager] Refresh start workspace={workspace_id} ttl_min={self._ttl_minutes}")
            t_retrieve_start = time.time()
            tables, source = self._retrieve_tables(workspace_id)
            retrieve_dur = time.time() - t_retrieve_start
            print(f"[SchemaManager] Phase retrieval_done workspace={workspace_id} source={source} duration_s={retrieve_dur:.3f} table_count={len(tables)}")
            # Backward-compatible log line for tests expecting legacy prefix
            print(f"[SchemaManager] Refresh retrieval_done workspace={workspace_id} source={source} duration_s={retrieve_dur:.3f}")
            t_manifest_start = time.time()
            self._ensure_manifest(ttl_seconds)
            manifest_dur = time.time() - t_manifest_start
            print(f"[SchemaManager] Phase manifest_done workspace={workspace_id} duration_s={manifest_dur:.3f} tables_index={len(self._manifest_cache.get('resource_type_tables', {}))}")
            # Manifest resource-type mapping
            table_resource_map: Dict[str, str] = {}
            manifest_path = os.path.join(os.path.dirname(__file__), 'NGSchema', 'LogAnalyticsWorkspace', 'WorkspaceManifest.manifest.json')
            if os.path.exists(manifest_path):
                try:
                    import json
                    with open(manifest_path, 'r', encoding='utf-8') as mf:
                        manifest = json.load(mf)
                    for tbl in manifest.get('tables', []):
                        tname = tbl.get('name')
                        dtype = tbl.get('dataTypeId', '')
                        cats = tbl.get('categories', [])
                        resource_type = dtype or (cats[0] if cats else '')
                        table_resource_map[tname] = resource_type
                except Exception as e:  # pragma: no cover
                    print(f"[Workspace Schema] Manifest parse error: {e}")
            # Enrichment
            t_enrich_start = time.time()
            enriched_tables: List[Dict[str, Any]] = []
            for tbl in tables:
                if isinstance(tbl, dict):
                    name_val = tbl.get("name") or tbl.get("tableName") or str(tbl)
                    metadata_copy = {k: v for k, v in tbl.items() if k != "name"}
                else:
                    name_val = str(tbl)
                    metadata_copy = {}
                if not name_val:
                    continue
                resource_type = table_resource_map.get(name_val, "Unknown")
                enriched_tables.append({"name": name_val, "resource_type": resource_type, **metadata_copy})
            enrich_dur = time.time() - t_enrich_start
            total_dur = time.time() - t_refresh_start
            print(f"[SchemaManager] Phase enrich_done workspace={workspace_id} duration_s={enrich_dur:.3f} enriched_count={len(enriched_tables)} total_refresh_s={total_dur:.3f}")
            print(f"creating WorkspaceSchemaCache")
            cache = WorkspaceSchemaCache(
                tables=enriched_tables,
                manifest=self._manifest_cache,
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                source=source,
                expires_at=time.time() + ttl_seconds,
            )
            print(f"WorkspaceSchemaCache created")
            print(f"[SchemaManager] debug print 1")
            self._cache[workspace_id] = cache
            print(f"[SchemaManager] debug print 2")
            return {
                "tables": cache.tables,
                "count": len(cache.tables),
                "manifest": self._manifest_cache,
                "retrieved_at": cache.retrieved_at,
                "source": cache.source,
                "refreshed": True,
            }

    # ----------------- Internal: Manifest ----------------- #
    def _ensure_manifest(self, ttl_seconds: int) -> None:
        now = time.time()
        if self._manifest_cache and (now - self._manifest_last_fetch) < ttl_seconds:
            return
        # Lightweight scan of NGSchema tree for resource type -> tables mapping
        base_dir = os.path.join(os.path.dirname(__file__), "NGSchema")
        mapping: Dict[str, List[str]] = {}
        if os.path.exists(base_dir):
            for root, dirs, files in os.walk(base_dir):  # type: ignore[attr-defined]
                for f in files:
                    if f.endswith(".manifest.json"):
                        # Could parse manifest here for future enrichment; keep simple for now
                        pass
                # Simple heuristic: tables might be described in *_kql_examples.md
                for f in files:
                    if f.endswith("_kql_examples.md"):
                        rtype = os.path.basename(root)
                        mapping.setdefault(rtype, []).append(f.replace("_kql_examples.md", ""))
        self._manifest_cache = {
            "resource_type_tables": mapping,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        self._manifest_last_fetch = now

    # ----------------- Internal: Table Retrieval ----------------- #
    def _retrieve_tables(self, workspace_id: str) -> tuple[list[Dict[str, Any]], str]:
        # Try REST API first
        rest_tables = self._rest_list_tables()
        if rest_tables:
            return rest_tables, "rest-api"
        # Fallback to union enumeration query
        union_tables = self._union_enumerate_tables(workspace_id)
        return union_tables, "union-query"

    def _rest_list_tables(self) -> list[Dict[str, Any]]:
        subscription_id = os.environ.get("LOG_SUBSCRIPTION_ID")
        resource_group = os.environ.get("LOG_RESOURCE_GROUP")
        workspace_name = os.environ.get("LOG_WORKSPACE_NAME")
        if not (subscription_id and resource_group and workspace_name):
            return []
        _azure_credential= _get_azure_credential()
        if requests is None or _azure_credential is None:
            return []
        try:
            t0 = time.time()
            print("[SchemaManager] REST list start")
            token = _azure_credential.get_token("https://management.azure.com/.default").token
            api_version = os.environ.get("LOG_TABLES_API_VERSION", "2022-10-01")
            url = (
                f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/"
                f"providers/Microsoft.OperationalInsights/workspaces/{workspace_name}/tables?api-version={api_version}"
            )
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"[SchemaManager] REST list tables failed: {resp.status_code} {resp.text[:200]}")
                return []
            data = resp.json()
            arr = data.get("value") or []
            tables: list[Dict[str, Any]] = []
            for item in arr:
                name = item.get("name") or item.get("properties", {}).get("name")
                props = item.get("properties", {})
                schema = props.get("schema", {})
                cols = []
                for col in schema.get("columns", []) or []:
                    cols.append({
                        "name": col.get("name"),
                        "type": col.get("type"),
                        "description": col.get("description")
                    })
                tables.append({
                    "name": name,
                    "columns": cols,
                    "retentionInDays": props.get("retentionInDays"),
                    "totalRetentionInDays": props.get("totalRetentionInDays"),
                })
            print(f"[SchemaManager] REST list done tables={len(tables)} duration_s={time.time()-t0:.3f}")
            return tables
        except Exception as e:  # pragma: no cover
            print(f"[SchemaManager] REST list tables exception: {e}")
            return []

    def _union_enumerate_tables(self, workspace_id: str) -> list[Dict[str, Any]]:
        _azure_credential= _get_azure_credential()
        if LogsQueryClient is None or _azure_credential is None:
            return []
        try:
            client = LogsQueryClient(_azure_credential)
            query = (
                "union withsource=__KQLAgentTableName__ * | summarize RowCount=count() by __KQLAgentTableName__ | "
                "sort by __KQLAgentTableName__ asc"
            )
            t0 = time.time()
            print(f"[SchemaManager] Union enumeration start workspace={workspace_id} timespan_days=7")
            resp = client.query_workspace(workspace_id=workspace_id, query=query, timespan=timedelta(days=7))
            tables: list[Dict[str, Any]] = []
            if hasattr(resp, "tables") and resp.tables:
                first = resp.tables[0]
                for row in getattr(first, "rows", []):
                    if row and row[0]:
                        tables.append({"name": str(row[0])})
            print(f"[SchemaManager] Union enumeration done tables={len(tables)} duration_s={time.time()-t0:.3f}")
            return tables
        except Exception as e:  # pragma: no cover
            print(f"[SchemaManager] Union enumeration error: {e}")
            return []

# Convenience functional wrapper
def get_workspace_schema(workspace_id: str) -> Dict[str, Any]:
    return SchemaManager.get().get_workspace_schema(workspace_id)
