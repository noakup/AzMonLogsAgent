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
from nl_to_kql import translate_nl_to_kql_enhanced as translate_nl_to_kql

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
            
            # Add sample of data (first few rows)
            rows = table.get('rows', [])
            columns = table.get('columns', [])
            
            if rows and columns:
                summary += f"- Sample data:\n"
                for j, row in enumerate(rows[:5]):  # Show first 5 rows max
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
        """Call OpenAI to generate explanation of the query results"""
        try:
            # Load environment variables
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass
            
            endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
            api_key = os.environ.get("AZURE_OPENAI_KEY")
            deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo")
            api_version_override = os.environ.get("AZURE_OPENAI_API_VERSION")

            # Debug: Print configuration (masked key) to help diagnose HTTP 400 issues
            try:
                masked_key = None
                if api_key:
                    masked_key = f"{api_key[:4]}***len={len(api_key)}"
                print("[Explain Debug] Azure OpenAI Config:")
                print(f"  Endpoint: {endpoint}")
                print(f"  Deployment: {deployment}")
                print(f"  API Key Present: {'YES' if api_key else 'NO'} ({masked_key if masked_key else ''})")
                if api_version_override:
                    print(f"  API Version Override: {api_version_override}")
            except Exception as dbg_e:
                print(f"[Explain Debug] Failed to print config: {dbg_e}")
            
            if not endpoint or not api_key:
                return "❌ Azure OpenAI configuration missing. Please check your .env file for AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY."
            
            # Clean endpoint URL
            if not endpoint.startswith('http'):
                endpoint = f"https://{endpoint}"
            endpoint = endpoint.rstrip('/')
            
            # Determine API version (override wins, else adaptive like translation path)
            if api_version_override:
                api_version = api_version_override
            else:
                if "o1" in deployment.lower() or "o4" in deployment.lower():
                    api_version = "2024-12-01-preview"
                else:
                    api_version = "2024-09-01-preview"
            print(f"[Explain Debug] Using api-version: {api_version} (override={'YES' if api_version_override else 'NO'})")
            
            url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
            headers = {
                "Content-Type": "application/json",
                "api-key": api_key
            }

            # Debug: Show final request URL (without key)
            print(f"[Explain Debug] Request URL: {url}")
            
            # Create enhanced system prompt for better explanations
            system_prompt = """You are an expert data analyst specializing in Azure Log Analytics and KQL query results. Your task is to provide clear, actionable insights from data.

When analyzing query results:
1. Identify the main finding or pattern in simple terms
2. Highlight any concerning trends, anomalies, or notable values  
3. Provide context about what the data means from a business or operational perspective
4. Keep explanations concise but insightful (2-4 sentences)
5. Use plain English and avoid technical jargon

Focus on what the data tells us and what actions might be needed."""

            user_prompt = f"""Analyze these Azure Log Analytics query results:

Original Question: {original_question if original_question else 'Not specified'}

{data_summary}

Please provide a clear, actionable explanation of what this data shows and its significance."""

            # Truncate data_summary if excessively large to avoid 400s due to payload size
            MAX_DATA_SUMMARY_CHARS = 8000
            if len(data_summary) > MAX_DATA_SUMMARY_CHARS:
                print(f"[Explain Debug] Truncating data_summary from {len(data_summary)} to {MAX_DATA_SUMMARY_CHARS} chars")
                data_summary = data_summary[:MAX_DATA_SUMMARY_CHARS] + "\n...TRUNCATED..."

            # Build request payload (o-models use different parameter surface)
            lower_deployment = deployment.lower()
            if "o1" in lower_deployment or "o4" in lower_deployment:
                # For o-models: single user message combining system + user; use max_completion_tokens
                combined_content = f"{system_prompt}\n\n{user_prompt}"
                request_data = {
                    "messages": [
                        {"role": "user", "content": combined_content}
                    ],
                    "max_completion_tokens": 500
                }
            else:
                # Standard chat completion payload
                request_data = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 400,
                    "top_p": 0.9,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0
                }
            
            # Make API call with timeout and retries
            import requests
            import json
            import time
            
            max_retries = 3
            base_delay = 1
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        url, 
                        headers=headers, 
                        data=json.dumps(request_data),
                        timeout=30
                    )
                    
                    # Handle specific HTTP errors
                    if response.status_code == 429:
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            print(f"[Explain] Rate limited, retrying in {delay}s...")
                            time.sleep(delay)
                            continue
                        else:
                            return "❌ Azure OpenAI service is currently busy. Please try explaining the results again in a few moments."
                    
                    if response.status_code == 401:
                        return "❌ Azure OpenAI authentication failed. Please check your API key in the .env file."
                    
                    if response.status_code == 404:
                        return f"❌ Azure OpenAI deployment '{deployment}' not found. Please check your deployment name in the .env file."
                    
                    if response.status_code == 400:
                        # Capture body for diagnostics
                        body_text = None
                        try:
                            body_text = response.text[:1000]
                        except Exception:
                            body_text = '<unavailable>'
                        print(f"[Explain Debug] HTTP 400 Body Snippet: {body_text}")
                    response.raise_for_status()
                    
                    result = response.json()
                    
                    # Enhanced response validation
                    if 'error' in result:
                        error_msg = result['error'].get('message', 'Unknown API error')
                        return f"❌ Azure OpenAI API error: {error_msg}"
                    
                    if 'choices' not in result or not result['choices']:
                        return "❌ Azure OpenAI API returned no response choices"
                    
                    choice = result['choices'][0]
                    
                    # Check for content filtering
                    if choice.get('finish_reason') == 'content_filter':
                        return "❌ Response was filtered due to content policy. Please try with different query results."
                    
                    if 'message' not in choice:
                        return "❌ Azure OpenAI API response missing message content"
                    
                    content = choice['message'].get('content', '').strip()
                    
                    if not content:
                        return "❌ Azure OpenAI API returned empty explanation"
                    
                    # Success - return the explanation
                    return content
                    
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        print(f"[Explain] Request timeout, retrying...")
                        time.sleep(base_delay * (attempt + 1))
                        continue
                    else:
                        return "❌ Azure OpenAI request timed out. Please try again."
                        
                except requests.exceptions.ConnectionError:
                    if attempt < max_retries - 1:
                        print(f"[Explain] Connection error, retrying...")
                        time.sleep(base_delay * (attempt + 1))
                        continue
                    else:
                        return "❌ Unable to connect to Azure OpenAI. Please check your network connection."
                        
                except requests.exceptions.HTTPError as e:
                    status = e.response.status_code if e.response is not None else 'Unknown'
                    detail_snip = ''
                    try:
                        txt = e.response.text if e.response is not None else ''
                        detail_snip = (txt[:300] + '...') if len(txt) > 300 else txt
                    except Exception:
                        pass
                    return f"❌ Azure OpenAI API error: HTTP {status}. {detail_snip}"
                    
                except json.JSONDecodeError:
                    return "❌ Invalid response from Azure OpenAI API"
            
            return "❌ Failed to get explanation after multiple attempts"
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[Explain API Error] {error_details}")
            return f"❌ Unexpected error generating explanation: {str(e)}"

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
