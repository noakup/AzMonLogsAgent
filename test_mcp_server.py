#!/usr/bin/env python3
"""
Test script for the KQL MCP Server
"""

import asyncio
import json
import sys
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async def test_mcp_server():
    """Test the MCP server functionality"""
    
    print("Testing KQL MCP Server...")
    
    # Start the MCP server as a subprocess
    import subprocess
    server_process = subprocess.Popen([
        sys.executable, "mcp_server.py"
    ], 
    cwd="my-first-mcp-server",
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
    )
    
    try:
        # Connect to the server
        async with stdio_client(server_process) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                
                print("✅ Connected to MCP server")
                
                # List available tools
                tools = await session.list_tools()
                print(f"📋 Available tools: {len(tools.tools)}")
                for tool in tools.tools:
                    print(f"  - {tool.name}: {tool.description}")
                
                # Test workspace validation (you'll need to provide a real workspace ID)
                workspace_id = input("\nEnter your workspace ID to test (or press Enter to skip): ").strip()
                
                if workspace_id:
                    print(f"\n🔄 Testing workspace connection: {workspace_id}")
                    result = await session.call_tool("validate_workspace_connection", {
                        "workspace_id": workspace_id
                    })
                    
                    for content in result.content:
                        if hasattr(content, 'text'):
                            print(f"Result: {content.text}")
                
                # Test getting examples
                print("\n📚 Getting KQL examples for requests...")
                result = await session.call_tool("get_kql_examples", {
                    "scenario": "requests"
                })
                
                for content in result.content:
                    if hasattr(content, 'text'):
                        # Show first 500 characters of examples
                        text = content.text[:500] + "..." if len(content.text) > 500 else content.text
                        print(f"Examples: {text}")
                
                print("\n✅ MCP server test completed successfully!")
                
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")
    finally:
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
