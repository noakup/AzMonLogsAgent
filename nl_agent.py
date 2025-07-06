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
                    print(f"📚 Getting example descriptions for: {scenario}")
                    descriptions = self.extract_example_descriptions(scenario)
                    
                    if descriptions:
                        # Return structured data for suggestion buttons
                        return {
                            "type": "example_suggestions",
                            "scenario": scenario,
                            "suggestions": descriptions,
                            "message": f"✅ Found {len(descriptions)} example suggestions for {scenario.title()}"
                        }
                    else:
                        return f"❌ No examples found for {scenario}"
            
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
    
    def extract_example_descriptions(self, scenario: str) -> List[str]:
        """Extract natural language descriptions from example files"""
        try:
            file_map = {
                'requests': 'app_requests_kql_examples.md',
                'exceptions': 'app_exceptions_kql_examples.md', 
                'traces': 'app_traces_kql_examples.md',
                'dependencies': 'app_dependencies_kql_examples.md',
                'custom_events': 'app_custom_events_kql_examples.md',
                'performance': 'app_performance_kql_examples.md',
                'usage': 'usage_kql_examples.md',
                'page_views': 'app_page_views_kql_examples.md'  # Added page_views mapping
            }
            
            filename = file_map.get(scenario)
            if not filename:
                print(f"⚠️ No file mapping found for scenario: {scenario}")
                return []
            
            filepath = os.path.join(os.path.dirname(__file__), filename)
            if not os.path.exists(filepath):
                print(f"⚠️ Example file not found: {filepath}")
                return []
            
            descriptions = []
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"📖 Processing example file: {filename}")
            
            # Split by lines and look for patterns like "**Description**"
            lines = content.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                # Look for lines that start with ** and end with ** (markdown bold)
                if line.startswith('**') and line.endswith('**') and len(line) > 4:
                    # Remove the ** markers
                    description = line[2:-2].strip()
                    
                    # Handle special case for "Prompt:" - get the next non-empty line
                    if description.lower() == "prompt:":
                        # Look for the actual prompt in the next few lines
                        for j in range(i + 1, min(i + 5, len(lines))):
                            next_line = lines[j].strip()
                            if next_line and not next_line.startswith('**') and not next_line.startswith('```'):
                                descriptions.append(next_line)
                                print(f"✅ Found prompt: {next_line}")
                                break
                        continue
                    
                    # Skip if it looks like a header (contains words like "Example", "Analysis", etc.)
                    skip_words = ['example', 'analysis', 'queries', 'insights', 'metadata', 'kql', 'document', 'table']
                    should_skip = any(skip_word in description.lower() for skip_word in skip_words)
                    
                    # Also skip very short descriptions (likely headers)
                    if len(description) < 10:
                        should_skip = True
                    
                    if not should_skip:
                        descriptions.append(description)
                        print(f"✅ Found example: {description}")
                    else:
                        print(f"⏭️ Skipped header/short text: {description}")
            
            print(f"📊 Found {len(descriptions)} example descriptions for {scenario}")
            return descriptions[:10]  # Limit to first 10 examples
            
        except Exception as e:
            print(f"❌ Error extracting examples for {scenario}: {e}")
            return []

    async def explain_results(self, query_result: Dict, original_question: str = "") -> str:
        """
        Use OpenAI to analyze and explain query results
        Only works for results with 1-1000 records
        """
        try:
            # Check if result format is valid
            if not query_result or query_result.get("type") != "query_success":
                return "❌ Cannot explain results: Invalid or failed query result"
            
            # Get the tables data
            data = query_result.get("data", {})
            if data.get("type") != "table_data":
                return "❌ Cannot explain results: No table data found"
            
            tables = data.get("tables", [])
            if not tables:
                return "❌ Cannot explain results: No tables in result"
            
            # Count total records across all tables
            total_records = sum(table.get("row_count", 0) for table in tables)
            
            # Check record count constraints
            if total_records == 0:
                return "📊 No records to explain - the query returned empty results."
            elif total_records > 1000:
                return f"📊 Cannot explain results: Too many records ({total_records}). Results explanation is only available for queries returning 1-1000 records."
            
            # Prepare data summary for OpenAI
            data_summary = self._format_data_for_explanation(tables, query_result.get("kql_query", ""))
            
            # Call OpenAI to explain the results
            explanation = await self._call_openai_for_explanation(data_summary, original_question)
            
            return f"🧠 **Results Explanation:**\n\n{explanation}"
            
        except Exception as e:
            return f"❌ Error explaining results: {str(e)}"
    
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
            
            print(f"[DEBUG] Endpoint: {endpoint}")
            print(f"[DEBUG] Deployment: {deployment}")
            print(f"[DEBUG] API Key: {'SET' if api_key else 'NOT SET'}")
            
            if not endpoint or not api_key:
                return "❌ Azure OpenAI configuration missing. Please check your .env file."
              # Determine API version - use standard version for better compatibility
            api_version = "2024-12-01-preview"
            
            print(f"[DEBUG] API Version: {api_version}")
            
            url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
            headers = {
                "Content-Type": "application/json",
                "api-key": api_key
            }
            
            # Create system prompt for explanation
            system_prompt = """You are a data analyst expert. Your task is to analyze query results and provide clear, concise explanations.

For the provided query results, analyze the data and provide:
1. A brief summary of what the data shows
2. Key patterns, trends, or insights
3. Notable values, outliers, or anomalies

Keep your explanation concise (2-3 sentences) and focus on the most important insights. Use plain English and avoid technical jargon."""

            user_prompt = f"""Please analyze these query results and provide a clear explanation:

Original Question: {original_question if original_question else 'Not provided'}

Query Results:
{data_summary}

Provide a concise explanation focusing on the key insights and patterns in the data."""

            # Use standard message format for all models for better compatibility
            data = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                #"temperature": 0.3,
                "max_completion_tokens": 300
            }
              # Make API call
            import requests
            import json
            
            print(f"[DEBUG] URL: {url}")
            print(f"[DEBUG] Request data: {json.dumps(data, indent=2)}")
            
            response = requests.post(url, headers=headers, data=json.dumps(data))
            
            print(f"[DEBUG] Response status: {response.status_code}")
            print(f"[DEBUG] Response headers: {dict(response.headers)}")
            print(f"[DEBUG] Raw response: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            print(f"[DEBUG] Response JSON: {json.dumps(result, indent=2)}")
            
            # Check if response has the expected structure
            if 'choices' not in result:
                print(f"[DEBUG] No 'choices' in response: {result}")
                return "❌ Azure OpenAI API returned unexpected format"
            
            if not result['choices'] or len(result['choices']) == 0:
                print(f"[DEBUG] Empty choices array: {result}")
                return "❌ Azure OpenAI API returned no response choices"
            
            choice = result['choices'][0]
            if 'message' not in choice:
                print(f"[DEBUG] No 'message' in choice: {choice}")
                return "❌ Azure OpenAI API response missing message"
            
            content = choice['message'].get('content', '').strip()
            print(f"[DEBUG] Extracted explanation: '{content}'")
            print(f"[DEBUG] Content length: {len(content)}")
            
            if not content:
                return "❌ Azure OpenAI API returned empty explanation"
            
            return content
            
        except Exception as e:
            print(f"[DEBUG] Exception in _call_openai_for_explanation: {e}")
            import traceback
            traceback.print_exc()
            return f"Failed to generate explanation: {str(e)}"

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
