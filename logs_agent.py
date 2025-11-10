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
from nl_to_kql import translate_nl_to_kql as translate_nl_to_kql

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
                    "requests": "app_insights_capsule/kql_examples/app_requests_kql_examples.md",
                    "exceptions": "app_insights_capsule/kql_examples/app_exceptions_kql_examples.md", 
                    "traces": "app_insights_capsule/kql_examples/app_traces_kql_examples.md",
                    "dependencies": "app_insights_capsule/kql_examples/app_dependencies_kql_examples.md",
                    "custom_events": "app_insights_capsule/kql_examples/app_custom_events_kql_examples.md",
                    "performance": "app_insights_capsule/kql_examples/app_performance_kql_examples.md",
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
        
        # Step 3: Direct match against curated capsule CSV examples (skip model translation if exact prompt match)
        # try:
        #     from examples_loader import load_capsule_csv_queries  # local import to avoid hard dependency if module missing
        #     capsule_map = load_capsule_csv_queries()  # { table: [ { name, prompt, code, ... } ] }
        #     # Flatten prompt->code mapping
        #     prompt_lookup = {}
        #     for entries in capsule_map.values():
        #         for e in entries:
        #             # Prefer explicit prompt field; fallback to legacy name
        #             prompt_val = (e.get('prompt') or e.get('name') or '').strip()
        #             code_val = e.get('code') or ''
        #             if prompt_val and code_val:
        #                 prompt_lookup.setdefault(prompt_val, code_val)
        #     # Exact match (case-insensitive)
        #     for prompt_key, kql_direct in prompt_lookup.items():
        #         if prompt_key.lower() == question.lower().strip():
        #             print("⚡ Exact prompt match found in capsule examples; skipping model translation.")
        #             kql_query = kql_direct
        #             # Detect timespan from query
        #             timespan_hours = self.detect_query_timespan(kql_query)
        #             result = await self.call_mcp_tool("execute_kql_query", {
        #                 "workspace_id": self.workspace_id,
        #                 "query": kql_query,
        #                 "timespan_hours": timespan_hours
        #             })
        #             if result.get("success"):
        #                 tables = result.get("tables")
        #                 formatted_results = self.format_table_results(tables)
        #                 return {
        #                     "type": "query_success",
        #                     "kql_query": kql_query,
        #                     "data": formatted_results,
        #                     "message": "✅ Query executed successfully (direct example)"
        #                 }
        #             else:
        #                 return {
        #                     "type": "query_error",
        #                     "kql_query": kql_query,
        #                     "error": result.get('error'),
        #                     "message": f"❌ Query execution failed (direct example): {result.get('error')}"
        #                 }
        # except Exception as direct_exc:  # noqa: BLE001
        #     print(f"[DirectExample] Lookup failed (will fall back to translation): {direct_exc}")

        # Step 4: Translate natural language to KQL
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

    async def explain_results(self, query_result: Dict, original_question: str = "") -> str:
        """
        Use OpenAI to analyze and explain query results
        Enhanced with better error handling and data validation
        """
        try:
            # Check if result format is valid
            if not query_result or not isinstance(query_result, dict):
                return "❌ Cannot explain results: Invalid query result format"
            
            if query_result.get("type") != "query_success":
                if query_result.get("type") == "query_error":
                    return f"❌ Cannot explain results: Query failed with error: {query_result.get('error', 'Unknown error')}"
                return "❌ Cannot explain results: Query did not succeed"
            
            # Get the tables data with improved validation
            data = query_result.get("data", {})
            if not isinstance(data, dict):
                return "❌ Cannot explain results: Invalid data format"
            
            if data.get("type") == "no_data":
                return f"📊 Query explanation: The query executed successfully but returned no data. {data.get('message', '')}"
            
            if data.get("type") != "table_data":
                return "❌ Cannot explain results: Expected table data but got different format"
            
            tables = data.get("tables", [])
            if not tables or not isinstance(tables, list):
                return "📊 Query explanation: The query executed successfully but returned no table data."
            
            # Enhanced record counting with validation
            total_records = 0
            valid_tables = 0
            
            for table in tables:
                if isinstance(table, dict) and table.get("has_data", False):
                    row_count = table.get("row_count", 0)
                    if isinstance(row_count, int) and row_count > 0:
                        total_records += row_count
                        valid_tables += 1
            
            # Check record count constraints with better messaging
            if total_records == 0:
                if valid_tables == 0:
                    return "📊 Query explanation: The query executed successfully but all tables are empty."
                else:
                    return "📊 Query explanation: The query executed successfully but returned no data rows."
            
            # Handle case where we have more than 1000 records
            truncated_tables = tables
            truncation_note = ""
            
            if total_records > 1000:
                # Truncate tables to first 1000 records total
                truncated_tables = self._truncate_tables_to_limit(tables, 1000)
                truncation_note = f" (Note: Results truncated to first 1000 records out of {total_records:,} total records for explanation purposes.)"
            
            # Prepare data summary for OpenAI
            data_summary = self._format_data_for_explanation(truncated_tables, query_result.get("kql_query", ""))
            
            # Call OpenAI to explain the results
            explanation = await self._call_openai_for_explanation(data_summary, original_question)
            
            # Add truncation note if applicable
            if truncation_note:
                explanation = explanation + truncation_note
            
            return explanation
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[Explain Error] {error_details}")
            return f"❌ Error explaining results: {str(e)}"
    
    def _truncate_tables_to_limit(self, tables: List[Dict], limit: int) -> List[Dict]:
        """
        Truncate tables to contain at most 'limit' total records
        Returns a new list of tables with truncated data
        """
        truncated_tables = []
        records_included = 0
        
        for table in tables:
            if records_included >= limit:
                break
                
            table_copy = table.copy()
            rows = table.get('rows', [])
            row_count = table.get('row_count', len(rows))
            
            if not table.get("has_data", False) or row_count == 0:
                # Include empty tables as-is
                truncated_tables.append(table_copy)
                continue
            
            records_remaining = limit - records_included
            
            if row_count <= records_remaining:
                # Include entire table
                truncated_tables.append(table_copy)
                records_included += row_count
            else:
                # Truncate table to fit remaining limit
                truncated_rows = rows[:records_remaining]
                table_copy['rows'] = truncated_rows
                table_copy['row_count'] = len(truncated_rows)
                truncated_tables.append(table_copy)
                records_included += len(truncated_rows)
                break
        
        return truncated_tables
    
    def _format_data_for_explanation(self, tables: List[Dict], kql_query: str) -> str:
        """Format query results data for OpenAI analysis"""
        summary = f"KQL Query: {kql_query}\n\n"
        
        for i, table in enumerate(tables, 1):
            summary += f"Table {i}:\n"
            summary += f"- Columns: {', '.join(table.get('columns', []))}\n"
            summary += f"- Row count: {table.get('row_count', 0)}\n"
            
            # TBD: send all data if under limit (currently 1000 rows)

            rows = table.get('rows', [])
            columns = table.get('columns', [])
            
            if rows and columns:
                summary += f"- Sample data:\n"
                for j, row in enumerate(rows[:500]):  # Show first 500 rows max
                    row_data = []
                    for k, cell in enumerate(row):
                        if k < len(columns):
                            row_data.append(f"{columns[k]}: {cell}")
                    summary += f"  Row {j+1}: {', '.join(row_data)}\n"
                
                if len(rows) > 5:
                    summary += f"  ... and {len(rows) - 5} more rows\n"
            
            summary += "\n"
        
        return summary

    async def _call_openai_for_explanation(self, data_summary: str, original_question: str) -> str:
        """Call Azure OpenAI using centralized helpers to generate an explanation.

        Uses the shared chat_completion flow so behavior stays aligned with translation.
        Adds defensive extraction to reduce false 'empty explanation' cases.
        """
        try:
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass

            from azure_openai_utils import (
                run_chat,
                emit_chat_event,
                truncate_text,
                get_env_int,
            )

            # Prompts
            system_prompt = (
                "You are an expert data analyst specializing in Azure Log Analytics and KQL query results. "
                "Provide clear, actionable insights from the provided summarized query output."
            )
            user_prompt = (
                f"Analyze these Azure Log Analytics query results.\n\n"
                f"Original Question: {original_question if original_question else 'Not specified'}\n\n"
                f"{data_summary}\n\n"
                "Return 2-4 concise sentences focusing on:\n"
                "1) Key patterns or anomalies\n"
                "2) Business/operational significance\n"
                "3) Any suggested next step if appropriate."
            )

            # Limits
            max_data_chars = get_env_int("AZURE_OPENAI_EXPLAIN_MAX_DATA_CHARS", 8000, min_value=1000, max_value=20000)
            if len(data_summary) > max_data_chars:
                print(f"[Explain Debug] Truncating data_summary from {len(data_summary)} to {max_data_chars} chars")
                data_summary = data_summary[:max_data_chars] + "\n...TRUNCATED..."

            # Use run_chat (no escalation needed for summary, but could enable later)
            chat_res = run_chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                purpose="explain",
                allow_escalation=True,  # allow in case of truncation
                debug_prefix="Explain",
            )

            emit_chat_event(chat_res, extra={"phase": "explanation"})

            if chat_res.error:
                return f"❌ Azure OpenAI API error: {chat_res.error}"
            if not chat_res.content:
                return "❌ Azure OpenAI API returned empty explanation"
            return chat_res.content

        except Exception as e:
            import traceback
            print(f"[Explain API Error] {traceback.format_exc()}")
            return f"❌ Unexpected error generating explanation: {e}" 

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
