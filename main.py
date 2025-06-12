# main.py
"""
CLI entry point for the Azure Monitor MCP Agent.
Uses Click for argument parsing and command-line interface.
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
        kql_query = translate_nl_to_kql(ask)
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
    Always check the usage_kql_examples.md file for a matching example before calling the LLM. If a matching example is found, return its KQL directly.
    Never return or run a KQL query that is only a table name (e.g., 'Usage').
    Requires the following environment variables to be set:
    - AZURE_OPENAI_ENDPOINT: The endpoint URL of your Azure OpenAI resource
    - AZURE_OPENAI_KEY: The key for your Azure OpenAI resource
    - AZURE_OPENAI_DEPLOYMENT: The deployment name for your model (e.g., 'gpt-35-turbo')
    """
    import os
    import requests
    import json
    # First, check the examples file for a matching prompt
    examples_path = os.path.join(os.path.dirname(__file__), 'usage_kql_examples.md')
    if os.path.exists(examples_path):
        with open(examples_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Look for a matching prompt (case-insensitive, strip whitespace)
            import re
            pattern = re.compile(r'\*\*Prompt:\*\*\s*(.+?)\n\n\*\*KQL:\*\*\s*(.+?)(?:\n|$)', re.DOTALL | re.IGNORECASE)
            matches = pattern.findall(content)
            for prompt, kql in matches:
                if prompt.strip().lower() == nl_question.strip().lower():
                    # Never return a query that is only a table name
                    if kql.strip().lower() in ["usage", "heartbeat", "event"]:
                        return "// Error: Refusing to run a query that is only a table name. Please ask a more specific question."
                    return kql.strip()
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
    prompt = f"""
You are an expert in Azure Log Analytics and Kusto Query Language (KQL).
Translate the following natural language question into a valid KQL query that can be run on a Log Analytics workspace. If the question asks for totals, counts, averages, or similar aggregations, use the appropriate summarize/aggregation operator in KQL. Only return the KQL query, no explanation, no comments, no extra text.

Example:
Question: Show me the total ingestion volume in MB in the last 24 hours based on the Usage table
KQL: Usage | summarize sum(Quantity)

Question: {nl_question}
KQL:"""
    data = {
        "messages": [
            {"role": "system", "content": "You are an expert in Azure Log Analytics and Kusto Query Language (KQL). Translate natural language questions into valid KQL queries only. Use summarize/aggregation operators when the question asks for totals, counts, averages, etc."},
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

if __name__ == '__main__':
    cli()
