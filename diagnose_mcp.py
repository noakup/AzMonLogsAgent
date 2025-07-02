#!/usr/bin/env python3
"""
Diagnostic script for MCP server issues
"""

import os
import json
import subprocess
import sys

def check_mcp_setup():
    """Check various aspects of the MCP setup"""
    
    print("🔍 MCP Setup Diagnostic")
    print("=" * 50)
    
    # 1. Check if config file exists and is valid
    config_path = os.path.expandvars(r"%APPDATA%\Claude\config.json")
    print(f"1. Claude Desktop config: {config_path}")
    
    if os.path.exists(config_path):
        print("   ✅ Config file exists")
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            if "mcpServers" in config:
                print("   ✅ mcpServers section found")
                servers = config["mcpServers"]
                for name, server_config in servers.items():
                    print(f"   📋 Server '{name}':")
                    print(f"      Command: {server_config.get('command', 'Not set')}")
                    print(f"      Args: {server_config.get('args', [])}")
                    
                    # Check if the script file exists
                    if 'args' in server_config and server_config['args']:
                        script_path = server_config['args'][0]
                        if os.path.exists(script_path):
                            print(f"      ✅ Script file exists: {script_path}")
                        else:
                            print(f"      ❌ Script file NOT found: {script_path}")
            else:
                print("   ❌ No mcpServers section found")
                
        except json.JSONDecodeError as e:
            print(f"   ❌ Invalid JSON: {e}")
        except Exception as e:
            print(f"   ❌ Error reading config: {e}")
    else:
        print("   ❌ Config file does not exist")
    
    # 2. Check if MCP server script exists and can be executed
    print("\n2. MCP Server Script:")
    mcp_script = "my-first-mcp-server/mcp_server.py"
    
    if os.path.exists(mcp_script):
        print(f"   ✅ Script exists: {mcp_script}")
        
        # Try to run it with --help or just check syntax
        try:
            result = subprocess.run([
                sys.executable, "-m", "py_compile", mcp_script
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                print("   ✅ Script syntax is valid")
            else:
                print(f"   ❌ Script has syntax errors: {result.stderr}")
                
        except Exception as e:
            print(f"   ⚠️  Could not check script syntax: {e}")
    else:
        print(f"   ❌ Script NOT found: {mcp_script}")
    
    # 3. Check Python environment
    print("\n3. Python Environment:")
    try:
        import mcp
        print(f"   ✅ MCP package available: {mcp.__version__ if hasattr(mcp, '__version__') else 'version unknown'}")
    except ImportError:
        print("   ❌ MCP package not installed")
    
    try:
        import azure.identity
        print("   ✅ Azure Identity package available")
    except ImportError:
        print("   ❌ Azure Identity package not installed")
    
    try:
        import azure.monitor.query
        print("   ✅ Azure Monitor Query package available")
    except ImportError:
        print("   ❌ Azure Monitor Query package not installed")
    
    # 4. Check if Claude Desktop is running
    print("\n4. Claude Desktop Process:")
    try:
        result = subprocess.run([
            "powershell", "-Command", 
            "Get-Process | Where-Object {$_.ProcessName -like '*Claude*'} | Select-Object ProcessName, Id"
        ], capture_output=True, text=True)
        
        if result.stdout.strip():
            print("   ✅ Claude Desktop is running")
            print(f"   {result.stdout.strip()}")
        else:
            print("   ❌ Claude Desktop is NOT running")
            
    except Exception as e:
        print(f"   ⚠️  Could not check Claude Desktop process: {e}")
    
    print("\n" + "=" * 50)
    print("💡 Recommendations:")
    print("1. Make sure Claude Desktop is completely closed and restarted after config changes")
    print("2. Check Claude Desktop's developer console for MCP-related errors")
    print("3. Ensure the MCP server starts without errors when run manually")
    print("4. Verify all required Python packages are installed")

if __name__ == "__main__":
    check_mcp_setup()
