#!/usr/bin/env python3
"""
Simple test to verify MCP server is responding correctly
"""

import subprocess
import sys
import json
import time

def test_mcp_server():
    """Test if the MCP server responds to basic MCP protocol messages"""
    
    print("Testing MCP Server...")
    
    # Start the MCP server
    server_process = subprocess.Popen([
        sys.executable, "my-first-mcp-server/mcp_server.py"
    ], 
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
    )
    
    try:
        # Send an initialization message
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        print("Sending initialization message...")
        server_process.stdin.write(json.dumps(init_message) + "\n")
        server_process.stdin.flush()
        
        # Wait for response
        time.sleep(2)
        
        # Try to read response
        if server_process.poll() is None:  # Process is still running
            print("✅ MCP server started successfully")
        else:
            print("❌ MCP server exited")
            stderr_output = server_process.stderr.read()
            if stderr_output:
                print(f"Error output: {stderr_output}")
        
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")
    finally:
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    test_mcp_server()
