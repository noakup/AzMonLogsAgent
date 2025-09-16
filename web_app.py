#!/usr/bin/env python3
"""
Web Interface for Natural Language KQL Agent
A Flask web application that provides a user-friendly interface for the KQL agent
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import asyncio
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
import threading

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


app = Flask(__name__)


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
    """Suggest example queries for a given resource type, dynamically discovered from NGSchema and app_insights_capsule."""
    try:
        import glob
        data = request.get_json()
        resource_type = data.get('resource_type', '').strip()
        if not resource_type:
            return jsonify({'success': False, 'error': 'Resource type is required'})

        # Dynamically build mapping: resource_type -> example file
        example_file = None
        # 1. Search NGSchema for resource type folders with kql_examples.md
        ngschema_dir = os.path.join(os.path.dirname(__file__), 'NGSchema')
        if os.path.exists(ngschema_dir):
            for root, dirs, files in os.walk(ngschema_dir):
                for d in dirs:
                    if d.lower() == resource_type.replace(' ', '').lower():
                        kql_files = glob.glob(os.path.join(root, d, '*_kql_examples.md'))
                        if kql_files:
                            example_file = kql_files[0]
                            break
                if example_file:
                    break
        # 2. Fallback: search app_insights_capsule/kql_examples
        if not example_file:
            capsule_dir = os.path.join(os.path.dirname(__file__), 'app_insights_capsule', 'kql_examples')
            if os.path.exists(capsule_dir):
                kql_files = glob.glob(os.path.join(capsule_dir, '*_kql_examples.md'))
                for f in kql_files:
                    # Try to match resource_type in filename
                    if resource_type.replace(' ', '').lower() in os.path.basename(f).lower():
                        example_file = f
                        break
        # 3. Fallback: usage_kql_examples.md for Usage Analytics
        if not example_file and resource_type.lower() == 'usage analytics':
            usage_file = os.path.join(os.path.dirname(__file__), 'usage_kql_examples.md')
            if os.path.exists(usage_file):
                example_file = usage_file

        examples = []
        if example_file and os.path.exists(example_file):
            with open(example_file, 'r', encoding='utf-8') as f:
                content = f.read()
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('- '):
                    examples.append(line[2:].strip())
                elif line.startswith('# '):
                    continue
            # Fallback to generic if not enough
            if len(examples) < 5:
                examples.extend(GENERIC_EXAMPLES.get(resource_type, [])[:5-len(examples)])
        else:
            # Use generic examples if file not found
            examples = GENERIC_EXAMPLES.get(resource_type, [])

        examples = examples[:8]

        return jsonify({
            'success': True,
            'resource_type': resource_type,
            'examples': examples,
            'count': len(examples),
            'source_file': example_file or 'generic',
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# New endpoint to fetch and print workspace schema on demand
@app.route('/api/fetch-workspace-schema', methods=['POST'])
def fetch_workspace_schema():
    """Fetch workspace schema and print to console only."""
    global workspace_id
    try:
        data = request.get_json()
        workspace = data.get('workspace_id', '').strip()
        if not workspace:
            return jsonify({'success': False, 'error': 'Workspace ID is required'})
        threading.Thread(target=_fetch_workspace_tables, args=(workspace,), daemon=True).start()
        return jsonify({'success': True, 'message': f'Workspace schema fetch started for {workspace}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Global agent instance
agent = None
workspace_id = None
_workspace_schema_cache = {}


def _fetch_workspace_tables(workspace: str):
    """Fetch and print workspace table list (best-effort, console only).

    Uses a broad union query over last 7 days to enumerate tables that emitted data.
    This can be expensive in very large workspaces; consider optimization later.
    Results are cached for the process lifetime to avoid repeated cost.
    """
    if not workspace:
        print("[Workspace Schema] No workspace ID provided.")
        return
    if workspace in _workspace_schema_cache:
        print(f"[Workspace Schema] Cached tables for {workspace}: {_workspace_schema_cache[workspace]['count']} tables")
        return
    if LogsQueryClient is None or DefaultAzureCredential is None:
        print("[Workspace Schema] Azure Monitor SDK not available; skipping schema fetch.")
        return
    try:
        print(f"[Workspace Schema] Starting fetch for workspace: {workspace}")
        credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
        print(f"[Workspace Schema] Credential type: {type(credential).__name__}")
        client = LogsQueryClient(credential)
        query = "union withsource=__KQLAgentTableName__ * | summarize RowCount=count() by __KQLAgentTableName__ | sort by __KQLAgentTableName__ asc"
        resp = client.query_workspace(workspace_id=workspace, query=query, timespan=timedelta(days=7))
        print(f"[Workspace Schema] API response status: {getattr(resp, 'status', 'N/A')}")
        if hasattr(resp, 'error') and resp.error:
            print(f"[Workspace Schema] API error: {resp.error}")
        tables = []
        table_resource_map = {}
        # Try to parse manifest for resource type info
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
                    # Prefer dataTypeId, fallback to first category
                    resource_type = dtype or (cats[0] if cats else '')
                    table_resource_map[tname] = resource_type
            except Exception as e:
                print(f"[Workspace Schema] Manifest parse error: {e}")
        if hasattr(resp, 'tables') and resp.tables:
            first = resp.tables[0]
            rows = getattr(first, 'rows', [])
            print(f"[Workspace Schema] Raw rows returned: {len(rows)}")
            for row in rows:
                if row and row[0]:
                    tname = str(row[0])
                    tables.append(tname)
        else:
            print(f"[Workspace Schema] No tables found in response for workspace {workspace}")
        # Build enriched table info
        enriched_tables = []
        for t in tables:
            enriched_tables.append({
                "name": t,
                "resource_type": table_resource_map.get(t, "Unknown")
            })
        _workspace_schema_cache[workspace] = {
            "tables": enriched_tables,
            "count": len(enriched_tables),
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        print(f"[Workspace Schema] Retrieved {len(enriched_tables)} tables for {workspace}")
        if enriched_tables:
            for info in enriched_tables:
                print(f"  - {info['name']} [{info['resource_type']}]")
    except Exception as e:
        print(f"[Workspace Schema] Exception during table enumeration for {workspace}: {e}")
        import traceback as tb
        print(tb.format_exc())

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
        # Fire background thread to enumerate workspace tables (console only)
        threading.Thread(target=_fetch_workspace_tables, args=(workspace_id,), daemon=True).start()
        
        return jsonify({
            'success': True, 
            'message': f'Agent initialized for workspace: {workspace_id}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Failed to setup workspace: {str(e)}'
        })

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
            return jsonify({
                'success': True,
                'result': result,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
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

@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    """Test the workspace connection"""
    global agent
    
    try:
        if not agent:
            return jsonify({
                'success': False, 
                'error': 'Agent not initialized. Please setup workspace first.'
            })
        
        # Run the async connection test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                agent.process_natural_language("test my workspace connection")
            )
            return jsonify({
                'success': True,
                'result': result,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        finally:
            loop.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# Category-specific examples route removed - examples now used internally for AI translation only

@app.route('/api/explain', methods=['POST'])
def explain_results():
    """Explain the results of a previous query"""
    global agent
    
    try:
        if not agent:
            return jsonify({
                'success': False, 
                'error': 'Agent not initialized. Please setup workspace first.'
            })
        
        data = request.get_json()
        query_result = data.get('query_result', '')
        original_question = data.get('original_question', '')
        
        if not query_result:
            return jsonify({'success': False, 'error': 'Query result is required for explanation'})
        
        # Run the async explanation using the dedicated explain_results method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            explanation = loop.run_until_complete(
                agent.explain_results(query_result, original_question)
            )
            return jsonify({
                'success': True,
                'explanation': explanation,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        finally:
            loop.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/examples/<scenario>')
def get_examples(scenario):
    """Get example queries for a specific scenario"""
    try:
        import os
    # Map scenarios to example files
        scenario_files = {
            'requests': 'app_insights_capsule/kql_examples/app_requests_kql_examples.md',
            'exceptions': 'app_insights_capsule/kql_examples/app_exceptions_kql_examples.md',
            'traces': 'app_insights_capsule/kql_examples/app_traces_kql_examples.md',
            'dependencies': 'app_insights_capsule/kql_examples/app_dependencies_kql_examples.md',
            'custom_events': 'app_insights_capsule/kql_examples/app_custom_events_kql_examples.md',
            'page_views': 'app_insights_capsule/kql_examples/app_page_views_kql_examples.md',
            'performance': 'app_insights_capsule/kql_examples/app_performance_kql_examples.md',
            'usage': 'usage_kql_examples.md'
        }
        
        if scenario not in scenario_files:
            return jsonify({
                'success': False,
                'error': f'Unknown scenario: {scenario}'
            })
        
        filename = scenario_files[scenario]
        
        if not os.path.exists(filename):
            return jsonify({
                'success': False,
                'error': f'Example file not found: {filename}'
            })
        
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
    print("🚀 Starting server on http://localhost:8080")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=8080)
    except KeyboardInterrupt:
        print("\n🛑 Web Interface stopped")
    except Exception as e:
        print(f"❌ Error starting web interface: {e}")
        import traceback
        traceback.print_exc()