#!/usr/bin/env python3
"""
Web Interface for Natural Language KQL Agent
A Flask web application that provides a user-friendly interface for the KQL agent
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import asyncio
import time  # needed for docs enrichment timing budget
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
import threading
import re
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the KQL agent
from logs_agent import KQLAgent
try:
    from azure.identity import DefaultAzureCredential  # type: ignore
    from azure.monitor.query import LogsQueryClient  # type: ignore
except Exception:  # Library might not be installed yet; schema fetch will be skipped
    DefaultAzureCredential = None  # type: ignore
    LogsQueryClient = None  # type: ignore
from example_catalog import load_example_catalog
from schema_manager import get_workspace_schema
from examples_loader import load_capsule_csv_queries  # CSV capsule queries


app = Flask(__name__)
# Ensure workspace_id is defined before any early cache load attempts to avoid NameError
workspace_id = None

# Legacy compatibility globals (removed caching logic, retained empty structures for tests/UI expecting them)
_workspace_schema_cache = {}
_workspace_schema_refresh_flags = {}
_workspace_schema_refresh_errors = {}

# Workspace schema cache removed; all schema requests now perform a fresh fetch via get_workspace_schema().

# Optional simple persistence for workspace schema across debug reloads.
SCHEMA_CACHE_FILE = None  # caching disabled
def _persist_workspace_cache():
    return  # no-op (caching disabled)

def _load_workspace_cache():
    return  # no-op (caching disabled)

# Attempt load at module import (only effective on debug reloads)
_load_workspace_cache()

# Docs enrichment tuning (env configurable to avoid UI stalls from slow/blocked Microsoft Docs fetches)
DOCS_ENRICH_DISABLE = bool(os.environ.get("DOCS_ENRICH_DISABLE"))  # "1" or any non-empty string disables
WORKSPACE_SCHEMA_SYNC_FETCH = os.environ.get("WORKSPACE_SCHEMA_SYNC_FETCH", "0") == "1"  # allow reverting to old synchronous behavior
DOCS_META_MAX_SECONDS = float(os.environ.get("DOCS_META_MAX_SECONDS", "10"))  # cumulative time budget for metadata enrichment (raised from 4s to 10s)
# Removed legacy refresh flags and lock (stateless schema fetch)
DOCS_ENRICH_MAX_TABLES = int(os.environ.get("DOCS_ENRICH_MAX_TABLES", "8"))  # cap number of unmatched tables to enrich per request
DOCS_ENRICH_MAX_SECONDS = float(os.environ.get("DOCS_ENRICH_MAX_SECONDS", "5"))  # cumulative time budget per request
DOCS_ENRICH_COLUMN_FETCH = bool(os.environ.get("DOCS_ENRICH_COLUMN_FETCH", "1"))  # allow disabling column scraping (heavier)


# Generic examples fallback
GENERIC_EXAMPLES = {
    'Application Insights': [
        'Show me failed requests from the last hour',
        'Show me recent exceptions',
        'Show me recent trace logs',
        'Show me dependency failures',
        'Show me page views from the last hour',
        'Show me performance counters',
    ],
    'Usage Analytics': [
        'Show me user activity patterns',
        'Get daily active users',
        'Show me usage statistics by region',
        'Show me usage trends over time',
    ],
}

# New endpoint: Suggest example queries based on resource type (dynamic mapping)
@app.route('/api/resource-examples', methods=['POST'])
def resource_examples():
    """Suggest example queries for a given resource type.

    Strategy:
      1. Attempt to locate an *_kql_examples.md file matching the resource_type inside NGSchema.
      2. Fallback to app_insights_capsule/kql_examples directory.
      3. If none found, return generic examples if available.
    """
    try:
        import glob
        data = request.get_json(silent=True) or {}
        resource_type = data.get('resource_type', '').strip()
        if not resource_type:
            return jsonify({'success': False, 'error': 'Resource type is required'})

        def _normalize(s: str) -> str:
            return s.replace(' ', '').lower()

        example_file = None
        ngschema_dir = os.path.join(os.path.dirname(__file__), 'NGSchema')
        if os.path.exists(ngschema_dir):
            for root, dirs, _ in os.walk(ngschema_dir):
                for d in dirs:
                    if _normalize(d) == _normalize(resource_type):
                        kql_files = glob.glob(os.path.join(root, d, '*_kql_examples.md'))
                        if kql_files:
                            example_file = kql_files[0]
                            break
                if example_file:
                    break
        if not example_file:
            capsule_dir = os.path.join(os.path.dirname(__file__), 'app_insights_capsule', 'kql_examples')
            if os.path.exists(capsule_dir):
                kql_files = glob.glob(os.path.join(capsule_dir, '*_kql_examples.md'))
                for f in kql_files:
                    base = os.path.basename(f).lower()
                    if _normalize(resource_type) in base:
                        example_file = f
                        break

        examples = []
        if example_file:
            try:
                with open(example_file, 'r', encoding='utf-8') as ef:
                    content = ef.read()
                # Simple heuristic: lines starting with "#" are titles, code blocks are fenced ``` lines
                current_title = None
                current_code = []
                for line in content.splitlines():
                    if line.startswith('#'):
                        if current_title and current_code:
                            examples.append({'title': current_title.strip('# ').strip(), 'query': '\n'.join(current_code).strip()})
                        current_title = line
                        current_code = []
                    elif line.startswith('```'):
                        # Toggle collection; naive approach: start capturing after opening fence until closing
                        if current_code and current_code[-1] == '__END_FENCE__':
                            current_code.pop()  # remove marker
                        else:
                            current_code.append('__END_FENCE__')
                    else:
                        if current_title:
                            current_code.append(line)
                if current_title and current_code:
                    if current_code and current_code[-1] == '__END_FENCE__':
                        current_code.pop()
                    examples.append({'title': current_title.strip('# ').strip(), 'query': '\n'.join(current_code).strip()})
            except Exception as ex:  # noqa: BLE001
                print(f"[Examples] Failed parsing examples file {example_file}: {ex}")

        # Fallback generic examples
        if not examples:
            generic = GENERIC_EXAMPLES.get(resource_type) or GENERIC_EXAMPLES.get('Application Insights') or []
            examples = [{'title': f'Example {i+1}', 'query': q} for i, q in enumerate(generic)]

        return jsonify({'success': True, 'resource_type': resource_type, 'example_file': example_file, 'examples': examples})
    except Exception as e:  # noqa: BLE001
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/fetch-workspace-schema', methods=['GET', 'POST'])
def fetch_workspace_schema():
    """Direct, stateless workspace schema retrieval (lightweight summary).

    Returns JSON:
      success, workspace_id, table_count, retrieved_at, source, error (optional)
    """
    global workspace_id
    if not workspace_id:
        return jsonify({'success': False, 'workspace_id': None, 'table_count': 0, 'error': 'Workspace not initialized'}), 200
    try:
        result = get_workspace_schema(workspace_id)
        if result.get('error'):
            return jsonify({'success': False, 'workspace_id': workspace_id, 'table_count': 0, 'error': result.get('error')}), 200
        return jsonify({
            'success': True,
            'workspace_id': workspace_id,
            'table_count': len(result.get('tables', [])),
            'retrieved_at': result.get('retrieved_at'),
            'source': result.get('source')
        })
    except Exception as e:  # noqa: BLE001
        return jsonify({'success': False, 'workspace_id': workspace_id, 'table_count': 0, 'error': str(e)}), 200

# Global agent instance
agent = None
_workspace_resource_types_cache = {}  # deprecated: manifest data now supplied via SchemaManager
_workspace_queries_cache = {}
_ms_docs_table_resource_type_cache = {}  # table_name -> resource_type | 'unknown resource type'
_ms_docs_table_full_cache = {}           # table_name -> { description, columns:[{name,type,description}], fetched_at }
_ms_docs_table_queries_cache = {}        # table_name -> [ { name, description } ]

# Shared Azure credential (created once to avoid multiple az login prompts)
_azure_credential = None
_credential_creation_lock = threading.Lock()

# Static fallback map for common Application Insights (Azure Monitor 'classic' AI) derived tables
_STATIC_FALLBACK_TABLE_RESOURCE_TYPES = {
    # App Insights standard tables
    'AppRequests': 'microsoft.insights/components',
    'AppDependencies': 'microsoft.insights/components',
    'AppTraces': 'microsoft.insights/components',
    'AppExceptions': 'microsoft.insights/components',
    'AppAvailabilityResults': 'microsoft.insights/components',
    'AppPageViews': 'microsoft.insights/components',
    'AppPerformanceCounters': 'microsoft.insights/components',
    'AppBrowserTimings': 'microsoft.insights/components',
    'AppCustomEvents': 'microsoft.insights/components',
    'AppCustomMetrics': 'microsoft.insights/components',
    'AppMetric': 'microsoft.insights/components',
    'AppMetrics': 'microsoft.insights/components',
    'AppSessions': 'microsoft.insights/components',
    'AppEvents': 'microsoft.insights/components',
    'AppPageViewPerformance': 'microsoft.insights/components'
}


def _lookup_table_resource_type_doc(table_name: str, timeout: float = 4.0) -> str:
    """Best-effort lookup of resource type for a given table via public Microsoft Docs.

    Tries https://learn.microsoft.com/en-us/azure/azure-monitor/reference/tables/{table}
    Table pages typically include a "Resource type:" label followed by a provider/resourceType value.
    Returns discovered resource type string or 'unknown resource type'.
    Caches results per process. Keeps failures cached to avoid repeated outbound calls.
    """
    if DOCS_ENRICH_DISABLE:
        return 'unknown resource type'
    if not table_name:
        return 'unknown resource type'
    cache_key = table_name
    # Static fallback first (case-insensitive)
    for k, v in _STATIC_FALLBACK_TABLE_RESOURCE_TYPES.items():
        if k.lower() == table_name.lower():
            return v
    if cache_key in _ms_docs_table_resource_type_cache:
        return _ms_docs_table_resource_type_cache[cache_key]
    slug = table_name.lower()
    url = f"https://learn.microsoft.com/en-us/azure/azure-monitor/reference/tables/{slug}"
    try:
        req = urlrequest.Request(url, headers={
            'User-Agent': 'AzMonLogsAgent/1.0 (+https://github.com/noakup)'
        })
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                _ms_docs_table_resource_type_cache[cache_key] = 'unknown resource type'
                return 'unknown resource type'
            content = resp.read().decode('utf-8', errors='ignore')
            # Heuristic: look for 'Resource type' line then capture next provider/resourceType token
            # Common patterns: <strong>Resource type:</strong> Microsoft.Insights/components
            # or visible text 'Resource type: microsoft.operationalinsights/workspaces'
            m = re.search(r'Resource\s*type:?\s*</?strong>[^A-Za-z0-9/]*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)', content, re.IGNORECASE)
            if not m:
                # Fallback: search anywhere for microsoft.<provider>/<resourcetype> preceded by 'Resource type'
                m = re.search(r'Resource\s*type:?[^\n]{0,120}?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)', content, re.IGNORECASE)
            if m:
                rtype = m.group(1)
                # Normalize provider casing (Microsoft.*) if missing capital M
                if rtype.lower().startswith('microsoft.') and not rtype.startswith('Microsoft.'):
                    rtype = 'Microsoft.' + rtype.split('.', 1)[1]
                _ms_docs_table_resource_type_cache[cache_key] = rtype
                return rtype
    except (HTTPError, URLError, TimeoutError, ValueError) as e:  # noqa: PERF203 - broad acceptable for network
        print(f"[Docs Enrichment] Failed to fetch {url}: {e}")
    except Exception as e:  # noqa: BLE001
        print(f"[Docs Enrichment] Unexpected error for {url}: {e}")
    _ms_docs_table_resource_type_cache[cache_key] = 'unknown resource type'
    return 'unknown resource type'


def _fetch_table_docs_full(table_name: str, timeout: float = 6.0) -> dict:
    """Fetch table description and columns from Microsoft Docs table reference page.

    Caches results in _ms_docs_table_full_cache. Returns a dict:
      { description:str, columns:[{name,type,description}], fetched_at:str }
    """
    if DOCS_ENRICH_DISABLE:
        return {}
    if not table_name:
        return {}
    if table_name in _ms_docs_table_full_cache:
        return _ms_docs_table_full_cache[table_name]
    slug = table_name.lower()
    url = f"https://learn.microsoft.com/azure/azure-monitor/reference/tables/{slug}"
    try:
        req = urlrequest.Request(url, headers={'User-Agent': 'AzMonLogsAgent/1.0 (+https://github.com/noakup)'})
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return {}
            html = resp.read().decode('utf-8', errors='ignore')
        # Very lightweight parsing heuristics (avoid full HTML parser to keep deps minimal)
        # Description: first <p> after <h1> or meta description
        desc_match = re.search(r'<h1[^>]*>.*?</h1>\s*<p>(.*?)</p>', html, re.IGNORECASE | re.DOTALL)
        description = ''
        if desc_match:
            description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
        # Columns: look for markdown-like table rendered as HTML <table> with column headers Name, Type
        columns = []
        table_sections = re.findall(r'<table.*?>.*?</table>', html, re.IGNORECASE | re.DOTALL)
        if DOCS_ENRICH_COLUMN_FETCH:
            for sect in table_sections:
                if re.search(r'<th[^>]*>\s*Name\s*</th>', sect, re.IGNORECASE) and re.search(r'<th[^>]*>\s*Type\s*</th>', sect, re.IGNORECASE):
                    # Extract rows
                    rows = re.findall(r'<tr>(.*?)</tr>', sect, re.IGNORECASE | re.DOTALL)
                    for r in rows[1:]:  # skip header
                        cols = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.IGNORECASE | re.DOTALL)
                        if len(cols) >= 2:
                            cname = re.sub(r'<[^>]+>', '', cols[0]).strip()
                            ctype = re.sub(r'<[^>]+>', '', cols[1]).strip()
                            cdesc = ''
                            if len(cols) >= 3:
                                cdesc = re.sub(r'<[^>]+>', '', cols[2]).strip()
                            if cname:
                                columns.append({'name': cname, 'type': ctype, 'description': cdesc})
                    if columns:
                        break
        record = {
            'description': description,
            'columns': columns,
            'fetched_at': datetime.now(timezone.utc).isoformat()
        }
        _ms_docs_table_full_cache[table_name] = record
        return record
    except Exception as e:  # noqa: BLE001
        print(f"[Docs Enrichment] Failed full table fetch for {table_name}: {e}")
        return {}


def _fetch_table_docs_queries(table_name: str, timeout: float = 6.0) -> list:
    """Fetch example queries for a table from Microsoft Docs queries page.

    Heuristic extraction pattern:
      <h3>Query Title</h3> (sometimes h2)
      <p>Short description sentence.</p>
      <pre><code class="lang-kusto">KQL HERE</code></pre>

    Returns list of { name, description, code, source='docs' }.
    Caches results per table.
    """
    if DOCS_ENRICH_DISABLE:
        return []
    if not table_name:
        return []
    if table_name in _ms_docs_table_queries_cache:
        return _ms_docs_table_queries_cache[table_name]
    slug = table_name.lower()
    url = f"https://learn.microsoft.com/azure/azure-monitor/reference/queries/{slug}"
    try:
        req = urlrequest.Request(url, headers={'User-Agent': 'AzMonLogsAgent/1.0 (+https://github.com/noakup)'})
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return []
            html_text = resp.read().decode('utf-8', errors='ignore')
        import html as html_lib  # local import to avoid global namespace clutter
        queries = []
        # Find all h2/h3 headings as potential query titles
        heading_iter = list(re.finditer(r'<h[23][^>]*>(.*?)</h[23]>', html_text, re.IGNORECASE | re.DOTALL))
        for idx, match in enumerate(heading_iter):
            raw_title = match.group(1)
            title_clean = re.sub(r'<[^>]+>', '', raw_title).strip()
            if not title_clean:
                continue
            # Slice segment until next heading or limited length
            start = match.end()
            end = heading_iter[idx + 1].start() if idx + 1 < len(heading_iter) else len(html_text)
            segment = html_text[start:end]
            # Description: first <p>...</p>
            desc_match = re.search(r'<p>(.*?)</p>', segment, re.IGNORECASE | re.DOTALL)
            desc_clean = ''
            if desc_match:
                desc_clean = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
            # Code: prefer <pre><code ...>...</code></pre>
            code_match = re.search(r'<pre[^>]*>\s*<code[^>]*>([\s\S]*?)</code>\s*</pre>', segment, re.IGNORECASE)
            if not code_match:
                # fallback single code tag
                code_match = re.search(r'<code[^>]*>([\s\S]*?)</code>', segment, re.IGNORECASE)
            code_text = ''
            if code_match:
                code_text = code_match.group(1)
                # Remove HTML tags inside code (rare) and unescape entities
                code_text = re.sub(r'<[^>]+>', '', code_text)
                code_text = html_lib.unescape(code_text).strip()
            # Only record if we have at least a code block (to ensure it's an actual query example)
            if code_text:
                queries.append({
                    'name': title_clean,
                    'description': desc_clean,
                    'code': code_text,
                    'source': 'docs'
                })
        _ms_docs_table_queries_cache[table_name] = queries
        return queries
    except Exception as e:  # noqa: BLE001
        print(f"[Docs Enrichment] Failed table queries fetch for {table_name}: {e}")
        return []


    # Legacy cache-based workspace schema block removed.

    for entry in workspace_tables:
        tname = entry.get('name')
        ws_rt = entry.get('resource_type') or 'Unknown'
        manifest_rts = manifest_tables_index.get(tname, [])
        in_manifest = bool(manifest_rts)
        if in_manifest:
            matched += 1
            # Build subset mapping: include table under each manifest resource type it appears in
            for mrt in manifest_rts:
                resource_type_subset.setdefault(mrt, []).append(tname)
                provider = mrt.split('/')[0]
                provider_summary.setdefault(provider, {'tables': 0, 'resource_types': set()})
                provider_summary[provider]['tables'] += 1
                provider_summary[provider]['resource_types'].add(mrt)
        else:
            unmatched.append(tname)
        enriched.append({
            'name': tname,
            'workspace_resource_type': ws_rt,
            'in_manifest': in_manifest,
            'manifest_resource_type': manifest_rts[0] if manifest_rts else None,
            'manifest_resource_types': manifest_rts,
            'provider': (manifest_rts[0].split('/')[0] if manifest_rts else None)
        })

    # NOTE: Synthetic fallback grouping for unmatched tables removed per user request.
    # Unmatched tables will no longer be assigned to a synthetic resource type; they remain
    # visible only in the 'unmatched_tables' list. This keeps the UI honest about mapping
    # completeness and allows the frontend to surface an explicit error state when
    # workspace tables exist but no resource types are mapped.

    # Enrich unmatched tables using Microsoft Docs table pages (best-effort)
    doc_enriched = 0
    # if unmatched and not DOCS_ENRICH_DISABLE:
        # # Bound number of tables & cumulative time to keep endpoint responsive
        # t_docs_start = time.time()
        # for table in unmatched[:DOCS_ENRICH_MAX_TABLES]:
        #     doc_rtype = _lookup_table_resource_type_doc(table)
        #     # Normalize to lowercase provider/resource type to be consistent (as per docs examples)
        #     if doc_rtype != 'unknown resource type':
        #         doc_rtype = doc_rtype.strip()
        #         # Ensure pattern provider/resourceType; if uppercase Microsoft.* keep as-is else lowercase
        #         if '/' in doc_rtype:
        #             parts = doc_rtype.split('/')
        #             if len(parts) == 2:
        #                 # Keep original provider case if startswith Microsoft., else lowercase both
        #                 if not parts[0].startswith('Microsoft.'):
        #                     doc_rtype = f"{parts[0].lower()}/{parts[1].lower()}"
        #         else:
        #             # Not a recognized pattern, mark unknown
        #             doc_rtype = 'unknown resource type'
        #     # Update enriched list entry
        #     for e in enriched:
        #         if e['name'] == table:
        #             e['doc_resource_type'] = doc_rtype
        #             if doc_rtype != 'unknown resource type' and not e.get('provider'):
        #                 e['provider'] = doc_rtype.split('/')[0]
        #             break
        #     # If a resource type was found (not unknown), include in subset; otherwise bucket under 'unknown resource type'
        #     target_rtype = doc_rtype if doc_rtype != 'unknown resource type' else 'unknown resource type'
        #     if target_rtype not in resource_type_subset:
        #         resource_type_subset[target_rtype] = []
        #     resource_type_subset[target_rtype].append(table)
        #     if target_rtype != 'unknown resource type':
        #         provider = target_rtype.split('/')[0]
        #     else:
        #         provider = 'unknown'
        #     provider_summary.setdefault(provider, {'tables': 0, 'resource_types': set()})
        #     provider_summary[provider]['tables'] += 1
        #     if target_rtype != 'unknown resource type':
        #         provider_summary[provider]['resource_types'].add(target_rtype)
        #     doc_enriched += 1
        #     if (time.time() - t_docs_start) > DOCS_ENRICH_MAX_SECONDS:
        #         print(f"[Docs Enrichment] Cumulative time budget exceeded ({DOCS_ENRICH_MAX_SECONDS}s); skipping remaining tables.")
        #         break
    

    # Normalize provider summary sets to counts (after enrichment)
    provider_summary_out = {
        prov: {'tables': info['tables'], 'resource_types': len(info['resource_types']) if isinstance(info['resource_types'], set) else info['resource_types']}
        for prov, info in provider_summary.items()
    }

    # Build per-table queries mapping (manifest first, docs fallback)
    manifest_table_queries = manifest_data.get('table_queries', {}) or {}
    capsule_csv_queries = {}
    try:
        capsule_csv_queries = load_capsule_csv_queries()
        # Debug summary of capsule CSV ingestion
        total_capsule_query_count = sum(len(v) for v in capsule_csv_queries.values())
        print(f"[Capsule CSV] tables={list(capsule_csv_queries.keys())} total_queries={total_capsule_query_count}")
        for tbl, qlist in capsule_csv_queries.items():
            preview = [q.get('name','<noname>')[:60] for q in qlist[:5]]
            print(f"[Capsule CSV] table={tbl} count={len(qlist)} preview={preview}")
    except Exception as e:  # noqa: BLE001
        print(f"[Workspace Schema] Capsule CSV ingestion error: {e}")

    def _normalize_code(code: str) -> str:
        if not isinstance(code, str):
            return ''
        c = code.replace('\r\n', '\n').replace('\r', '\n').strip()
        while '\n\n' in c:
            c = c.replace('\n\n', '\n')
        return c

    workspace_table_queries = {}
    tables_with_manifest_queries = 0
    tables_with_capsule_queries = 0
    tables_with_docs_queries = 0
    for tinfo in enriched:
        tname = tinfo['name']
        combined: list[dict] = []
        # 1. Manifest queries (highest precedence)
        m_list = manifest_table_queries.get(tname) or []
        if m_list:
            for q in m_list:
                # Ensure uniform shape; manifest queries already include name/description
                if q.get('name'):
                    combined.append({
                        'name': q.get('name'),
                        'description': q.get('description'),
                        'code': q.get('code') if q.get('code') else None,
                        'source': 'manifest'
                    })
            tables_with_manifest_queries += 1
        # 2. Capsule CSV queries (second precedence)
        c_list = capsule_csv_queries.get(tname) or []
        if c_list:
            for q in c_list:
                if q.get('name') and q.get('code'):
                    norm_code = _normalize_code(q.get('code'))
                    if not any(_normalize_code(existing.get('code')) == norm_code for existing in combined if existing.get('code')):
                        combined.append({
                            'name': q.get('name'),
                            'description': q.get('description') or '',
                            'code': q.get('code'),
                            'source': q.get('source') or 'capsule-csv',
                            'file': q.get('file')
                        })
            tables_with_capsule_queries += 1
        # 3. Docs queries (fallback only adds if new code)
        if not DOCS_ENRICH_DISABLE:
            docs_q = _fetch_table_docs_queries(tname)
            if docs_q:
                added_docs = 0
                for q in docs_q:
                    if q.get('name') and q.get('code'):
                        norm_code = _normalize_code(q.get('code'))
                        if not any(_normalize_code(existing.get('code')) == norm_code for existing in combined if existing.get('code')):
                            combined.append({
                                'name': q.get('name'),
                                'description': q.get('description'),
                                'code': q.get('code'),
                                'source': 'docs'
                            })
                            added_docs += 1
                if added_docs:
                    tables_with_docs_queries += 1
        if combined:
            workspace_table_queries[tname] = combined
            # Debug per-table merged result
            src_counts = {
                'manifest': sum(1 for q in combined if q.get('source') == 'manifest'),
                'capsule-csv': sum(1 for q in combined if q.get('source') == 'capsule-csv'),
                'docs': sum(1 for q in combined if q.get('source') == 'docs')
            }
            print(f"[QueryMerge] table={tname} total={len(combined)} breakdown={src_counts}")
        else:
            print(f"[QueryMerge] table={tname} no queries merged (manifest={len(m_list)} capsule={len(capsule_csv_queries.get(tname, []))})")

    # Final debug: any query objects missing required fields
    missing_fields_total = 0
    for tbl, qlist in workspace_table_queries.items():
        for q in qlist:
            if not q.get('name') or not q.get('code'):
                print(f"[QueryMerge][WARN] table={tbl} query missing name/code -> {q}")
                missing_fields_total += 1
    if missing_fields_total:
        print(f"[QueryMerge][WARN] total_incomplete_queries={missing_fields_total}")
    else:
        print("[QueryMerge] all merged queries have name & code")

    response = {
        'success': True,
        'status': 'ready',
        'workspace_id': workspace_id,
        'counts': {
            'workspace_tables': len(workspace_tables),
            'manifest_tables': sum(len(v) for v in manifest_data.get('resource_type_tables', {}).values()),
            'matched_tables': matched,
            'unmatched_tables': len(unmatched),
            'resource_types_with_data': len(resource_type_subset)
        },
        'tables': enriched,
        'resource_type_tables': resource_type_subset,
        'providers': provider_summary_out,
        'unmatched_tables': unmatched,
        'retrieved_at': ws_cache.get('retrieved_at'),
        'doc_enrichment': {
            'performed': bool(unmatched) and not DOCS_ENRICH_DISABLE,
            'enriched_tables': doc_enriched,
            'cache_size': len(_ms_docs_table_resource_type_cache),
            'disabled': DOCS_ENRICH_DISABLE,
            'limits': {
                'max_tables': DOCS_ENRICH_MAX_TABLES,
                'max_seconds': DOCS_ENRICH_MAX_SECONDS,
                'column_fetch': DOCS_ENRICH_COLUMN_FETCH
            }
        },
        # Workspace scoped table metadata (manifest first, docs fallback)
        'table_metadata': {},
        'table_queries': workspace_table_queries,
        'query_enrichment': {
            'tables_with_manifest_queries': tables_with_manifest_queries,
            'tables_with_capsule_csv_queries': tables_with_capsule_queries,
            'tables_with_docs_queries': tables_with_docs_queries
        }
    }
    try:
        manifest_meta = manifest_data.get('table_metadata', {}) or {}
        t_meta_start = time.time()
        for tinfo in enriched:
            if (time.time() - t_meta_start) > DOCS_META_MAX_SECONDS:
                print(f"[Workspace Schema] Metadata enrichment time budget exceeded ({DOCS_META_MAX_SECONDS}s); truncating.")
                break
            tname = tinfo['name']
            meta = manifest_meta.get(tname, {}).copy()
            if not DOCS_ENRICH_DISABLE and (not meta.get('description') or not meta.get('columns')):
                docs_meta = _fetch_table_docs_full(tname)
                if docs_meta:
                    if not meta.get('description') and docs_meta.get('description'):
                        meta['description'] = docs_meta['description']
                    if not meta.get('columns') and docs_meta.get('columns'):
                        meta['columns'] = docs_meta['columns']
            response['table_metadata'][tname] = meta
    except Exception as e:  # noqa: BLE001
        print(f"[Workspace Schema] Metadata enrichment error: {e}")
    # Verbose schema dump removed per request to reduce console noise.
    # Persist enriched response back into cache (exclude success/status to keep shape stable for early return)
    # Caching disabled: do not persist enriched workspace schema response.
    print(f"[Workspace Schema] Enrichment complete (no persistence) tables={len(response.get('tables', []))} table_queries_total={sum(len(v) for v in response.get('table_queries', {}).values())}")
    return jsonify(response)

@app.route('/api/workspace-schema-status', methods=['GET'])
def workspace_schema_status():
    """Stateless status endpoint (cache removed).

    Returns JSON:
      success: bool
      status: 'uninitialized' | 'ready' | 'empty'
      workspace_id: str|None
      table_count: int
      retrieved_at: str|None
      source: str|None
    """
    global workspace_id
    if not workspace_id:
        return jsonify({'success': False, 'status': 'uninitialized', 'workspace_id': None, 'table_count': 0, 'retrieved_at': None, 'source': None})
    result = get_workspace_schema(workspace_id)
    if result.get('error'):
        return jsonify({'success': False, 'status': 'error', 'workspace_id': workspace_id, 'error': result.get('error'), 'table_count': 0, 'retrieved_at': None, 'source': None})
    tables = result.get('tables', [])
    status = 'ready' if tables else 'empty'
    return jsonify({
        'success': True,
        'status': status,
        'workspace_id': workspace_id,
        'table_count': len(tables),
        'retrieved_at': result.get('retrieved_at'),
        'source': result.get('source')
    })

# ---------------------------------------------------------------------------
# Compatibility workspace schema endpoint (previously removed). Front-end and
# tests poll this path; we now serve immediate ready state with stateless fetch.
# ---------------------------------------------------------------------------
@app.route('/api/workspace-schema', methods=['GET'])
def workspace_schema():
    """Enriched workspace schema (stateless) with merged query suggestions.

    Returns:
      success: bool
      status: ready|empty|uninitialized|error
      workspace_id: str|None
      tables: [ { name, resource_type, manifest_resource_types? } ]
      counts: { workspace_tables, tables_with_manifest_queries, tables_with_capsule_csv_queries, tables_with_docs_queries }
      table_queries: { tableName: [ { name, description, code, source, file? } ] }
      table_metadata: { tableName: { description, columns:[{name,type,description}] } }
      doc_enrichment: { disabled: bool }
    """
    global workspace_id
    if not workspace_id:
        return jsonify({'success': False, 'status': 'uninitialized', 'workspace_id': None, 'tables': [], 'counts': {}, 'table_queries': {}, 'table_metadata': {}, 'error': 'Workspace not initialized'}), 400
    try:
        # Fetch workspace tables
        ws_result = get_workspace_schema(workspace_id)
        if ws_result.get('error'):
            return jsonify({'success': False, 'status': 'error', 'workspace_id': workspace_id, 'error': ws_result.get('error'), 'tables': [], 'table_queries': {}, 'table_metadata': {}}), 500
        workspace_tables = ws_result.get('tables', [])

        # Load manifest (resource types + manifest queries)
        manifest_tables_index = {}
        manifest_table_queries = {}
        manifest_table_metadata = {}
        try:
            from schema_manager import SchemaManager
            mgr = SchemaManager.get()
            mgr.load_manifest(force=False)
            manifest_cache = mgr._manifest_cache or {}
            manifest_tables_index = manifest_cache.get('resource_type_tables', {}) or {}
            # Build reverse index for resource types per table
            reverse_index = {}
            for rt, tbls in manifest_tables_index.items():
                for t in tbls:
                    reverse_index.setdefault(t, []).append(rt)
            manifest_table_queries = manifest_cache.get('table_queries', {}) or {}
            manifest_table_metadata = manifest_cache.get('table_metadata', {}) or {}
        except Exception as me:  # noqa: BLE001
            print(f"[WorkspaceSchema] Manifest load error: {me}")
            reverse_index = {}

        # Capsule CSV queries
        try:
            from examples_loader import load_capsule_csv_queries
            capsule_csv_queries = load_capsule_csv_queries()
        except Exception as ce:  # noqa: BLE001
            print(f"[WorkspaceSchema] Capsule CSV ingestion error: {ce}")
            capsule_csv_queries = {}

        # Docs queries (optional, only if not disabled)
        tables_with_docs_queries = 0
        def _normalize_code(code: str) -> str:
            if not isinstance(code, str):
                return ''
            c = code.replace('\r\n', '\n').replace('\r', '\n').strip()
            while '\n\n' in c:
                c = c.replace('\n\n', '\n')
            return c

        table_queries = {}
        tables_with_manifest_queries = 0
        tables_with_capsule_queries = 0
        for entry in workspace_tables:
            tname = entry.get('name')
            combined = []
            # Manifest queries first
            m_list = manifest_table_queries.get(tname) or []
            if m_list:
                for q in m_list:
                    if q.get('name'):
                        combined.append({
                            'name': q.get('name'),
                            'description': q.get('description'),
                            'code': q.get('code') if q.get('code') else None,
                            'source': 'manifest'
                        })
                tables_with_manifest_queries += 1
            # Capsule CSV queries second
            c_list = capsule_csv_queries.get(tname) or []
            if c_list:
                for q in c_list:
                    if q.get('name') and q.get('code'):
                        norm_code = _normalize_code(q.get('code'))
                        if not any(_normalize_code(existing.get('code')) == norm_code for existing in combined if existing.get('code')):
                            combined.append({
                                'name': q.get('name'),
                                'description': q.get('description') or '',
                                'code': q.get('code'),
                                'source': q.get('source') or 'capsule-csv',
                                'file': q.get('file')
                            })
                tables_with_capsule_queries += 1
            # Docs queries third (only if enabled)
            if not DOCS_ENRICH_DISABLE:
                docs_q = _fetch_table_docs_queries(tname)
                if docs_q:
                    added_docs = 0
                    for q in docs_q:
                        if q.get('name') and q.get('code'):
                            norm_code = _normalize_code(q.get('code'))
                            if not any(_normalize_code(existing.get('code')) == norm_code for existing in combined if existing.get('code')):
                                combined.append({
                                    'name': q.get('name'),
                                    'description': q.get('description'),
                                    'code': q.get('code'),
                                    'source': 'docs'
                                })
                                added_docs += 1
                    if added_docs:
                        tables_with_docs_queries += 1
            if combined:
                table_queries[tname] = combined

        # Attach manifest resource type info to tables
        reverse_index = {}
        for rt, tbls in manifest_tables_index.items():
            for t in tbls:
                reverse_index.setdefault(t, []).append(rt)
        enriched_tables = []
        for entry in workspace_tables:
            tname = entry.get('name')
            enriched_tables.append({
                'name': tname,
                'resource_type': entry.get('resource_type') or 'Unknown',
                'manifest_resource_types': reverse_index.get(tname, [])
            })

        # Build minimal table metadata (manifest first, docs fallback if enabled)
        table_metadata_out = {}
        for tname in [e['name'] for e in enriched_tables]:
            meta = manifest_table_metadata.get(tname, {}).copy()
            if not DOCS_ENRICH_DISABLE and (not meta.get('description') or not meta.get('columns')):
                docs_meta = _fetch_table_docs_full(tname)
                if docs_meta:
                    if not meta.get('description') and docs_meta.get('description'):
                        meta['description'] = docs_meta['description']
                    if not meta.get('columns') and docs_meta.get('columns'):
                        meta['columns'] = docs_meta['columns']
            table_metadata_out[tname] = meta

        status = 'ready' if enriched_tables else 'empty'
        return jsonify({
            'success': True,
            'status': status,
            'workspace_id': workspace_id,
            'tables': enriched_tables,
            'counts': {
                'workspace_tables': len(enriched_tables),
                'tables_with_manifest_queries': tables_with_manifest_queries,
                'tables_with_capsule_csv_queries': tables_with_capsule_queries,
                'tables_with_docs_queries': tables_with_docs_queries
            },
            'table_queries': table_queries,
            'table_metadata': table_metadata_out,
            'retrieved_at': ws_result.get('retrieved_at'),
            'source': ws_result.get('source'),
            'doc_enrichment': {
                'disabled': DOCS_ENRICH_DISABLE
            },
            'error': None
        })
    except Exception as e:  # noqa: BLE001
        return jsonify({'success': False, 'status': 'error', 'workspace_id': workspace_id, 'error': str(e)}), 500

@app.route('/api/refresh-manifest', methods=['POST'])
def refresh_manifest():
    """Force a rescan of NGSchema manifests and update persisted manifest cache.

    This endpoint is explicit and not part of normal UI flow. Returns summary counts.
    """
    try:
        from schema_manager import SchemaManager
        mgr = SchemaManager.get()
        mgr.load_manifest(force=True)
        manifest = mgr._manifest_cache
        return jsonify({
            'success': True,
            'forced': True,
            'resource_type_count': len(manifest.get('resource_type_tables', {})),
            'total_table_mappings': sum(len(v) for v in manifest.get('resource_type_tables', {}).values()),
            'fetched_at': manifest.get('fetched_at'),
            'manifests_scanned': manifest.get('manifests_scanned')
        })
    except Exception as e:  # noqa: BLE001
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/resource-schema', methods=['GET'])
def resource_schema():
    """Return manifest-derived resource schema merged with any cached workspace tables.

    This endpoint restores the previous /api/resource-schema functionality (now missing) so
    UI callers expecting it no longer receive a 404. It focuses on resource types and
    manifest metadata while optionally enriching with currently cached workspace tables.

    Response JSON includes:
      success: bool
      status: 'uninitialized' | 'pending' | 'ready'
      workspace_id: str|None
      manifest: {
        resource_types: [str],
        providers: [str],
        counts: { resource_types:int, providers:int, tables:int },
        resource_type_tables: { resource_type: [tableName] },
        table_metadata: { tableName: { description:str, columns:[{name,type,descriptions:[str]}], resource_types:[str] } },
        queries: [ { name, description, resource_type, provider, table, manifest_file, related_tables:[...] } ]
      }
      workspace: {
        tables: [ { name, resource_type } ],
        retrieved_at: str|None,
        count: int,
        source: str|None
      }
      table_join: [ { name, workspace_resource_type, manifest_resource_types:[str] } ]
    """
    global workspace_id

    # Persistent manifest load via SchemaManager (decoupled from workspace fetch)
    try:
        from schema_manager import SchemaManager
        mgr = SchemaManager.get()
        mgr.load_manifest(force=False)
        manifest_data = mgr._manifest_cache
    except Exception as e:  # pragma: no cover
        print(f"[ResourceSchema] Manifest load error: {e}")
        manifest_data = {}

    # If no workspace selected yet, return manifest-only payload (no error)
    if not workspace_id:
        # Provide explicit top-level lists for frontend convenience (resource_types/providers)
        _rt_tables = manifest_data.get('resource_type_tables', {}) or {}
        _resource_types_list = sorted(_rt_tables.keys())
        _providers_list = sorted({rt.split('/')[0] for rt in _rt_tables})
        return jsonify({
            'success': True,
            'status': 'manifest-only',
            'workspace_id': None,
            'manifest': {
                'resource_type_tables': _rt_tables,
                'table_resource_types': manifest_data.get('table_resource_types', {}),
                'resource_types': _resource_types_list,
                'providers': _providers_list,
                'fetched_at': manifest_data.get('fetched_at'),
                'manifests_scanned': manifest_data.get('manifests_scanned'),
                'counts': {
                    'resource_types': len(_resource_types_list),
                    'providers': len(_providers_list),
                    'tables': sum(len(v) for v in _rt_tables.values())
                }
            },
            'workspace': {
                'tables': [], 'retrieved_at': None, 'count': 0, 'source': None
            },
            'table_join': []
        })

    # Workspace tables (may be absent if not yet fetched)
    # Fresh fetch of workspace tables (cache removed)
    ws_result = get_workspace_schema(workspace_id)
    if ws_result.get('error'):
        print(f"[ResourceSchema] workspace fetch error: {ws_result.get('error')}")
        workspace_tables = []
        ws_retrieved = None
        ws_source = None
    else:
        workspace_tables = ws_result.get('tables', [])
        ws_retrieved = ws_result.get('retrieved_at')
        ws_source = ws_result.get('source')

    # workspace_tables already set above
    join = []
    manifest_tables_index = manifest_data.get('resource_type_tables', {})
    # Build reverse index table -> list(resource_types)
    reverse_index = {}
    for rt, tbls in manifest_tables_index.items():
        for t in tbls:
            reverse_index.setdefault(t, []).append(rt)
    for entry in workspace_tables:
        tname = entry.get('name')
        w_rt = entry.get('resource_type') or 'Unknown'
        m_rts = reverse_index.get(tname, [])
        join.append({'name': tname, 'workspace_resource_type': w_rt, 'manifest_resource_types': m_rts})

    _rt_tables = manifest_data.get('resource_type_tables', {}) or {}
    _resource_types_list = sorted(_rt_tables.keys())
    _providers_list = sorted({rt.split('/')[0] for rt in _rt_tables})
    return jsonify({
        'success': True,
        'status': 'ready',
        'workspace_id': workspace_id,
        'manifest': {
            'resource_type_tables': _rt_tables,
            'table_resource_types': manifest_data.get('table_resource_types', {}),
            'resource_types': _resource_types_list,
            'providers': _providers_list,
            'fetched_at': manifest_data.get('fetched_at'),
            'manifests_scanned': manifest_data.get('manifests_scanned'),
            'counts': {
                'resource_types': len(_resource_types_list),
                'providers': len(_providers_list),
                'tables': sum(len(v) for v in _rt_tables.values())
            }
        },
        'workspace': {
            'tables': [{'name': e.get('name'), 'resource_type': e.get('resource_type') or 'Unknown', 'manifest_resource_types': e.get('manifest_resource_types', [])} for e in workspace_tables],
            'retrieved_at': ws_retrieved,
            'count': len(workspace_tables),
            'source': ws_source
        },
        'table_join': join
    })


def _scan_manifest_resource_types() -> dict:
    """Scan NGSchema manifest files to enumerate resource types/providers, map tables, and pick up query definitions.

    Returns a dict with keys:
        resource_types: List[str]
        providers: List[str]
        counts: { 'resource_types': int, 'providers': int, 'tables': int }
        resource_type_tables: { resource_type: [tableName, ...] }
        table_resource_type: { tableName: resource_type }
        queries: [ { 'resource_type': str, 'provider': str, 'name': str, 'description': str, 'table': str|None, 'path': str|None, 'manifest_file': str } ]
        queries_by_provider: { provider: [query, ...] }
        queries_by_resource_type: { resource_type: [query, ...] }
        retrieved_at: ISO timestamp

    Query extraction heuristics:
        - Look for top-level or nested keys named 'queries', 'sampleQueries', 'queryExamples'
        - Each item may include name/description/table/path or similar fields
        - Record path relative to repo if provided or attempt to infer when key 'file'/'path' present
    """
    if _workspace_resource_types_cache.get('resource_types') and _workspace_resource_types_cache.get('resource_type_tables'):
        return _workspace_resource_types_cache

    base_dir = os.path.join(os.path.dirname(__file__), 'NGSchema')
    if not os.path.isdir(base_dir):
        print('[Manifest Scan] NGSchema directory not found; skipping.')
        _workspace_resource_types_cache.update({
            'resource_types': [],
            'providers': [],
            'counts': {'resource_types': 0, 'providers': 0, 'tables': 0},
            'resource_type_tables': {},
            'table_resource_type': {},
            'retrieved_at': datetime.now(timezone.utc).isoformat()
        })
        return _workspace_resource_types_cache

    import json
    resource_types = set()
    resource_type_tables = {}
    table_resource_type = {}
    table_metadata = {}  # table_name -> { description, columns: [ {name,type,description?} ], resource_types:[...] }
    extracted_queries = []  # flat list of query metadata
    table_queries = {}      # table_name -> [ { name, description, resource_type, provider, manifest_file } ]
    manifest_files = []
    for root, _, files in os.walk(base_dir):
        for fname in files:
            if fname.endswith('.manifest.json'):
                manifest_files.append(os.path.join(root, fname))

    print(f'[Manifest Scan] Found {len(manifest_files)} manifest files. Parsing...')

    def _extract_types(obj, current_resource_type=None, manifest_path=None):
        if isinstance(obj, dict):
            tval = obj.get('type')
            if isinstance(tval, str) and '/' in tval:
                resource_types.add(tval)
                current_resource_type = tval
                resource_type_tables.setdefault(current_resource_type, [])
            # Strict query collection: ONLY process items under a 'queries' list.
            # Each query's related tables come EXCLUSIVELY from its 'relatedTables' array.
            if 'queries' in obj and isinstance(obj['queries'], list):
                for q in obj['queries']:
                    if not isinstance(q, dict):
                        continue
                    q_name = q.get('name') or q.get('title') or q.get('queryName')
                    if not q_name:
                        continue  # skip nameless entries
                    q_desc = q.get('description') or q.get('summary') or ''
                    q_path = q.get('path') or q.get('file') or q.get('kqlFile') or q.get('kql_path')
                    # Only consider 'relatedTables' as authoritative mapping
                    related_list = q.get('relatedTables')
                    if not isinstance(related_list, list) or not related_list:
                        # If no relatedTables provided, we treat it as global (no table association)
                        related_tables = []
                    else:
                        # Filter to non-empty string table names
                        related_tables = [t for t in related_list if isinstance(t, str) and t]
                    q_record = {
                        'resource_type': current_resource_type,
                        'provider': (current_resource_type.split('/')[0] if current_resource_type else None),
                        'name': q_name,
                        'description': q_desc,
                        'path': q_path,
                        'manifest_file': manifest_path,
                        'related_tables': sorted(related_tables)
                    }
                    extracted_queries.append(q_record)
                    for rt_table in related_tables:
                        table_queries.setdefault(rt_table, []).append({
                            'name': q_name,
                            'description': q_desc,
                            'resource_type': current_resource_type,
                            'provider': (current_resource_type.split('/')[0] if current_resource_type else None),
                            'manifest_file': manifest_path
                        })
            if 'tables' in obj and isinstance(obj['tables'], list):
                for tbl in obj['tables']:
                    if isinstance(tbl, dict):
                        tname = tbl.get('name') or tbl.get('tableName')
                        if tname and current_resource_type:
                            if tname not in resource_type_tables[current_resource_type]:
                                resource_type_tables[current_resource_type].append(tname)
                                table_resource_type.setdefault(tname, current_resource_type)
                            # Capture table metadata
                            tdesc = tbl.get('description') or tbl.get('summary') or ''
                            columns = []
                            raw_cols = tbl.get('columns') or tbl.get('schema') or []
                            if isinstance(raw_cols, list):
                                for c in raw_cols:
                                    if isinstance(c, dict):
                                        cname = c.get('name') or c.get('columnName')
                                        ctype = c.get('type') or c.get('dataType')
                                        cdesc = c.get('description') or ''
                                        if cname:
                                            columns.append({'name': cname, 'type': ctype, 'description': cdesc})
                            meta = table_metadata.setdefault(tname, {'descriptions': set(), 'columns': {}, 'resource_types': set()})
                            if tdesc:
                                meta['descriptions'].add(tdesc)
                            meta['resource_types'].add(current_resource_type)
                            for col in columns:
                                existing = meta['columns'].get(col['name'])
                                if not existing:
                                    meta['columns'][col['name']] = {'type': col['type'], 'descriptions': set()}
                                if col.get('type') and not meta['columns'][col['name']]['type']:
                                    meta['columns'][col['name']]['type'] = col['type']
                                if col.get('description'):
                                    meta['columns'][col['name']]['descriptions'].add(col['description'])
            for v in obj.values():
                _extract_types(v, current_resource_type=current_resource_type, manifest_path=manifest_path)
        elif isinstance(obj, list):
            for item in obj:
                _extract_types(item, current_resource_type=current_resource_type, manifest_path=manifest_path)

    for mpath in manifest_files:
        try:
            with open(mpath, 'r', encoding='utf-8') as mf:
                data = json.load(mf)
            _extract_types(data, manifest_path=mpath)
        except Exception as e:  # noqa: BLE001
            print(f'[Manifest Scan] Error parsing {mpath}: {e}')

    providers = {rt.split('/')[0] for rt in resource_types}
    resource_types_list = sorted(resource_types)
    providers_list = sorted(providers)

    # Organize queries by provider and resource type
    queries_by_provider = {}
    queries_by_resource_type = {}
    for q in extracted_queries:
        prov = q.get('provider') or 'Unknown'
        rt = q.get('resource_type') or 'Unknown'
        queries_by_provider.setdefault(prov, []).append(q)
        queries_by_resource_type.setdefault(rt, []).append(q)

    _workspace_resource_types_cache.update({
        'resource_types': resource_types_list,
        'providers': providers_list,
        'counts': {
            'resource_types': len(resource_types_list),
            'providers': len(providers_list),
            'tables': sum(len(v) for v in resource_type_tables.values())
        },
        'resource_type_tables': resource_type_tables,
        'table_resource_type': table_resource_type,
        'queries': extracted_queries,
        'queries_by_provider': queries_by_provider,
        'queries_by_resource_type': queries_by_resource_type,
        'table_queries': table_queries,
        'table_metadata': {
            t: {
                'description': next(iter(m['descriptions'])) if m['descriptions'] else '',
                'all_descriptions': sorted(m['descriptions']),
                'columns': [
                    {
                        'name': cname,
                        'type': cinfo.get('type'),
                        'descriptions': sorted(cinfo.get('descriptions'))
                    } for cname, cinfo in sorted(m['columns'].items())
                ],
                'resource_types': sorted(m['resource_types'])
            } for t, m in table_metadata.items()
        },
        'retrieved_at': datetime.now(timezone.utc).isoformat()
    })

    # print('[Manifest Scan] Summary:')
    # print(f"  Resource Types: {len(resource_types_list)}")
    # print(f"  Providers: {len(providers_list)}")
    # total_tables = sum(len(v) for v in resource_type_tables.values())
    # print(f"  Tables (mapped): {total_tables}")
    # if extracted_queries:
        # print(f"  Queries extracted: {len(extracted_queries)}")
        # print(f"  Tables with query references: {len(table_queries)}")
    # if table_metadata:
        # print(f"  Tables with metadata: {len(table_metadata)}")
    # preview_types = resource_types_list[:20]
    # if preview_types:
    #     print('  Sample Resource Types:')
    #     for t in preview_types:
    #         print(f'    - {t}')
    #     if len(resource_types_list) > len(preview_types):
    #         print(f'    ... (+{len(resource_types_list) - len(preview_types)} more)')
    # print('  Providers: ' + ', '.join(providers_list[:15]) + (' ...' if len(providers_list) > 15 else ''))
    # print('  Sample Resource Type -> Tables:')
    # shown = 0
    # for rt in preview_types:
    #     tables_preview = resource_type_tables.get(rt, [])[:5]
    #     if tables_preview:
    #         print(f'    * {rt}: {", ".join(tables_preview)}' + (' ...' if len(resource_type_tables.get(rt, [])) > 5 else ''))
    #         shown += 1
    #     if shown >= 8:
    #         break

    return _workspace_resource_types_cache


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


def _fetch_workspace_tables(workspace: str):
    """Deprecated (cache removed). Kept for backward compatibility; now just performs a direct fetch and logs summary."""
    if not workspace:
        print("[Workspace Schema] No workspace ID provided.")
        return
    result = get_workspace_schema(workspace)
    if result.get("error"):
        print(f"[Workspace Schema] Error: {result['error']}")
        return
    tables = result.get("tables", [])
    print(f"[Workspace Schema] Direct fetch tables={len(tables)} source={result.get('source')} refreshed={result.get('refreshed')}")


def _background_fetch_workspace_tables(workspace: str):
    """Deprecated shim retained for compatibility; just calls get_workspace_schema and logs summary."""
    if not workspace:
        return
    try:
        result = get_workspace_schema(workspace)
        if result.get('error'):
            print(f"[Workspace Schema] Background fetch error workspace={workspace}: {result['error']}")
        else:
            print(f"[Workspace Schema] Background direct fetch tables={len(result.get('tables', []))} source={result.get('source')} refreshed={result.get('refreshed')}")
    except Exception as e:  # noqa: BLE001
        print(f"[Workspace Schema] Background fetch unexpected error workspace={workspace}: {e}")


@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')

@app.route('/api/setup', methods=['POST'])
def setup_workspace():
    """Setup the workspace ID for the agent"""
    global agent, workspace_id
    
    try:
        data = request.get_json()
        workspace_id = data.get('workspace_id', '').strip()
        
        if not workspace_id:
            return jsonify({'success': False, 'error': 'Workspace ID is required'})
        
        # Initialize agent
        agent = KQLAgent(workspace_id)
        # Intentionally do NOT start schema fetch here to allow client to trigger and observe pending state
        print("[Setup] Workspace initialized; schema fetch will start on first /api/workspace-schema request.")
    # Skip early persistence; we'll persist only once tables or enrichment are available.
        
        return jsonify({
            'success': True, 
            'message': f'Agent initialized for workspace: {workspace_id}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Failed to setup workspace: {str(e)}'
        })

@app.route('/api/clear-workspace-cache', methods=['POST'])
def clear_workspace_cache():
    """Deprecated: cache removed. Always returns success without side effects."""
    global workspace_id
    if not workspace_id:
        return jsonify({'success': False, 'error': 'Workspace not initialized'}), 400
    return jsonify({'success': True, 'workspace_id': workspace_id, 'cache_cleared': False, 'message': 'Schema caching removed; nothing to clear.'})

@app.route('/api/query', methods=['POST'])
def process_query():
    """Process a natural language question"""
    global agent
    
    try:
        if not agent:
            return jsonify({
                'success': False, 
                'error': 'Agent not initialized. Please setup workspace first.'
            })
        
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'success': False, 'error': 'Question is required'})
        
        # Run the async query processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(agent.process_natural_language(question))
            response_payload = {
                'success': True,
                'result': result,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            # Expose examples_error and candidate scores when container selection failed
            if isinstance(result, str) and result.startswith('// Error') and 'domain=containers' in result and 'selected_example_count=0' in result:
                try:
                    from nl_to_kql import load_container_shots
                    ctx = load_container_shots(question)
                    response_payload['examples_error'] = ctx.get('examples_error')
                    response_payload['top_candidate_scores'] = ctx.get('top_candidate_scores')
                except Exception as expose_exc:
                    response_payload['examples_error'] = f'expose_failed: {expose_exc}'
            return jsonify(response_payload)
        finally:
            loop.close()
            
    except Exception as e:
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        
        return jsonify({
            'success': False,
            'error': error_msg,
            'traceback': traceback_str
        })

@app.route('/api/explain', methods=['POST'])
def explain_query_result():
    """Explain previously returned query results.

    Expects JSON body:
      {
        "query_result": <result object returned by /api/query>,
        "original_question": "string"
      }

    Returns JSON:
      success: bool
      explanation: str (present on success)
      error: str (present on failure)
      timestamp: ISO8601
    """
    global agent
    try:
        if not agent:
            return jsonify({'success': False, 'error': 'Agent not initialized'}), 400
        payload = request.get_json(silent=True) or {}
        query_result = payload.get('query_result')
        original_question = payload.get('original_question', '')
        if not query_result:
            return jsonify({'success': False, 'error': 'query_result is required'}), 400
        # Ensure result structure minimally matches expectations
        if not isinstance(query_result, dict) or query_result.get('type') != 'query_success':
            return jsonify({'success': False, 'error': 'query_result must be a successful query response'}), 400
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            explanation = loop.run_until_complete(agent.explain_results(query_result, original_question))
        finally:
            loop.close()
        if isinstance(explanation, str) and explanation.startswith('❌'):
            return jsonify({'success': False, 'error': explanation}), 200
        return jsonify({
            'success': True,
            'explanation': explanation,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:  # noqa: BLE001
        print(f"[Explain] Unexpected error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/refresh-workspace-schema', methods=['GET', 'POST'])
def refresh_workspace_schema():
    """Compatibility refresh endpoint (stateless model).

    Accepts optional JSON {"refetch": bool}. Always returns 200 with summary.
    If workspace not initialized, returns success=False but does not error.
    """
    global workspace_id
    if not workspace_id:
        return jsonify({'success': False, 'workspace_id': None, 'message': 'Workspace not initialized', 'table_count': 0}), 200
    try:
        payload = request.get_json(silent=True) or {}
        if not payload.get('refetch', True):
            return jsonify({'success': True, 'workspace_id': workspace_id, 'message': 'No refetch requested', 'table_count': 0}), 200
        result = get_workspace_schema(workspace_id)
        if result.get('error'):
            return jsonify({'success': False, 'workspace_id': workspace_id, 'error': result.get('error'), 'table_count': 0}), 200
        tables = result.get('tables', [])
        return jsonify({
            'success': True,
            'workspace_id': workspace_id,
            'refetched': True,
            'table_count': len(tables),
            'retrieved_at': result.get('retrieved_at'),
            'source': result.get('source')
        }), 200
    except Exception as e:  # noqa: BLE001
        return jsonify({'success': False, 'workspace_id': workspace_id, 'error': str(e), 'table_count': 0}), 200
        
        # Read and parse the example file
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Extract example queries (simple parsing - look for lines starting with specific patterns)
        examples = []
        lines = content.split('\n')
        current_example = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('# ') or line.startswith('## '):
                if current_example:
                    examples.append(current_example)
                current_example = line.replace('#', '').strip()
            elif line.startswith('- ') and current_example:
                example_text = line.replace('- ', '').strip()
                if example_text:
                    examples.append(example_text)
                    current_example = None
    # If we have fewer than 5 examples, add some generic ones
        if len(examples) < 5:
            generic_examples = {
                'requests': [
                    'Show me failed requests from the last hour',
                    'What are the slowest requests in the last 24 hours?',
                    'Show me requests with response time > 5 seconds',
                    'Get the top 10 most frequent request URLs',
                    'Show me requests grouped by status code'
                ],
                'exceptions': [
                    'Show me recent exceptions',
                    'What are the most common exception types?',
                    'Show me exceptions from the last 6 hours',
                    'Get exception count by severity level',
                    'Show me exceptions grouped by operation name'
                ],
                'traces': [
                    'Show me recent trace logs',
                    'What are the most frequent trace messages?',
                    'Show me error traces from the last hour',
                    'Get traces with specific severity level',
                    'Show me traces grouped by source'
                ],
                'dependencies': [
                    'Show me dependency failures',
                    'What are the slowest dependencies?',
                    'Show me dependencies with high failure rate',
                    'Get dependency calls from the last hour',
                    'Show me dependencies grouped by type'
                ],
                'custom_events': [
                    'Show me recent custom events',
                    'What are the most frequent custom event types?',
                    'Show me custom events from the last hour',
                    'Get custom events grouped by name',
                    'Show me custom events with specific properties'
                ],
                'page_views': [
                    'Show me page views from the last hour',
                    'What are the most popular pages?',
                    'Show me page views grouped by browser',
                    'Get page load times by URL',
                    'Show me page views by geographic location'
                ],
                'performance': [
                    'Show me performance counters',
                    'What are the CPU usage trends?',
                    'Show me memory usage over time',
                    'Get performance metrics for the last hour',
                    'Show me performance counters by category'
                ],
                'usage': [
                    'Show me user activity patterns',
                    'What are the most popular features?',
                    'Show me usage statistics by region',
                    'Get daily active users',
                    'Show me usage trends over time'
                ]
            }
            
            if scenario in generic_examples:
                examples.extend(generic_examples[scenario][:5-len(examples)])
        
        # Limit to top 8 examples
        examples = examples[:8]
        
        return jsonify({
            'success': True,
            'result': {
                'type': 'example_suggestions',
                'scenario': scenario,
                'suggestions': examples,
                'count': len(examples)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/workspace-examples', methods=['POST'])
def discover_workspace_examples():
    """Discover workspace tables and map them to available example queries"""
    global agent, workspace_id
    
    try:
        # Allow workspace examples discovery even without agent initialization
        # since we're just showing available example files
        
        import os
        import glob
        
        # Define table mappings to example files
        table_examples_map = {
            'AppRequests': {
                'file': 'app_insights_capsule/kql_examples/app_requests_kql_examples.md',
                'category': 'Application Insights',
                'description': 'HTTP requests to your application'
            },
            'AppExceptions': {
                'file': 'app_insights_capsule/kql_examples/app_exceptions_kql_examples.md', 
                'category': 'Application Insights',
                'description': 'Exceptions thrown by your application'
            },
            'AppTraces': {
                'file': 'app_insights_capsule/kql_examples/app_traces_kql_examples.md',
                'category': 'Application Insights', 
                'description': 'Custom trace logs from your application'
            },
            'AppDependencies': {
                'file': 'app_insights_capsule/kql_examples/app_dependencies_kql_examples.md',
                'category': 'Application Insights',
                'description': 'External dependencies called by your application'
            },
            'AppPageViews': {
                'file': 'app_insights_capsule/kql_examples/app_page_views_kql_examples.md',
                'category': 'Application Insights',
                'description': 'Page views in your web application'
            },
            'AppCustomEvents': {
                'file': 'app_insights_capsule/kql_examples/app_custom_events_kql_examples.md',
                'category': 'Application Insights', 
                'description': 'Custom events tracked by your application'
            },
            'AppPerformanceCounters': {
                'file': 'app_insights_capsule/kql_examples/app_performance_kql_examples.md',
                'category': 'Application Insights',
                'description': 'Performance counters and metrics'
            },
            'Usage': {
                'file': 'usage_kql_examples.md',
                'category': 'Usage Analytics',
                'description': 'User behavior and usage patterns'
            }
        }
        
        # Get available example files
        example_files = glob.glob('*_kql_examples.md')
        available_examples = {}
        
        for table, info in table_examples_map.items():
            if os.path.exists(info['file']):
                available_examples[table] = info
        
        # Count examples by category
        example_categories = {}
        for table, info in available_examples.items():
            category = info['category']
            example_categories[category] = example_categories.get(category, 0) + 1
        
        # Simulate discovered tables (in a real implementation, you'd query the workspace)
        discovered_tables = list(available_examples.keys())
        
        # Create summary
        summary = {
            'workspace_id': workspace_id or 'Not configured',
            'total_tables': len(discovered_tables),
            'tables_with_examples': len(available_examples),
            'example_categories': example_categories
        }
        
        # Create table details in the format expected by the frontend
        available_examples_formatted = {}
        for table in discovered_tables:
            if table in available_examples:
                info = available_examples[table]
                available_examples_formatted[table] = {
                    'table_info': {
                        'record_count': 10000,  # Simulated count, would be real in production
                        'category': info['category'],
                        'description': info['description']
                    },
                    'examples': [
                        {
                            'source': '',
                            'description': '',  # Remove duplicate description (now shown in table header)
                            'query_count': 5  # Simulated count
                        }
                    ]
                }
        
        return jsonify({
            'success': True,
            'summary': summary,
            'available_examples': available_examples_formatted,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/example-catalog', methods=['POST'])
def example_catalog():
    """Return unified example + (optional) live schema catalog.

    Expects JSON body: {"include_schema": bool, "force": bool}
    """
    global workspace_id
    try:
        req = request.get_json(silent=True) or {}
        include_schema = bool(req.get('include_schema', True))
        force = bool(req.get('force', False))
        catalog = load_example_catalog(workspace_id, include_schema=include_schema, force=force)
        return jsonify({
            'success': True,
            'catalog': catalog
        })
    except Exception as e:  # Broad catch acceptable for endpoint boundary
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

if __name__ == '__main__':
    print("🌐 Starting Natural Language KQL Agent Web Interface...")
    print("📊 Features available:")
    print("   - Natural language to KQL translation")
    print("   - Interactive workspace setup")
    print("   - Query execution and results display")
    print("   - Example queries and suggestions")
    print("   - Workspace table discovery")
    debug_mode = os.environ.get('FLASK_DEBUG','0') == '1'
    print(f"🚀 Starting server on http://localhost:8080 (debug={debug_mode})")
    try:
        app.run(debug=debug_mode, host='0.0.0.0', port=8080)
    except KeyboardInterrupt:
        print("\n🛑 Web Interface stopped")
    except Exception as e:
        print(f"❌ Error starting web interface: {e}")
        import traceback
        traceback.print_exc()