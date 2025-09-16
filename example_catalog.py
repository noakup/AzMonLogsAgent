"""Example & schema catalog utilities.

Builds a catalog of example KQL queries (parsed from markdown assets) and
optionally enriches them with live column schema retrieved from Azure Monitor.

Lightweight parsing intentionally conservative: we extract candidate KQL lines
that look query-like (contain a pipe `|`) or code fenced blocks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import re

try:
    from azure.identity import DefaultAzureCredential  # type: ignore
    from azure.monitor.query import LogsQueryClient  # type: ignore
except Exception:  # pragma: no cover - optional during docs-only use
    DefaultAzureCredential = None  # type: ignore
    LogsQueryClient = None  # type: ignore


# Mapping of logical table names to example file & metadata
TABLE_EXAMPLE_MAP: Dict[str, Dict[str, str]] = {
    "AppRequests": {
        "file": "app_insights_capsule/kql_examples/app_requests_kql_examples.md",
        "category": "Application Insights",
        "description": "HTTP requests to your application",
    },
    "AppExceptions": {
        "file": "app_insights_capsule/kql_examples/app_exceptions_kql_examples.md",
        "category": "Application Insights",
        "description": "Exceptions thrown by your application",
    },
    "AppTraces": {
        "file": "app_insights_capsule/kql_examples/app_traces_kql_examples.md",
        "category": "Application Insights",
        "description": "Custom trace logs from your application",
    },
    "AppDependencies": {
        "file": "app_insights_capsule/kql_examples/app_dependencies_kql_examples.md",
        "category": "Application Insights",
        "description": "External dependencies called by your application",
    },
    "AppPageViews": {
        "file": "app_insights_capsule/kql_examples/app_page_views_kql_examples.md",
        "category": "Application Insights",
        "description": "Page views in your web application",
    },
    "AppCustomEvents": {
        "file": "app_insights_capsule/kql_examples/app_custom_events_kql_examples.md",
        "category": "Application Insights",
        "description": "Custom events tracked by your application",
    },
    "AppPerformanceCounters": {
        "file": "app_insights_capsule/kql_examples/app_performance_kql_examples.md",
        "category": "Application Insights",
        "description": "Performance counters and metrics",
    },
    "Usage": {
        "file": "usage_kql_examples.md",
        "category": "Usage Analytics",
        "description": "User behavior and usage patterns",
    },
}

KQL_LINE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*\|.*")


@dataclass
class ExampleEntry:
    kql: str
    title: Optional[str] = None


@dataclass
class TableCatalog:
    table: str
    description: str
    category: str
    columns: List[str] = field(default_factory=list)
    examples: List[ExampleEntry] = field(default_factory=list)


_CACHE: Dict[str, Dict[str, Any]] = {}
_SCHEMA_TTL = timedelta(minutes=15)


def _parse_examples(md_path: Path, limit: int = 8) -> List[ExampleEntry]:
    if not md_path.exists():
        return []
    text = md_path.read_text(encoding="utf-8", errors="ignore")

    examples: List[ExampleEntry] = []
    current_title: Optional[str] = None
    in_code = False
    code_buf: List[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        # Headings become potential titles
        if stripped.startswith("#"):
            if code_buf and in_code:
                # finalize existing code block
                joined = "\n".join(code_buf).strip()
                if "|" in joined:
                    examples.append(ExampleEntry(kql=joined, title=current_title))
                code_buf.clear()
            current_title = stripped.lstrip("# ")
            continue
        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                code_buf = []
            else:
                in_code = False
                joined = "\n".join(code_buf).strip()
                if "|" in joined:
                    examples.append(ExampleEntry(kql=joined, title=current_title))
                code_buf = []
            continue
        if in_code:
            code_buf.append(stripped)
            continue
        # Fallback: single-line candidate
        if KQL_LINE_RE.match(stripped):
            examples.append(ExampleEntry(kql=stripped, title=current_title))
        if len(examples) >= limit:
            break
    return examples[:limit]


def _get_logs_client() -> Optional[LogsQueryClient]:  # pragma: no cover
    if LogsQueryClient is None or DefaultAzureCredential is None:
        return None
    try:
        return LogsQueryClient(DefaultAzureCredential(exclude_interactive_browser_credential=False))
    except Exception:
        return None


def _fetch_table_columns(workspace_id: str, table: str, client: LogsQueryClient) -> List[str]:  # pragma: no cover network
    try:
        # Minimal schema hint: no row retrieval cost (should be metadata only)
        query = f"{table} | take 0"
        # azure-monitor-query requires a timespan; use 1h baseline
        from datetime import timedelta
        resp = client.query_workspace(workspace_id=workspace_id, query=query, timespan=timedelta(hours=1))
        if hasattr(resp, "tables") and resp.tables:  # type: ignore[attr-defined]
            tbl = resp.tables[0]
            cols = [getattr(c, "name", str(c)) for c in getattr(tbl, "columns", [])]
            # Filter obviously synthetic columns
            return [c for c in cols if c]
    except Exception:
        return []
    return []


def load_example_catalog(workspace_id: Optional[str], include_schema: bool = True, force: bool = False) -> Dict[str, Any]:
    """Return catalog structure.

    Caches per workspace id (schema may differ by workspace). If workspace is None
    only file examples are returned.
    """
    cache_key = workspace_id or "__no_workspace__"
    now = datetime.utcnow()
    cached = _CACHE.get(cache_key)
    if cached and not force:
        # Expire schema portion only; examples rarely change
        if include_schema:
            age = now - cached["generated"]
            if age < _SCHEMA_TTL:
                return cached["data"]
        else:
            return cached["data"]

    tables: Dict[str, TableCatalog] = {}
    for table, meta in TABLE_EXAMPLE_MAP.items():
        examples = _parse_examples(Path(meta["file"]))
        tables[table] = TableCatalog(
            table=table,
            description=meta["description"],
            category=meta["category"],
            examples=examples,
        )

    if include_schema and workspace_id:
        client = _get_logs_client()
        if client:
            for tname, tc in tables.items():
                cols = _fetch_table_columns(workspace_id, tname, client)
                if cols:
                    # Limit to first 40 columns to keep payload compact
                    tc.columns = cols[:40]

    catalog = {
        "workspace_id": workspace_id,
        "generated_at": now.isoformat() + "Z",
        "tables": {
            t.table: {
                "description": t.description,
                "category": t.category,
                "columns": t.columns,
                "examples": [
                    {"title": e.title, "kql": e.kql} for e in t.examples
                ],
            }
            for t in tables.values()
        },
    }

    _CACHE[cache_key] = {"generated": now, "data": catalog}
    return catalog


__all__ = ["load_example_catalog", "TABLE_EXAMPLE_MAP"]
