# main.py
"""
CLI entry point for the Azure Monitor MCP Agent.
"""

import click
from azure_agent.monitor_client import AzureMonitorAgent
import openai  # Add this import at the top
from datetime import datetime, timedelta, UTC

@click.group()
def cli():
    """Azure Monitor MCP Agent CLI"""
    pass

@cli.command()
@click.option('--workspace-id', required=True, help='Log Analytics Workspace ID (GUID)')
@click.option('--query', required=False, help='KQL query to run')
@click.option('--ask', required=False, help='Ask a question in natural language (will be translated to KQL)')
@click.option('--timespan', default=None, help='ISO8601 timespan (e.g., P1D for 1 day)')
def query(workspace_id, query, ask, timespan):
    """Run a KQL query or a natural language question against a Log Analytics workspace."""
    # If timespan is not provided, use last 24 hours as a tuple (start_time, end_time)
    if not timespan:
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=1)
        timespan_value = (start_time, end_time)
    else:
        timespan_value = timespan

    # If --ask is provided, use OpenAI to translate NL to KQL
    if ask:
        kql_query = translate_nl_to_kql_with_retries(ask, workspace_id)
        click.echo({'generated_kql': kql_query})  # Show the generated KQL for debugging
        # Check if KQL is valid (not empty or error)
        if not kql_query or kql_query.strip() == '' or kql_query.strip().startswith('// Error'):
            click.echo({"error": "Failed to generate a valid KQL query from natural language input."})
            return
    elif query:
        kql_query = query
    else:
        click.echo({"error": "You must provide either --query or --ask."})
        return
    agent = AzureMonitorAgent()
    result = agent.query_log_analytics(workspace_id, kql_query, timespan_value)
    # Defensive: handle both dict and string result
    if isinstance(result, dict) and 'tables' in result and result['tables']:
        for table in result['tables']:
            # Support both dict and list for columns
            columns = table.get('columns', [])
            if columns and isinstance(columns[0], dict):
                # Azure SDK style: list of dicts with 'name'
                columns = [col['name'] for col in columns if isinstance(col, dict) and 'name' in col]
            elif columns and isinstance(columns[0], str):
                # REST API style: list of column names as strings
                columns = columns
            else:
                columns = []
            rows = table.get('rows', [])
            if columns:
                click.echo(' | '.join(columns))
                click.echo('-' * (len(' | '.join(columns))))
            for row in rows:
                # row is a list of values
                click.echo(' | '.join(str(cell) for cell in row))
    else:
        click.echo(result)


# Helper function to translate NL to KQL using Azure OpenAI REST API

