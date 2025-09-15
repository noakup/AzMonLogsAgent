from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from mcp_agent_lib import Agent, Model, Request, Response
from pydantic import BaseModel
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus

# Load environment variables
load_dotenv()

app = FastAPI()

class KQLQueryModel(Model):
    """Model for executing KQL queries against Azure Log Analytics."""
    
    def __init__(self):
        super().__init__(
            name="kql-query",
            description="Execute KQL queries against Azure Log Analytics workspaces",
            parameters={
                "workspace_id": {
                    "type": "string",
                    "description": "The Log Analytics workspace ID (GUID)",
                },
                "query": {
                    "type": "string",
                    "description": "The KQL query to execute",
                },
                "timespan": {
                    "type": "string",
                    "description": "Optional ISO8601 timespan (e.g., P1D for 1 day)",
                    "optional": True,
                }
            }
        )
        # Initialize Azure Monitor client
        try:
            self.credential = DefaultAzureCredential()
            self.client = LogsQueryClient(self.credential)
        except Exception as e:
            print(f"Error initializing Azure credentials: {e}")
            raise

    async def process(self, request: Request) -> Response:
        try:
            # Extract parameters
            workspace_id = request.parameters["workspace_id"]
            kql_query = request.parameters["query"]
            timespan = request.parameters.get("timespan")  # Optional

            # Execute query
            response = self.client.query_workspace(
                workspace_id=workspace_id,
                query=kql_query,
                timespan=timespan
            )

            # Format response
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
                    
                    table_dict = {
                        'name': getattr(table, 'name', ''),
                        'columns': columns,
                        'rows': getattr(table, 'rows', [])
                    }
                    tables.append(table_dict)
                
                return Response(
                    content={"tables": tables},
                    format="json"
                )
            else:
                return Response(
                    content={"error": getattr(response, 'partial_error', 'Query failed')},
                    format="json"
                )

        except Exception as e:
            return Response(
                content={"error": str(e)},
                format="json"
            )

# Initialize the model
model = KQLQueryModel()

# MCP endpoint
@app.post("/process")
async def process(request: Request) -> Response:
    return await model.process(request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
