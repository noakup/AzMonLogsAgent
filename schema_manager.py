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

# @dataclass
# class WorkspaceSchemaCache:
#     tables: List[Dict[str, Any]] = field(default_factory=list)
#     manifest: Dict[str, Any] = field(default_factory=dict)
#     retrieved_at: str = ""
#     source: str = ""
#     expires_at: float = 0.0

class SchemaManager:
    def __init__(self):
        #self._cache: Dict[str, WorkspaceSchemaCache] = {}
        # Manifest cached globally; now persistent & loaded explicitly (not tied to workspace TTL)
        self._manifest_cache: Dict[str, Any] = {}
        self._manifest_loaded: bool = False
        self._manifest_lock = threading.Lock()
        self._manifest_cache_file = os.environ.get("MANIFEST_CACHE_FILE", "manifest_cache.json")
        self._manifest_last_scan: float = 0.0
        # TTL disabled (stateless model) -> always refresh
        self._ttl_minutes = 0
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
        
        print(f"[SchemaManager] getting workspace schema for workspace={workspace_id}")
        # Fast path without lock if cache is warm
        # now = time.time()
        # ttl_seconds = self._ttl_minutes * 60
        # cache = self._cache.get(workspace_id)
        # Disabled fast-path cache reuse (stateless fetch always refreshes)

        # Slow path: acquire lock and re-check to avoid duplicate work
        with self._refresh_lock:
            now = time.time()
            # cache = self._cache.get(workspace_id)
            # Disabled second chance cache reuse
            # Retrieve fresh data (single thread only)
            t_refresh_start = time.time()
            print(f"[SchemaManager] Refresh start workspace={workspace_id} ttl_min={self._ttl_minutes}")
            t_retrieve_start = time.time()
            tables, source = self._retrieve_tables(workspace_id)
            retrieve_dur = time.time() - t_retrieve_start
            print(f"[SchemaManager] Phase retrieval_done workspace={workspace_id} source={source} duration_s={retrieve_dur:.3f} table_count={len(tables)}")
            # Backward-compatible log line for tests expecting legacy prefix
            print(f"[SchemaManager] Refresh retrieval_done workspace={workspace_id} source={source} duration_s={retrieve_dur:.3f}")
            # Manifest loading deferred; log current state summary only.
            print(f"[SchemaManager] Manifest deferred loaded={self._manifest_loaded} tables_index={len(self._manifest_cache.get('resource_type_tables', {}))}")
            # Manifest resource-type mapping (expanded): use cached manifest scan of ALL NGSchema manifests
            # self._manifest_cache now (after _ensure_manifest) may contain:
            #   resource_type_tables: { resource_type: [tableName] }
            #   table_resource_types: { tableName: [resource_type, ...] }
            table_resource_types: Dict[str, List[str]] = self._manifest_cache.get('table_resource_types', {}) if self._manifest_loaded else {}
            # For backward compatibility provide a simple primary map: choose the first manifest resource type if any
            table_primary_resource_type: Dict[str, str] = {
                t: (rts[0] if rts else 'Unknown') for t, rts in table_resource_types.items()
            }
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
                    print(f"[Workspace Schema] Skipping table with no name")
                    continue
                resource_types = table_resource_types.get(name_val, [])
                resource_type = table_primary_resource_type.get(name_val, "Unknown")
                enriched_entry = {"name": name_val, "resource_type": resource_type, **metadata_copy}
                if resource_types:
                    enriched_entry["manifest_resource_types"] = resource_types
                enriched_tables.append(enriched_entry)
            enrich_dur = time.time() - t_enrich_start
            total_dur = time.time() - t_refresh_start
            print(f"[SchemaManager] Phase enrich_done workspace={workspace_id} duration_s={enrich_dur:.3f} enriched_count={len(enriched_tables)} total_refresh_s={total_dur:.3f}")
            # Print out workspace tables (name + resource_type) after enrichment
            try:
                sample_list = [f"{t.get('name')}({t.get('resource_type')})" for t in enriched_tables]
                joined = ", ".join(sample_list)
                print(f"[WorkspaceTables] --------- workspace={workspace_id} total={len(enriched_tables)} tables={joined}")
            except Exception as tbl_print_exc:  # defensive; never block refresh
                print(f"[WorkspaceTables] --------- print_failed error={tbl_print_exc}")
            # print(f"creating WorkspaceSchemaCache")
            # cache = WorkspaceSchemaCache(
            #     tables=enriched_tables,
            #     manifest=self._manifest_cache if self._manifest_loaded else {},
            #     retrieved_at=datetime.now(timezone.utc).isoformat(),
            #     source=source,
            #     expires_at=time.time() + ttl_seconds,
            # )
            # print(f"WorkspaceSchemaCache created")
            # self._cache[workspace_id] = cache
            return {
                "tables": enriched_tables,
                "count": len(enriched_tables),
                "manifest": self._manifest_cache if self._manifest_loaded else {},
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "source": source,
                "refreshed": True,
            }

    # ----------------- Internal: Manifest (explicit load & refresh) ----------------- #
    def load_manifest(self, force: bool = False) -> None:
        with self._manifest_lock:
            if self._manifest_loaded and not force:
                return
            # Try loading persisted cache first (unless forcing)
            if not force and os.path.exists(self._manifest_cache_file):
                try:
                    import json
                    with open(self._manifest_cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if isinstance(data, dict) and data.get('resource_type_tables'):
                        self._manifest_cache = data
                        self._manifest_loaded = True
                        print(f"[Manifest] Loaded persisted manifest cache file={self._manifest_cache_file} resource_types={len(data.get('resource_type_tables', {}))}")
                        return
                except Exception as e:  # pragma: no cover
                    print(f"[Manifest] Failed loading persisted manifest: {e}")
            # Perform fresh scan
            print(f"[Manifest] Scanning NGSchema manifests force={force}")
            base_dir = os.path.join(os.path.dirname(__file__), "NGSchema")
            mapping: Dict[str, List[str]] = {}
            table_resource_types: Dict[str, List[str]] = {}
            manifests_scanned = 0
            if os.path.exists(base_dir):
                for root, dirs, files in os.walk(base_dir):  # type: ignore[attr-defined]
                    for f in files:
                        if f.endswith('.manifest.json'):
                            manifest_path = os.path.join(root, f)
                            try:
                                import json
                                with open(manifest_path, 'r', encoding='utf-8') as mf:
                                    mdata = json.load(mf)
                                rtype = mdata.get('type') or os.path.basename(root)
                                tbls = []
                                for key in ('tables', 'Tables', 'tableList', 'relatedTables'):
                                    val = mdata.get(key)
                                    if isinstance(val, list):
                                        for t in val:
                                            if isinstance(t, dict):
                                                tname = t.get('name') or t.get('tableName')
                                            elif isinstance(t, str):
                                                tname = t
                                            else:
                                                tname = None
                                            if tname:
                                                tbls.append(tname)
                                def _walk(obj):
                                    if isinstance(obj, dict):
                                        for k, v in obj.items():
                                            if k.lower() == 'tables' and isinstance(v, list):
                                                for t in v:
                                                    if isinstance(t, dict):
                                                        nm = t.get('name') or t.get('tableName')
                                                    elif isinstance(t, str):
                                                        nm = t
                                                    else:
                                                        nm = None
                                                    if nm:
                                                        tbls.append(nm)
                                            _walk(v)
                                    elif isinstance(obj, list):
                                        for it in obj:
                                            _walk(it)
                                _walk(mdata)
                                if isinstance(rtype, str) and '/' in rtype:
                                    mapping.setdefault(rtype, [])
                                    for tname in sorted(set(tbls)):
                                        if tname not in mapping[rtype]:
                                            mapping[rtype].append(tname)
                                        table_resource_types.setdefault(tname, []).append(rtype)
                                manifests_scanned += 1
                            except Exception as e:
                                print(f"[Manifest] Parse error {manifest_path}: {e}")
                    # Example-based heuristic still supported
                    for f in files:
                        if f.endswith('_kql_examples.md'):
                            rtype = os.path.basename(root)
                            mapping.setdefault(rtype, []).append(f.replace('_kql_examples.md', ''))
            for rt, lst in mapping.items():
                mapping[rt] = sorted(set(lst))
            for t, lst in table_resource_types.items():
                table_resource_types[t] = sorted(set(lst))
            self._manifest_cache = {
                'resource_type_tables': mapping,
                'table_resource_types': table_resource_types,
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'manifests_scanned': manifests_scanned
            }
            self._manifest_loaded = True
            self._manifest_last_scan = time.time()
            # Persist
            try:
                import json
                with open(self._manifest_cache_file, 'w', encoding='utf-8') as pf:
                    json.dump(self._manifest_cache, pf)
                print(f"[Manifest] Persisted manifest cache file={self._manifest_cache_file} size_rt={len(mapping)} tables={len(table_resource_types)}")
            except Exception as e:  # pragma: no cover
                print(f"[Manifest] Persist failed: {e}")

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
