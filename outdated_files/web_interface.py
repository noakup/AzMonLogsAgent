#!/usr/bin/env python3
"""
Enhanced KQL Query Interface - Web version with better UI
"""

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
from pathlib import Path

# Import your existing functionality
import sys
sys.path.append('.')
from my_first_mcp_server.main_new import client, process_query_results
from azure.monitor.query import LogsQueryStatus
from datetime import datetime, timedelta, timezone

app = FastAPI(title="Azure Log Analytics KQL Query Interface")

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Azure Log Analytics KQL Query Interface</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, textarea, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        textarea { height: 120px; font-family: monospace; }
        button { background-color: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background-color: #0056b3; }
        .results { margin-top: 30px; }
        .error { color: red; background-color: #ffe6e6; padding: 15px; border-radius: 4px; }
        .success { color: green; background-color: #e6ffe6; padding: 15px; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .examples { background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; }
        .example-query { background-color: #fff; padding: 10px; margin: 5px 0; border-left: 4px solid #007bff; cursor: pointer; }
        .example-query:hover { background-color: #f0f0f0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Azure Log Analytics KQL Query Interface</h1>
        
        <div class="examples">
            <h3>📚 Example Queries (click to use):</h3>
            <div class="example-query" onclick="setQuery('Heartbeat | where TimeGenerated > ago(1h) | take 10')">
                <strong>Recent Heartbeat:</strong> Heartbeat | where TimeGenerated > ago(1h) | take 10
            </div>
            <div class="example-query" onclick="setQuery('AppRequests | where TimeGenerated > ago(1h) | where Success == false | take 10')">
                <strong>Failed Requests:</strong> AppRequests | where TimeGenerated > ago(1h) | where Success == false | take 10
            </div>
            <div class="example-query" onclick="setQuery('AppExceptions | where TimeGenerated > ago(1d) | summarize count() by ExceptionType | top 5 by count_')">
                <strong>Top Exceptions:</strong> AppExceptions | where TimeGenerated > ago(1d) | summarize count() by ExceptionType | top 5 by count_
            </div>
            <div class="example-query" onclick="setQuery('Usage | where TimeGenerated > ago(1d) | summarize sum(Quantity)')">
                <strong>Data Usage:</strong> Usage | where TimeGenerated > ago(1d) | summarize sum(Quantity)
            </div>
        </div>

        <form method="post" action="/query">
            <div class="form-group">
                <label for="workspace_id">Log Analytics Workspace ID:</label>
                <input type="text" id="workspace_id" name="workspace_id" required 
                       placeholder="12345678-1234-1234-1234-123456789012">
            </div>
            
            <div class="form-group">
                <label for="query">KQL Query:</label>
                <textarea id="query" name="query" required 
                          placeholder="Enter your KQL query here..."></textarea>
            </div>
            
            <div class="form-group">
                <label for="timespan_hours">Timespan (hours):</label>
                <select id="timespan_hours" name="timespan_hours">
                    <option value="1">Last 1 hour</option>
                    <option value="4">Last 4 hours</option>
                    <option value="24">Last 24 hours</option>
                    <option value="168">Last 7 days</option>
                </select>
            </div>
            
            <button type="submit">🚀 Execute Query</button>
        </form>
        
        {{ results }}
    </div>
    
    <script>
        function setQuery(query) {
            document.getElementById('query').value = query;
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def show_form():
    """Show the query form"""
    return HTML_TEMPLATE.replace("{{ results }}", "")

@app.post("/query", response_class=HTMLResponse)
async def execute_query(
    workspace_id: str = Form(...),
    query: str = Form(...),
    timespan_hours: int = Form(1)
):
    """Execute the KQL query and show results"""
    
    try:
        # Set up timespan
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=timespan_hours)
        timespan = (start_time, end_time)
        
        # Execute query
        response = client.query_workspace(
            workspace_id=workspace_id,
            query=query,
            timespan=timespan
        )
        
        # Process results
        if response.status == LogsQueryStatus.SUCCESS:
            tables = []
            for table in response.tables:
                columns = []
                for col in getattr(table, 'columns', []):
                    if hasattr(col, 'name'):
                        columns.append(col.name)
                    elif isinstance(col, dict) and 'name' in col:
                        columns.append(col['name'])
                    else:
                        columns.append(str(col))
                
                # Process rows
                processed_rows = []
                raw_rows = getattr(table, 'rows', [])
                
                for row in raw_rows:
                    processed_row = []
                    for cell in row:
                        if cell is None:
                            processed_row.append("NULL")
                        elif isinstance(cell, (str, int, float, bool)):
                            processed_row.append(str(cell))
                        else:
                            processed_row.append(str(cell))
                    processed_rows.append(processed_row)
                
                tables.append({
                    'columns': columns,
                    'rows': processed_rows
                })
            
            # Create HTML table
            results_html = '<div class="results success">'
            results_html += f'<h3>✅ Query executed successfully! Found {len(tables)} table(s):</h3>'
            
            for i, table in enumerate(tables):
                results_html += f'<h4>Table {i+1} ({len(table["rows"])} rows):</h4>'
                if table['columns'] and table['rows']:
                    results_html += '<table>'
                    results_html += '<tr>' + ''.join(f'<th>{col}</th>' for col in table['columns']) + '</tr>'
                    for row in table['rows']:
                        results_html += '<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>'
                    results_html += '</table>'
                else:
                    results_html += '<p>No data returned</p>'
            
            results_html += '</div>'
            
        else:
            error_msg = getattr(response, 'partial_error', 'Query failed')
            results_html = f'<div class="results error"><h3>❌ Query Failed:</h3><p>{error_msg}</p></div>'
        
    except Exception as e:
        results_html = f'<div class="results error"><h3>❌ Error:</h3><p>{str(e)}</p></div>'
    
    return HTML_TEMPLATE.replace("{{ results }}", results_html)

if __name__ == "__main__":
    print("🚀 Starting Enhanced KQL Query Interface...")
    print("📱 Open your browser to: http://localhost:8080")
    print("🛑 Press Ctrl+C to stop")
    uvicorn.run(app, host="0.0.0.0", port=8080)
