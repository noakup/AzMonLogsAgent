"""CSV Examples Loader for container-related KQL query examples.

Responsibilities:
  - Parse curated CSV files containing Prompt, Query columns
  - Map each query to one or more container-related tables based on filename and heuristic inspection
  - Provide caching (mtime-based) to avoid repeated parsing on frequent /api/workspace-schema calls
  - Return structure: { table_name: [ { name, code, source, file } ] }

CSV Files Supported (under containers_capsule/kql_examples/):
  * ContainerLogV2_kql_examples.csv    -> ContainerLogV2
  * KubePodInventory_kql_examples.csv  -> KubePodInventory
  * public_shots.csv                   -> heuristic multi-table mapping (queries may target several tables)

Dedup Strategy:
  - Within a single file: skip exact duplicate (normalized) code lines
  - Normalization removes leading/trailing whitespace and collapses internal Windows line endings to '\n'

Edge Cases Handled:
  - Quoted query cells that span multiple lines
  - CSV rows with missing columns are skipped
  - If a heuristic mapping finds multiple container tables in one query (e.g. join), assign to each
  - If no container table detected for public_shots.csv row, ignore (keeps result focused)

The loader purposely keeps logic lightweight (no external deps beyond stdlib).
"""
from __future__ import annotations

import csv
import os
import threading
from typing import Dict, List

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, dict] = {}
_MTIME_INDEX: dict[str, float] = {}

# File -> Primary table mapping (single table focus)
PRIMARY_FILE_TABLE_MAP = {
    'ContainerLogV2_kql_examples.csv': 'ContainerLogV2',
    'KubePodInventory_kql_examples.csv': 'KubePodInventory',
}

# Heuristic candidate tables for multi-table detection in public_shots.csv
PUBLIC_SHOTS_TABLE_CANDIDATES: list[str] = []  # no longer used (public_shots excluded from suggestions)

def _normalize_code(code: str) -> str:
    if not code:
        return ''
    # Normalize line endings and trim
    code = code.replace('\r\n', '\n').replace('\r', '\n').strip()
    # Collapse leading/trailing blank lines
    while '\n\n' in code:
        code = code.replace('\n\n', '\n')
    return code

def _public_shots_detect_tables(code: str) -> List[str]:
    """Deprecated: public_shots.csv no longer ingested for suggestions.
    Returns empty list always."""
    return []

def _parse_csv_file(path: str, primary_table: str | None, multi_detect: bool) -> Dict[str, List[dict]]:
    """Parse a CSV file returning table->list of query dicts.

    If primary_table is provided, all rows map to that table.
    If multi_detect is True, attempt heuristic detection per row (public_shots.csv scenario).
    """
    results: Dict[str, List[dict]] = {}
    if not os.path.exists(path):
        return results
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                prompt = row.get('Prompt')
                query = row.get('Query')
                if query is None:
                    # Some rows might have differently cased headers; attempt fallback
                    query = row.get('query') or ''
                query = _normalize_code(query)
                if not query:
                    continue
                # Determine tables
                tables: List[str]
                if primary_table:
                    tables = [primary_table]
                elif multi_detect:
                    tables = _public_shots_detect_tables(query)
                else:
                    tables = []
                if not tables:
                    continue  # skip entries with no detected tables for public shots
                # Build entry (Prompt becomes display name)
                name = prompt
                # Preserve both 'prompt' (original human-friendly text) and 'name' (legacy display fallback)
                entry = {
                    'prompt': prompt,  # may be empty string if not provided
                    'name': name,
                    'code': query,
                    'source': 'capsule-csv',
                    'file': os.path.basename(path)
                }
                for tbl in tables:
                    bucket = results.setdefault(tbl, [])
                    # Deduplicate within file by normalized code
                    if any(_normalize_code(e['code']) == query for e in bucket):
                        continue
                    bucket.append(entry)
    except Exception as e:  # noqa: BLE001
        print(f"[ExamplesLoader] Failed parsing {path}: {e}")
    return results

def _needs_reload(path: str) -> bool:
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return False
    cached_mtime = _MTIME_INDEX.get(path)
    return cached_mtime is None or mtime > cached_mtime

def load_capsule_csv_queries(base_dir: str | None = None, force: bool = False) -> Dict[str, List[dict]]:
    """Load (and cache) container capsule CSV queries.

    Parameters:
      base_dir: Optional base directory; defaults relative to this file.
      force: If True, bypass mtime check and reparse all files.

    Returns:
      dict mapping table_name -> list[ { name, code, source, file } ]
    """
    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(__file__), 'containers_capsule', 'kql_examples')

    with _CACHE_LOCK:
        # Determine files present
        if not os.path.isdir(base_dir):
            return {}
        aggregate: Dict[str, List[dict]] = {}
        for fname in os.listdir(base_dir):
            if not fname.endswith('.csv'):
                continue
            path = os.path.join(base_dir, fname)
            primary_table = PRIMARY_FILE_TABLE_MAP.get(fname)
            # public_shots.csv is intentionally ignored for suggestion ingestion
            if fname == 'public_shots.csv':
                continue
            multi_detect = False
            if not force and not _needs_reload(path):
                # Reuse cached fragment for this file
                fragment = _CACHE.get(path)
                if fragment:
                    for tbl, entries in fragment.items():
                        aggregate.setdefault(tbl, []).extend(entries)
                    continue
            fragment = _parse_csv_file(path, primary_table=primary_table, multi_detect=multi_detect)
            _CACHE[path] = fragment
            try:
                _MTIME_INDEX[path] = os.path.getmtime(path)
            except OSError:
                pass
            for tbl, entries in fragment.items():
                aggregate.setdefault(tbl, []).extend(entries)

        # Final dedup across all sources: if same normalized code appears multiple times for same table, keep first
        for tbl, entries in aggregate.items():
            deduped: List[dict] = []
            seen_codes = set()
            for e in entries:
                norm = _normalize_code(e['code'])
                if norm in seen_codes:
                    continue
                seen_codes.add(norm)
                deduped.append(e)
            aggregate[tbl] = deduped
        return aggregate

__all__ = ['load_capsule_csv_queries']
