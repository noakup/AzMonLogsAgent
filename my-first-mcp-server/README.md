# KQL Query MCP Server

This is a Model Context Protocol (MCP) server that allows you to execute KQL queries against Azure Log Analytics workspaces. It leverages the Azure Monitor Query API to execute queries and return results in a structured format.

## Features

- Execute KQL queries against Azure Log Analytics workspaces
- Support for timespan specification
- Azure authentication using DefaultAzureCredential
- Results returned in a structured JSON format
- Built using FastAPI and the MCP protocol

## Requirements

- Python 3.12 or higher
- Azure subscription
- Azure Log Analytics workspace
- Azure CLI installed and logged in (for DefaultAzureCredential)

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -e .
   ```

## Usage

1. Start the MCP server:
   ```bash
   python mcp_server.py
   ```

   Or start the HTTP REST API server:
   ```bash
   python rest_api.py
   ```

2. The server will listen on `http://localhost:8080`

3. Send requests to the `/process` endpoint with the following JSON structure:
   ```json
   {
     "parameters": {
       "workspace_id": "your-workspace-id",
       "query": "your-kql-query",
       "timespan": "P1D"  // optional, ISO8601 duration
     }
   }
   ```

Example using curl:
```bash
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "workspace_id": "12345678-1234-1234-1234-123456789012",
      "query": "Heartbeat | take 5",
      "timespan": "P1D"
    }
  }'
```

## Response Format

Successful response:
```json
{
  "content": {
    "tables": [
      {
        "name": "table_0",
        "columns": ["column1", "column2"],
        "rows": [
          ["value1", "value2"],
          ["value3", "value4"]
        ]
      }
    ]
  },
  "format": "json"
}
```

Error response:
```json
{
  "content": {
    "error": "Error message"
  },
  "format": "json"
}
```

## Authentication

The server uses DefaultAzureCredential for authentication, which supports:
1. Environment variables
2. Azure CLI credentials
3. Managed Identity
4. Visual Studio Code credentials

Make sure you're logged in with Azure CLI or have appropriate credentials configured before running the server.