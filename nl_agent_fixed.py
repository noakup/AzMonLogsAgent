#!/usr/bin/env python3
"""
Natural Language Agent for KQL Queries using MCP Server
This agent translates natural language questions into MCP tool calls
"""

import asyncio
import json
import subprocess
import sys
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import enhanced translation function
from enhanced_translation import translate_nl_to_kql_enhanced as translate_nl_to_kql

class KQLAgent:
    """Agent that processes natural language and calls MCP server tools"""
    
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        self.mcp_process = None
        
    async def start_mcp_server(self):
        """Start the MCP server as a subprocess"""
        try:
            self.mcp_process = subprocess.Popen([
                sys.executable, "my-first-mcp-server/mcp_server.py"
            ], 
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
            )
            print("🤖 MCP Server started")
            return True
        except Exception as e:
            print(f"❌ Failed to start MCP server: {e}")
            return False
    
    def stop_mcp_server(self):
        """Stop the MCP server"""
        if self.mcp_process:
            self.mcp_process.terminate()
            self.mcp_process.wait()
            print("🛑 MCP Server stopped")
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool and return the result"""
        
        # For this implementation, we'll call the tools directly since MCP client setup is complex
        # Import the tools from the MCP server
        sys.path.append('my-first-mcp-server')
        
        try:
            if tool_name == "execute_kql_query":
                from azure.identity import DefaultAzureCredential
                from azure.monitor.query import LogsQueryClient, LogsQueryStatus
                
                # Initialize client
                credential = DefaultAzureCredential()
                client = LogsQueryClient(credential)
                
                workspace_id = arguments["workspace_id"]
                query = arguments["query"]
                timespan_hours = arguments.get("timespan_hours")
                
                # Set up timespan only if specified (None means query has its own time filters)
                timespan = None
                if timespan_hours is not None:
                    end_time = datetime.now(timezone.utc)
                    start_time = end_time - timedelta(hours=timespan_hours)
                    timespan = (start_time, end_time)
                    print(f"🔍 Executing query: {query}")
                    print(f"📅 Timespan: Last {timespan_hours} hour(s)")
                else:
                    print(f"🔍 Executing query: {query}")
                    print(f"📅 Using query's own time range")
                
                # Execute query
                response = client.query_workspace(
                    workspace_id=workspace_id,
                    query=query,
                    timespan=timespan
                )
                
                # Process results
                if response.status == LogsQueryStatus.SUCCESS:
                    tables = []
                    for i, table in enumerate(response.tables):
                        columns = []
                        for col in getattr(table, 'columns', []):
                            if hasattr(col, 'name'):
                                columns.append(col.name)
                            elif isinstance(col, dict) and 'name' in col:
                                columns.append(col['name'])
                            else:
                                columns.append(str(col))
                        
                        # Process rows
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
                                    processed_row.append(str(cell))
                            processed_rows.append(processed_row)
                        
                        table_dict = {
                            'name': getattr(table, 'name', f'table_{i}'),
                            'columns': columns,
                            'rows': processed_rows,
                            'row_count': len(processed_rows)
                        }
                        tables.append(table_dict)
                    
                    return {"success": True, "tables": tables}
                else:
                    error_msg = getattr(response, 'partial_error', 'Query failed')
                    return {"success": False, "error": str(error_msg)}
                    
            elif tool_name == "get_kql_examples":
                scenario = arguments["scenario"]
                
                # Map scenarios to example files
                example_files = {
                    "requests": "app_requests_kql_examples.md",
                    "exceptions": "app_exceptions_kql_examples.md", 
                    "traces": "app_traces_kql_examples.md",
                    "dependencies": "app_dependencies_kql_examples.md",
                    "custom_events": "app_custom_events_kql_examples.md",
                    "performance": "app_performance_kql_examples.md",
                    "usage": "usage_kql_examples.md"
                }
                
                filename = example_files.get(scenario)
                if filename and os.path.exists(filename):
                    with open(filename, "r", encoding="utf-8") as f:
                        content = f.read()
                    return {"success": True, "examples": content}
                else:
                    return {"success": False, "error": f"No examples found for scenario: {scenario}"}
            
            elif tool_name == "validate_workspace_connection":
                from azure.identity import DefaultAzureCredential
                from azure.monitor.query import LogsQueryClient, LogsQueryStatus
                
                credential = DefaultAzureCredential()
                client = LogsQueryClient(credential)
                
                workspace_id = arguments["workspace_id"]
                test_query = "print 'Connection test successful'"
                
                try:
                    response = client.query_workspace(
                        workspace_id=workspace_id,
                        query=test_query,
                        timespan=None
                    )
                    
                    if response.status == LogsQueryStatus.SUCCESS:
                        return {"success": True, "message": f"✅ Successfully connected to workspace: {workspace_id}"}
                    else:
                        error_msg = getattr(response, 'partial_error', 'Unknown error')
                        return {"success": False, "error": f"❌ Failed to connect: {error_msg}"}
                        
                except Exception as e:
                    return {"success": False, "error": f"❌ Connection test failed: {str(e)}"}
            
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error calling tool {tool_name}: {str(e)}"}

    def format_table_results(self, tables: List[Dict]) -> Dict:
        """Format query results as structured data for web display"""
        if not tables:
            return {
                "type": "no_data",
                "message": "No data returned"
            }
        
        formatted_tables = []
        for i, table in enumerate(tables):
            columns = table.get('columns', [])
            rows = table.get('rows', [])
            row_count = table.get('row_count', len(rows))
            
            formatted_table = {
                "table_number": i + 1,
                "row_count": row_count,
                "columns": columns,
                "rows": rows if columns and rows else [],
                "has_data": bool(columns and rows)
            }
            formatted_tables.append(formatted_table)
        
        return {
            "type": "table_data",
            "tables": formatted_tables,
            "total_tables": len(formatted_tables)
        }
    
    def detect_query_timespan(self, kql_query):
        """
        Detect if a KQL query already contains time filters and determine appropriate timespan
        Returns None if query has time filters, otherwise returns default timespan_hours
        """
        if not kql_query:
            return 1
        
        # Convert to lowercase for case-insensitive matching
        query_lower = kql_query.lower()
        
        # Common time filter patterns in KQL
        time_filter_patterns = [
            'timegenerated >',
            'timegenerated >=', 
            'timegenerated between',
            'ago(',
            'startofday(',
            'endofday(',
            'startofweek(',
            'endofweek(',
            'startofmonth(',
            'endofmonth(',
            'datetime(',
            'now()'
        ]
        
        # Check if query contains any time filter patterns
        has_time_filter = any(pattern in query_lower for pattern in time_filter_patterns)
        
        if has_time_filter:
            print("🕐 Query contains time filters - using query's own time range")
            return None  # Let the query define its own time range
        else:
            print("🕐 No time filters detected - applying default 1 hour timespan")
            return 1  # Default to 1 hour for queries without time filters
    
    async def process_natural_language(self, question: str) -> str:
        """Process natural language question and return results"""
        
        print(f"💬 Question: {question}")
        print("🤔 Processing...")
        
        # Step 1: Check if it's a request for examples
        question_lower = question.lower()
        
        if "example" in question_lower:
            # Determine scenario from question
            scenarios = ["requests", "exceptions", "traces", "dependencies", "custom_events", "performance", "usage"]
            
            for scenario in scenarios:
                if scenario in question_lower:
                    print(f"📚 Getting examples for: {scenario}")
                    result = await self.call_mcp_tool("get_kql_examples", {"scenario": scenario})
                    
                    if result["success"]:
                        # Return first 1000 characters of examples
                        examples = result["examples"]
                        if len(examples) > 1000:
                            examples = examples[:1000] + "\n... (truncated)"
                        return f"📚 KQL Examples for {scenario.title()}:\n\n{examples}"
                    else:
                        return f"❌ Error getting examples: {result['error']}"
            
            return "❌ Please specify which type of examples you want: requests, exceptions, traces, dependencies, custom_events, performance, or usage"
        
        # Step 2: Check if it's a connection test
        if "test" in question_lower and ("connection" in question_lower or "workspace" in question_lower):
            print("🔗 Testing workspace connection...")
            result = await self.call_mcp_tool("validate_workspace_connection", {"workspace_id": self.workspace_id})
            
            if result["success"]:
                return result["message"]
            else:
                return f"❌ Connection test failed: {result['error']}"
        
        # Step 3: Translate natural language to KQL
        print("🔄 Translating natural language to KQL (with retry logic)...")
        
        try:
            kql_query = translate_nl_to_kql(question)
            
            if not kql_query or kql_query.strip() == '' or kql_query.strip().startswith('// Error'):
                return f"❌ Could not translate question to KQL after retries: {question}"
            
            print(f"📝 Generated KQL: {kql_query}")
            
            # Detect timespan from query
            timespan_hours = self.detect_query_timespan(kql_query)
            
            # Step 4: Execute the KQL query
            result = await self.call_mcp_tool("execute_kql_query", {
                "workspace_id": self.workspace_id,
                "query": kql_query,
                "timespan_hours": timespan_hours  # Use detected timespan
            })
            
            if result["success"]:
                tables = result["tables"]
                formatted_results = self.format_table_results(tables)
                
                # Return structured data for web interface
                return {
                    "type": "query_success",
                    "kql_query": kql_query,
                    "data": formatted_results,
                    "message": "✅ Query executed successfully"
                }
            else:
                return {
                    "type": "query_error", 
                    "kql_query": kql_query,
                    "error": result['error'],
                    "message": f"❌ Query execution failed: {result['error']}"
                }
                
        except Exception as e:
            return f"❌ Error processing question: {str(e)}"

async def main():
    """Main interactive loop"""
    
    print("🤖 Natural Language KQL Agent")
    print("=" * 50)
    
    # Get workspace ID
    workspace_id = input("Enter your Log Analytics Workspace ID: ").strip()
    if not workspace_id:
        print("❌ Workspace ID is required")
        return
    
    # Initialize agent
    agent = KQLAgent(workspace_id)
    
    print(f"\n✅ Agent initialized for workspace: {workspace_id}")
    print("\n💡 You can ask questions like:")
    print("   - 'Show me failed requests from the last hour'")
    print("   - 'Get examples for exceptions'")
    print("   - 'Test my workspace connection'")
    print("   - 'What are the top 5 slowest API calls?'")
    print("   - 'Show me recent heartbeat data'")
    print("\n💬 Type 'quit' to exit\n")
    
    try:
        while True:
            question = input("🗣️  Ask me anything: ").strip()
            
            if question.lower() in ['quit', 'exit', 'bye']:
                break
            
            if not question:
                continue
            
            print()
            response = await agent.process_natural_language(question)
            print(response)
            print("\n" + "-" * 50 + "\n")
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    finally:
        agent.stop_mcp_server()

if __name__ == "__main__":
    asyncio.run(main())
