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

@app.route('/api/examples/<scenario>')
def get_examples(scenario):
    """Get KQL examples for a specific scenario"""
    global agent
    
    try:
        if not agent:
            return jsonify({
                'success': False, 
                'error': 'Agent not initialized. Please setup workspace first.'
            })
        
        # Run the async examples request
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                agent.process_natural_language(f"get examples for {scenario}")
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

@app.route('/api/status')
def get_status():
    """Get the current status of the agent"""
    global agent, workspace_id
    
    return jsonify({
        'initialized': agent is not None,
        'workspace_id': workspace_id if workspace_id else None,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/explain', methods=['POST'])
def explain_results():
    """Explain query results using OpenAI analysis"""
    global agent
    
    try:
        if not agent:
            return jsonify({
                'success': False, 
                'error': 'Agent not initialized. Please setup workspace first.'
            })
        
        data = request.get_json()
        query_result = data.get('query_result')
        original_question = data.get('original_question', '')
        
        if not query_result:
            return jsonify({'success': False, 'error': 'Query result is required'})
        
        # Run the async explanation
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

@app.route('/api/test-explain', methods=['GET'])
def test_explain():
    """Test the explain functionality with a simple example"""
    global agent
    
    try:
        if not agent:
            return jsonify({
                'success': False, 
                'error': 'Agent not initialized. Please setup workspace first.'
            })
        
        # Create test data
        test_result = {
            "type": "query_success",
            "kql_query": "AppRequests | where ResultCode >= 400 | take 5",
            "data": {
                "type": "table_data",
                "tables": [
                    {
                        "name": "table_0",
                        "columns": ["TimeGenerated", "Name", "ResultCode", "DurationMs"],
                        "rows": [
                            ["2024-06-30T10:15:00Z", "/api/users", 404, 125],
                            ["2024-06-30T10:16:00Z", "/api/orders", 500, 2500],
                            ["2024-06-30T10:17:00Z", "/api/users", 404, 98]
                        ],
                        "row_count": 3
                    }
                ]
            }
        }
        
        # Run the async explanation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            explanation = loop.run_until_complete(
                agent.explain_results(test_result, "Show me failed requests")
            )
            return jsonify({
                'success': True,
                'explanation': explanation,
                'test_data': test_result,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        finally:
            loop.close()
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

if __name__ == '__main__':
    print("🌐 Starting Natural Language KQL Web Interface")
    print("=" * 60)
    print("📍 Web interface will be available at: http://localhost:5000")
    print("🤖 Ready to process natural language KQL questions!")
    print("=" * 60)
    
    # Create templates directory if it doesn't exist
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
