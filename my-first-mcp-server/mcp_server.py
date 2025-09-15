#!/usr/bin/env python3
"""
MCP Server for Azure Log Analytics KQL Queries

This is a proper Model Context Protocol (MCP) server that provides tools
for querying Azure Log Analytics workspaces using KQL.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
)
from pydantic import AnyUrl
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kql-mcp-server")

# Initialize Azure Monitor client
try:
    credential = DefaultAzureCredential()
    client = LogsQueryClient(credential)
    logger.info("Azure Monitor client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Azure credentials: {e}")
    raise

server = Server("kql-mcp-server")

def format_table_as_text(table_data: dict) -> str:
    """Format query results as a readable text table"""
    columns = table_data.get('columns', [])
    rows = table_data.get('rows', [])
    
    if not columns or not rows:
        return "No data returned"
    
    # Create header
    header = " | ".join(columns)
    separator = "-" * len(header)
    
    # Create rows
    formatted_rows = []
    for row in rows:
        row_str = " | ".join(str(cell) if cell is not None else "NULL" for cell in row)
        formatted_rows.append(row_str)
    
    return f"{header}\n{separator}\n" + "\n".join(formatted_rows)

def process_query_results(response) -> list:
    """Process Azure Monitor query response into serializable format"""
    tables = []
    
    if response.status == LogsQueryStatus.SUCCESS:
        for i, table in enumerate(response.tables):
            columns = []
            for col in getattr(table, 'columns', []):
                if hasattr(col, 'name'):
                    columns.append(col.name)
                elif isinstance(col, dict) and 'name' in col:
                    columns.append(col['name'])
                else:
                    columns.append(str(col))
            
            # Process rows with type conversion
            processed_rows = []
            raw_rows = getattr(table, 'rows', [])
            
            for row in raw_rows:
                processed_row = []
                for cell in row:
                    if cell is None:
                        processed_row.append(None)
                    elif isinstance(cell, (str, int, float, bool)):
                        processed_row.append(cell)
                    else:
                        # Convert complex types to string
                        processed_row.append(str(cell))
                processed_rows.append(processed_row)
            
            table_dict = {
                'name': getattr(table, 'name', f'table_{i}'),
                'columns': columns,
                'rows': processed_rows,
                'row_count': len(processed_rows)
            }
            tables.append(table_dict)
    
    return tables

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="execute_kql_query",
            description="Execute a KQL query against an Azure Log Analytics workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "The Log Analytics workspace ID (GUID)"
                    },
                    "query": {
                        "type": "string",
                        "description": "The KQL query to execute"
                    },
                    "timespan_hours": {
                        "type": "number",
                        "description": "Number of hours to look back (optional, defaults to 1 hour)",
                        "default": 1
                    }
                },
                "required": ["workspace_id", "query"]
            }
        ),
        Tool(
            name="get_kql_examples",
            description="Get KQL query examples for different Application Insights scenarios",
            inputSchema={
                "type": "object",
                "properties": {
                    "scenario": {
                        "type": "string",
                        "enum": ["requests", "exceptions", "traces", "dependencies", "custom_events", "performance", "usage"],
                        "description": "The Application Insights scenario to get examples for"
                    }
                },
                "required": ["scenario"]
            }
        ),
        Tool(
            name="validate_workspace_connection",
            description="Test connection to an Azure Log Analytics workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "The Log Analytics workspace ID (GUID) to test"
                    }
                },
                "required": ["workspace_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls"""
    
    if name == "execute_kql_query":
        try:
            workspace_id = arguments["workspace_id"]
            query = arguments["query"]
            timespan_hours = arguments.get("timespan_hours", 1)
            
            logger.info(f"Executing KQL query for workspace: {workspace_id}")
            logger.info(f"Query: {query}")
            
            # Set up timespan
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=timespan_hours)
            timespan = (start_time, end_time)
            
            # Execute query
            response = client.query_workspace(
                workspace_id=workspace_id,
                query=query,
                timespan=timespan
            )
            
            # Process results
            tables = process_query_results(response)
            
            if not tables:
                if hasattr(response, 'partial_error') and response.partial_error:
                    error_msg = str(response.partial_error)
                else:
                    error_msg = "No data returned or query failed"
                return [TextContent(type="text", text=f"Error: {error_msg}")]
            
            # Format results as text
            result_text = f"Query executed successfully. Found {len(tables)} table(s):\n\n"
            
            for i, table in enumerate(tables):
                if i > 0:
                    result_text += "\n\n"
                result_text += f"Table {i+1} ({table['row_count']} rows):\n"
                result_text += format_table_as_text(table)
            
            return [TextContent(type="text", text=result_text)]
            
        except Exception as e:
            logger.error(f"Error executing KQL query: {e}")
            return [TextContent(type="text", text=f"Error executing query: {str(e)}")]
    
    elif name == "get_kql_examples":
        try:
            scenario = arguments["scenario"]
            
            # Map scenarios to example files
            example_files = {
                "requests": "../app_insights_capsule/kql_examples/app_requests_kql_examples.md",
                "exceptions": "../app_insights_capsule/kql_examples/app_exceptions_kql_examples.md", 
                "traces": "../app_insights_capsule/kql_examples/app_traces_kql_examples.md",
                "dependencies": "../app_insights_capsule/kql_examples/app_dependencies_kql_examples.md",
                "custom_events": "../app_insights_capsule/kql_examples/app_custom_events_kql_examples.md",
                "performance": "../app_insights_capsule/kql_examples/app_performance_kql_examples.md",
                "usage": "../usage_kql_examples.md"
            }
            
            filename = example_files.get(scenario)
            if not filename:
                return [TextContent(type="text", text=f"No examples found for scenario: {scenario}")]
            
            # Read the example file
            try:
                with open(f"../{filename}", "r", encoding="utf-8") as f:
                    content = f.read()
                return [TextContent(type="text", text=f"KQL Examples for {scenario.title()}:\n\n{content}")]
            except FileNotFoundError:
                return [TextContent(type="text", text=f"Example file not found: {filename}")]
            
        except Exception as e:
            logger.error(f"Error getting KQL examples: {e}")
            return [TextContent(type="text", text=f"Error getting examples: {str(e)}")]
    
    elif name == "validate_workspace_connection":
        try:
            workspace_id = arguments["workspace_id"]
            
            logger.info(f"Testing connection to workspace: {workspace_id}")
            
            # Test with a simple query
            test_query = "print 'Connection test successful'"
            
            response = client.query_workspace(
                workspace_id=workspace_id,
                query=test_query,
                timespan=None
            )
            
            if response.status == LogsQueryStatus.SUCCESS:
                return [TextContent(type="text", text=f"✅ Successfully connected to workspace: {workspace_id}")]
            else:
                error_msg = getattr(response, 'partial_error', 'Unknown error')
                return [TextContent(type="text", text=f"❌ Failed to connect to workspace: {workspace_id}\nError: {error_msg}")]
                
        except Exception as e:
            logger.error(f"Error testing workspace connection: {e}")
            return [TextContent(type="text", text=f"❌ Connection test failed: {str(e)}")]
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    # Import here to avoid issues with event loops
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="kql-mcp-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
