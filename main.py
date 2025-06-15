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
If the natural language question is related to ingestion volume, billing, usage or something similar, refer to the file "usage_kql_examples.md" to extend your knowledge on this.
If the questions is about Application Insights, exceptions, requests, traces, dependencies, or events - it is CRITICAL that you refer to "kql_examples_app_insights_over_la.md" to extend your knowledge on this. This is because Application Insights data stored in a Log Analytics workspace has different table and column names when they run on Log Analytics worksaces.
Use that file to extend your knowledge on this. For example, instead of using timestamp, these tables use TimeGenerated. Similarly, table names are AppRequests instead of requests etc. Similarly, the column names are different.

Metadata:
Table "AppRequests" contains Application Insights request data.
The names, types, and descriptions of the columns in this table are:
| Column | Type | Description |
|---|---|---|
| AppRoleInstance | string | Role instance of the application. |
| AppRoleName | string | Role name of the application. |
| AppVersion | string | Version of the application. |
| _BilledSize | real | The record size in bytes |
| ClientBrowser | string | Browser running on the client device. |
| ClientCity | string | City where the client device is located. |
| ClientCountryOrRegion | string | Country or region where the client device is located. |
| ClientIP | string | IP address of the client device. |
| ClientModel | string | Model of the client device. |
| ClientOS | string | Operating system of the client device. |
| ClientStateOrProvince | string | State or province where the client device is located. |
| ClientType | string | Type of the client device. |
| DurationMs | real | Number of milliseconds it took the application to handle the request. |
| Id | string | Application-generated, unique request ID. |
| IKey | string | Instrumentation key of the Azure resource. |
| _IsBillable | string | Specifies whether ingesting the data is billable. When _IsBillable is false ingestion isn't billed to your Azure account |
| ItemCount | int | Number of telemetry items represented by a single sample item. |
| Measurements | dynamic | Application-defined measurements. |
| Name | string | Human-readable name of the request. |
| OperationId | string | Application-defined operation ID. |
| OperationName | string | Application-defined name of the overall operation. The OperationName values typically match the Name values for AppRequests. |
| ParentId | string | ID of the parent operation. |
| Properties | dynamic | Application-defined properties. |
| ReferencedItemId | string | Id of the item with additional details about the request. |
| ReferencedType | string | Name of the table with additional details about the request. |
| ResourceGUID | string | Unique, persistent identifier of an Azure resource. |
| _ResourceId | string | A unique identifier for the resource that the record is associated with |
| ResultCode | string | Result code returned by the application after handling the request. |
| SDKVersion | string | Version of the SDK used by the application to generate this telemetry item. |
| SessionId | string | Application-defined session ID. |
| Source | string | Friendly name of the request source, when known. Source is based on the metadata supplied by the caller. |
| SourceSystem | string | The type of agent the event was collected by. For example, OpsManager for Windows agent, either direct connect or Operations Manager, Linux for all Linux agents, or Azure for Azure Diagnostics |
| _SubscriptionId | string | A unique identifier for the subscription that the record is associated with |
| Success | bool | Indicates whether the application handled the request successfully. |
| SyntheticSource | string | Synthetic source of the operation. |
| TenantId | string | The Log Analytics workspace ID |
| TimeGenerated | datetime | Date and time when request processing started. |
| Type | string | The name of the table |
| Url | string | URL of the request. |
| UserAccountId | string | Application-defined account associated with the user. |
| UserAuthenticatedId | string | Persistent string that uniquely represents each authenticated user in the application. |
| UserId | string | Anonymous ID of a user accessing the application. |

Example prompts and KQL queries:
Chart request duration over the last 12 hours:
AppRequests
| where TimeGenerated > ago(12h) 
| summarize avgRequestDuration=avg(DurationMs) by bin(TimeGenerated, 10m), _ResourceId // use a time grain of 10 minutes
| render timechart

Chart Request count over the last day:
AppRequests
| summarize totalCount=sum(ItemCount) by bin(TimeGenerated, 30m), _ResourceId
| render timechart
Response time buckets

Show how many requests are in each performance-bucket:
AppRequests
| summarize requestCount=sum(ItemCount), avgDuration=avg(DurationMs) by PerformanceBucket
| order by avgDuration asc // sort by average request duration
| project-away avgDuration // no need to display avgDuration, we used it only for sorting results
| render barchart

Calculate request count and duration by operations:
AppRequests
| summarize RequestsCount=sum(ItemCount), AverageDuration=avg(DurationMs), percentiles(DurationMs, 50, 95, 99) by OperationName, _ResourceId // you can replace 'OperationName' with another value to segment by a different property
| order by RequestsCount desc // order from highest to lower (descending)
Top 10 countries by traffic

Chart request duration over the last 12 hours:
AppRequests
| where TimeGenerated > ago(12h) 
| summarize avgRequestDuration=avg(DurationMs) by bin(TimeGenerated, 10m), _ResourceId // use a time grain of 10 minutes
| render timechart

Chart Request count over the last day:
AppRequests
| summarize totalCount=sum(ItemCount) by bin(TimeGenerated, 30m), _ResourceId
| render timechart

Show how many requests are in each performance-bucket:
AppRequests
| summarize requestCount=sum(ItemCount), avgDuration=avg(DurationMs) by PerformanceBucket
| order by avgDuration asc // sort by average request duration
| project-away avgDuration // no need to display avgDuration, we used it only for sorting results
| render barchart

Calculate request count and duration by operations:
AppRequests
| summarize RequestsCount=sum(ItemCount), AverageDuration=avg(DurationMs), percentiles(DurationMs, 50, 95, 99) by OperationName, _ResourceId // you can replace 'OperationName' with another value to segment by a different property
| order by RequestsCount desc // order from highest to lower (descending)


Chart the amount of requests from the top 10 countries:
AppRequests
| summarize CountByCountry=count() by ClientCountryOrRegion
| top 10 by CountByCountry
| render piechart

Show me the top 10 failed requests:
AppRequests
| where Success == false
| summarize failedCount=sum(ItemCount) by Name
| top 10 by failedCount desc
| render barchart

Calculate how many times operations failed, and how many users were impacted:
AppRequests
| where Success == false
| summarize failedCount=sum(ItemCount), impactedUsers=dcount(UserId) by OperationName, _ResourceId
| order by failedCount desc

Find which exceptions led to failed requests in the past hour:
AppRequests
| where TimeGenerated > ago(1h) and Success == false
| join kind= inner (
	AppExceptions
	| where TimeGenerated > ago(1h)
  ) on OperationId
| project exceptionType = Type, failedMethod = Method, requestName = Name, requestDuration = DurationMs, _ResourceId

see more examples in the kql_examples_app_insights_over_la.md file.

if the question is unclear or cannot be answered with KQL, return an error message starting with "// Error: " and do not return a KQL query.

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
        if not kql_query or kql_query.strip() == '' or kql_query.strip().startswith('// Error'):
            continue
        if is_valid_kql(workspace_id, kql_query):
            return kql_query
    return f"// Error: Failed to generate a valid KQL query for: '{nl_question}' after {max_attempts} attempts."

if __name__ == '__main__':
    cli()
