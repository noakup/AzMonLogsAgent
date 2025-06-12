# azure_agent/monitor_client.py
"""
This module provides a class for authenticating and querying Azure Monitor (Log Analytics) using the Azure SDK.
All methods are heavily commented for clarity and learning.
"""
from azure.identity import AzureCliCredential, DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus

class AzureMonitorAgent:
    def __init__(self):
        """
        Initialize the AzureMonitorAgent with Azure CLI credentials if available,
        otherwise fall back to DefaultAzureCredential.
        """
        try:
            # Try Azure CLI credentials first
            self.credential = AzureCliCredential()
            # This will raise if az is not installed or not logged in
            _ = self.credential.get_token("https://management.azure.com/.default")
        except Exception:
            # Fallback to DefaultAzureCredential (env vars, managed identity, etc.)
            self.credential = DefaultAzureCredential()
        self.client = LogsQueryClient(self.credential)

    def query_log_analytics(self, workspace_id, kql_query, timespan=None):
        """
        Run a KQL query against a Log Analytics workspace.
        Args:
            workspace_id (str): The Log Analytics workspace ID (GUID).
            kql_query (str): The Kusto Query Language (KQL) query to run.
            timespan (str or tuple): ISO8601 duration or (start, end) tuple.
        Returns:
            dict: Query results or error message.
        """
        try:
            response = self.client.query_workspace(
                workspace_id=workspace_id,
                query=kql_query,
                timespan=timespan
            )
            # Convert LogsTable objects to dicts manually
            if response.status == LogsQueryStatus.SUCCESS:
                tables = []
                for table in response.tables:
                    # Defensive: skip if table is not a LogsTable object
                    if not hasattr(table, 'name') or not hasattr(table, 'columns') or not hasattr(table, 'rows'):
                        continue
                    # Defensive: columns may be a list of dicts or strings, handle both
                    columns = []
                    for col in getattr(table, 'columns', []):
                        if hasattr(col, 'name'):
                            columns.append(col.name)
                        elif isinstance(col, dict) and 'name' in col:
                            columns.append(col['name'])
                        else:
                            columns.append(str(col))
                    table_dict = {
                        'name': getattr(table, 'name', ''),
                        'columns': columns,
                        'rows': getattr(table, 'rows', [])
                    }
                    tables.append(table_dict)
                return {"tables": tables}
            else:
                return {"error": getattr(response, 'partial_error', None)}
        except Exception as e:
            return {"error": str(e)}