def translate_nl_to_kql(nl_question):
    """
    Translate a natural language question to KQL using Azure OpenAI Service REST API.
    Requires the following environment variables to be set:
    - AZURE_OPENAI_ENDPOINT: The endpoint URL of your Azure OpenAI resource
    - AZURE_OPENAI_KEY: The key for your Azure OpenAI resource
    - AZURE_OPENAI_DEPLOYMENT: The deployment name for your model (e.g., 'gpt-35-turbo')
    """
    import os
    import requests
    import json
    # First, check the examples file for a matching prompt
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_KEY")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo")
    if not endpoint or not api_key:
        return "// Error: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY must be set in the environment."
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-12-01-preview"
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    system_prompt = """You are an expert in Azure Log Analytics and Kusto Query Language (KQL).
    Your task is to translate natural language questions into valid KQL queries that can be run on a Log Analytics workspace.
    If the user asks for totals, counts, averages, or similar aggregations, use the appropriate summarize/aggregation operator in KQL.
    Only return the KQL query, no explanation, no comments, no extra text.

    Scenario-Specific NL-to-KQL Routing:
    ------------------------------------
    - When a user provides a natural language (NL) question, you should:
      1. Analyze the NL question to determine which Application Insights entity or scenario it relates to (e.g., requests, exceptions, traces).
      2. Route the NL question to the appropriate specialized NL-to-KQL tool:
         - For requests-related questions (AppRequests): use the logic and examples from `nl_to_kql_requests.py` and `kql_examples_requests.md`.
         - For exceptions-related questions (AppExceptions): use the logic and examples from `nl_to_kql_exceptions.py` and `kql_examples_exceptions.md`.
         - For traces/logs-related questions (AppTraces): use the logic and examples from `nl_to_kql_traces.py` and `kql_examples_traces.md`.
         - For other scenarios/entities, use the generic OpenAI-based translation logic.
      3. Each specialized tool should reference the corresponding KQL example and metadata files (e.g., `kql_examples_requests.md`, `app_exceptions_metadata.md`).
      4. If the scenario is ambiguous or cannot be answered with KQL, don't create a kql query, and return an error message indicating ambiguity and starting with "// Error: ".

    Important Notes:
    - When adding new entities/scenarios, create a new NL-to-KQL tool and KQL example file, and update this routing logic accordingly.
    - Do NOT implement the routing logic in code unless specifically requested. These are instructions for future maintainers and agent developers.
    - Always return a valid KQL query that can be run against a Log Analytics workspace.
    - Do not return any explanations, comments, or additional text in the response.
    - Use the metadata files (e.g., `app_exceptions_metadata.md`) to understand the structure of the Application Insights tables and columns.
    - Use the KQL examples files (e.g., `kql_examples_requests.md`, `kql_examples_exceptions.md`, `kql_examples_traces.md`) to understand how to construct queries for specific scenarios.
    - some tables have a column named 'ItemCount' which denotes the number of telemetry items represented by a single sample item. When performing aggregations, you should sum by ItemCount to get the total number of items. """

    prompt = f"""

Question: {nl_question}
KQL:"""
    data = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        result = response.json()
        kql = result["choices"][0]["message"]["content"].strip()
        # Never return a query that is only a table name
        if kql.lower() in ["usage", "heartbeat", "event"]:
            return "// Error: Refusing to run a query that is only a table name. Please ask a more specific question."
        # Remove any leading/trailing non-KQL text
        # kql = kql.split('\n')[0] if '\n' in kql else kql
        return kql
    except Exception as e:
        return f"// Error translating NL to KQL: {str(e)}"

def is_valid_kql(workspace_id, kql_query):
    """
    Checks if a KQL query is valid by attempting to run it with a very short timespan and catching syntax errors.
    Returns True if valid, False otherwise.
    """
    from azure_agent.monitor_client import AzureMonitorAgent
    agent = AzureMonitorAgent()
    # Use a short timespan to minimize data scanned
    try:
        result = agent.query_log_analytics(workspace_id, kql_query, timespan=("2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"))
        # If the result contains an error related to syntax, return False
        if isinstance(result, dict) and 'error' in result and result['error']:
            error_msg = str(result['error']).lower()
            if 'syntax' in error_msg or 'parse' in error_msg or 'invalid' in error_msg:
                return False
        return True
    except Exception as e:
        if 'syntax' in str(e).lower() or 'parse' in str(e).lower() or 'invalid' in str(e).lower():
            return False
        return True

def translate_nl_to_kql_with_retries(nl_question, workspace_id, max_attempts=3):
    """
    Attempts to generate a valid KQL query from a natural language question, up to max_attempts times.
    Returns the valid KQL query or an error message after 3 failed attempts.
    """
    for attempt in range(max_attempts):
        kql_query = translate_nl_to_kql(nl_question)
        print(f"[translate_nl_to_kql] Returned KQL: {kql_query}")
        if not kql_query or kql_query.strip() == '' or kql_query.strip().startswith('// Error'):
            continue
        if is_valid_kql(workspace_id, kql_query):
            return kql_query
    return f"// Error: Failed to generate a valid KQL query for: '{nl_question}' after {max_attempts} attempts."

if __name__ == '__main__':
    cli()
