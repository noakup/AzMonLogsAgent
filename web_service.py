# web_service.py
"""
Flask-based web service for the Azure Monitor MCP Agent.
Provides a REST API to run KQL queries against Log Analytics workspaces.
"""
from flask import Flask, request, jsonify
from azure_agent.monitor_client import AzureMonitorAgent

app = Flask(__name__)
agent = AzureMonitorAgent()

@app.route('/query', methods=['POST'])
def query():
    """
    POST /query
    JSON body: {"workspace_id": "<GUID>", "query": "<KQL>", "timespan": "P1D"}
    """
    data = request.get_json()
    workspace_id = data.get('workspace_id')
    kql_query = data.get('query')
    timespan = data.get('timespan', 'P1D')
    if not workspace_id or not kql_query:
        return jsonify({"error": "workspace_id and query are required"}), 400
    result = agent.query_log_analytics(workspace_id, kql_query, timespan)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
