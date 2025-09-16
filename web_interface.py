#!/usr/bin/env python3
"""
Legacy FastAPI-based KQL web interface (restored from outdated_files).

Updated to remove deprecated imports and use current Azure SDK patterns.
Prefer using the richer Flask UI in `web_app.py` for full functionality.
This file is kept for lightweight, form-based KQL execution.
"""

from __future__ import annotations

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uvicorn
from datetime import timedelta
from typing import List

try:  # Azure SDK imports
    from azure.identity import DefaultAzureCredential
    from azure.monitor.query import LogsQueryClient, LogsQueryStatus
except ImportError as e:  # Provide helpful guidance if missing
    raise SystemExit(
        "Missing Azure Monitor dependencies. Install requirements first: pip install -r requirements.txt\n" \
        f"Original import error: {e}"
    )

# Instantiate client once (relies on Azure CLI / Managed Identity / Env creds)
_credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
_logs_client = LogsQueryClient(_credential)

app = FastAPI(title="Azure Log Analytics KQL Query Interface (Legacy)")

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset='utf-8'/>
    <title>Azure Log Analytics KQL Query Interface</title>
    <style>
        body { font-family: system-ui, Arial, sans-serif; margin: 40px; background:#fafafa; }
        h1 { margin-top:0; }
        .container { max-width: 1180px; margin: 0 auto; }
        .form-group { margin-bottom: 18px; }
        label { display:block; margin-bottom:6px; font-weight:600; }
        input, textarea, select { width:100%; padding:10px 12px; border:1px solid #ccc; border-radius:6px; font-size:14px; }
        textarea { height:120px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
        button { background:#2563eb; color:#fff; padding:12px 26px; border:none; border-radius:6px; font-size:15px; cursor:pointer; }
        button:hover { background:#1d4ed8; }
        .results { margin-top:32px; }
        .error { color:#991b1b; background:#fee2e2; padding:16px 18px; border-radius:6px; }
        .success { color:#065f46; background:#d1fae5; padding:16px 18px; border-radius:6px; }
        table { width:100%; border-collapse:collapse; margin-top:16px; font-size:13px; background:#fff; }
        th, td { border:1px solid #e5e7eb; padding:6px 8px; text-align:left; }
        th { background:#f3f4f6; font-weight:600; }
        .examples { background:#f1f5f9; padding:16px 18px; border-radius:6px; margin-bottom:22px; }
        .example-query { background:#fff; padding:8px 10px; margin:5px 0; border-left:4px solid #2563eb; cursor:pointer; font-family: ui-monospace, monospace; }
        .example-query:hover { background:#f1f5f9; }
        footer { margin-top:42px; font-size:12px; color:#555; }
        .pill { display:inline-block; background:#e0f2fe; color:#0369a1; padding:4px 10px; border-radius:999px; font-size:12px; margin:2px 4px 0 0; }
        code { background:#eef2f7; padding:2px 5px; border-radius:4px; }
    </style>
    <script>
        function setQuery(q){ document.getElementById('query').value = q; }
    </script>
</head>
<body>
<div class='container'>
  <h1>🔍 Azure Log Analytics – KQL Query Interface (Legacy)</h1>
  <p>This minimalist interface is kept for quick tests. For the full-featured experience use <code>web_app.py</code>.</p>
  <div class='examples'>
    <h3>📚 Example Queries (click to load):</h3>
    <div class='example-query' onclick="setQuery('Heartbeat | where TimeGenerated > ago(1h) | take 10')"><strong>Recent Heartbeat</strong></div>
    <div class='example-query' onclick="setQuery('AppRequests | where TimeGenerated > ago(1h) | where Success == false | take 10')"><strong>Failed Requests (1h)</strong></div>
    <div class='example-query' onclick="setQuery('AppExceptions | where TimeGenerated > ago(1d) | summarize count() by Type | top 5 by count_')"><strong>Top Exceptions (24h)</strong></div>
    <div class='example-query' onclick="setQuery('Usage | where TimeGenerated > ago(1d) | summarize sum(Quantity)')"><strong>Ingestion Volume (24h)</strong></div>
  </div>
  <form method='post' action='/query'>
    <div class='form-group'>
      <label for='workspace_id'>Log Analytics Workspace ID</label>
      <input id='workspace_id' name='workspace_id' required placeholder='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' />
    </div>
    <div class='form-group'>
      <label for='query'>KQL Query</label>
      <textarea id='query' name='query' required placeholder='Enter KQL here...'></textarea>
    </div>
    <div class='form-group'>
      <label for='timespan_hours'>Timespan (hours)</label>
      <select id='timespan_hours' name='timespan_hours'>
        <option value='1'>Last 1 hour</option>
        <option value='4'>Last 4 hours</option>
        <option value='24'>Last 24 hours</option>
        <option value='168'>Last 7 days</option>
      </select>
    </div>
    <button type='submit'>🚀 Execute Query</button>
  </form>
  {{ results }}
  <footer>
    <div>Auth uses DefaultAzureCredential – ensure you ran <code>az login</code> or set env credentials.</div>
    <div>For advanced features (NL → KQL, formatting, multi-table UI) use <code>python web_app.py</code>.</div>
  </footer>
</div>
</body>
</html>"""


def _render(results_html: str = "") -> str:
    return HTML_TEMPLATE.replace("{{ results }}", results_html)


@app.get("/", response_class=HTMLResponse)
async def root():  # noqa: D401
    return _render("")


@app.post("/query", response_class=HTMLResponse)
async def query(workspace_id: str = Form(...), query: str = Form(...), timespan_hours: int = Form(1)):
    try:
        timespan = timedelta(hours=int(timespan_hours))
        response = _logs_client.query_workspace(workspace_id=workspace_id, query=query, timespan=timespan)

        if response.status == LogsQueryStatus.SUCCESS:
            tables_html: List[str] = []
            for ti, table in enumerate(response.tables):  # type: ignore[attr-defined]
                cols = [getattr(c, 'name', str(c)) for c in getattr(table, 'columns', [])]
                rows = getattr(table, 'rows', [])
                header = '<tr>' + ''.join(f'<th>{c}</th>' for c in cols) + '</tr>' if cols else ''
                body_parts = []
                for r in rows:
                    body_parts.append('<tr>' + ''.join(f'<td>{'' if v is None else v}</td>' for v in r) + '</tr>')
                table_html = f"<h4>Table {ti+1} ({len(rows)} rows)</h4><table>{header}{''.join(body_parts)}</table>"
                tables_html.append(table_html)
            results_html = "<div class='results success'><h3>✅ Query executed successfully.</h3>" + ''.join(tables_html) + "</div>"
        else:
            partial = getattr(response, 'partial_error', 'Query failed')
            results_html = f"<div class='results error'><h3>❌ Query failed</h3><pre>{partial}</pre></div>"
    except Exception as exc:  # noqa: BLE001
        results_html = f"<div class='results error'><h3>❌ Error</h3><pre>{exc}</pre></div>"
    return _render(results_html)


if __name__ == "__main__":
    print("🚀 Starting legacy FastAPI KQL interface at http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)
