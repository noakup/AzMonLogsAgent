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
from datetime import datetime
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the KQL agent
from nl_agent import KQLAgent

app = Flask(__name__)

# Global agent instance
agent = None
workspace_id = None

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
        
        # Create explanation prompt
        explanation_prompt = f"Explain these query results for the question '{original_question}': {query_result}"
        
        # Run the async explanation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                agent.process_natural_language(explanation_prompt)
            )
            return jsonify({
                'success': True,
                'explanation': result,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        finally:
            loop.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)        })

@app.route('/api/examples/<scenario>')
def get_examples(scenario):
    """Get example queries for a specific scenario"""
    try:
        import os
          # Map scenarios to example files
        scenario_files = {
            'requests': 'app_requests_kql_examples.md',
            'exceptions': 'app_exceptions_kql_examples.md',
            'traces': 'app_traces_kql_examples.md',
            'dependencies': 'app_dependencies_kql_examples.md',
            'custom_events': 'app_custom_events_kql_examples.md',
            'page_views': 'app_page_views_kql_examples.md',
            'performance': 'app_performance_kql_examples.md',
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
                'file': 'app_requests_kql_examples.md',
                'category': 'Application Insights',
                'description': 'HTTP requests to your application'
            },
            'AppExceptions': {
                'file': 'app_exceptions_kql_examples.md', 
                'category': 'Application Insights',
                'description': 'Exceptions thrown by your application'
            },
            'AppTraces': {
                'file': 'app_traces_kql_examples.md',
                'category': 'Application Insights', 
                'description': 'Custom trace logs from your application'
            },
            'AppDependencies': {
                'file': 'app_dependencies_kql_examples.md',
                'category': 'Application Insights',
                'description': 'External dependencies called by your application'
            },
            'AppPageViews': {
                'file': 'app_page_views_kql_examples.md',
                'category': 'Application Insights',
                'description': 'Page views in your web application'
            },
            'AppCustomEvents': {
                'file': 'app_custom_events_kql_examples.md',
                'category': 'Application Insights', 
                'description': 'Custom events tracked by your application'
            },
            'AppPerformanceCounters': {
                'file': 'app_performance_kql_examples.md',
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
                    },                    'examples': [
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