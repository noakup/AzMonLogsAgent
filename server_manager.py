#!/usr/bin/env python3
"""
Startup script for KQL servers
"""

import click
import subprocess
import sys
import os

@click.group()
def cli():
    """KQL Server Management"""
    pass

@cli.command()
def http():
    """Start the HTTP/REST API server"""
    click.echo("🚀 Starting KQL HTTP Server on http://localhost:8080")
    click.echo("Available endpoints:")
    click.echo("  POST /query - Execute KQL queries")
    click.echo("  GET /health - Health check")
    click.echo()
    click.echo("Press Ctrl+C to stop the server")
    
    try:
        subprocess.run([sys.executable, "my-first-mcp-server/rest_api.py"])
    except KeyboardInterrupt:
        click.echo("\n🛑 HTTP Server stopped")

@cli.command()
def mcp():
    """Start the MCP server for AI assistant integration"""
    click.echo("🤖 Starting KQL MCP Server")
    click.echo("MCP Tools available:")
    click.echo("  - execute_kql_query: Run KQL queries")
    click.echo("  - get_kql_examples: Get example queries")
    click.echo("  - validate_workspace_connection: Test connections")
    click.echo()
    click.echo("To integrate with Claude Desktop, add this to your config.json:")
    config_path = os.path.join(os.getcwd(), "my-first-mcp-server", "claude_desktop_config.json")
    click.echo(f"Config file: {config_path}")
    click.echo()
    click.echo("Press Ctrl+C to stop the server")
    
    try:
        subprocess.run([sys.executable, "my-first-mcp-server/mcp_server.py"])
    except KeyboardInterrupt:
        click.echo("\n🛑 MCP Server stopped")

@cli.command()
def test():
    """Test the MCP server functionality"""
    click.echo("🧪 Testing MCP Server...")
    try:
        subprocess.run([sys.executable, "test_mcp_server.py"])
    except Exception as e:
        click.echo(f"❌ Test failed: {e}")

@cli.command()
def test_translation():
    """Test and compare translation methods"""
    click.echo("🧪 Testing NL to KQL Translation")
    click.echo("This will test the consistency of natural language translation")
    
    try:
        subprocess.run([sys.executable, "test_comparison.py"])
    except Exception as e:
        click.echo(f"❌ Test failed: {e}")

@cli.command()
def client():
    """Run the interactive KQL client"""
    click.echo("💻 Starting KQL Interactive Client...")
    try:
        subprocess.run([sys.executable, "kql_client.py"])
    except Exception as e:
        click.echo(f"❌ Client failed: {e}")

@cli.command()
def agent():
    """Start the Natural Language KQL Agent"""
    click.echo("🤖 Starting Natural Language KQL Agent")
    click.echo("This agent can:")
    click.echo("  - Answer KQL questions in natural language")
    click.echo("  - Get examples for different scenarios")
    click.echo("  - Test workspace connections")
    click.echo("  - Execute queries and format results")
    click.echo()
    
    try:
        subprocess.run([sys.executable, "logs_agent.py"])
    except KeyboardInterrupt:
        click.echo("\n🛑 Agent stopped")
    except Exception as e:
        click.echo(f"❌ Agent failed: {e}")

@cli.command()
def setup():
    """Setup Azure OpenAI configuration for natural language queries"""
    click.echo("🔧 Setting up Azure OpenAI configuration")
    try:
        subprocess.run([sys.executable, "setup_azure_openai.py"])
    except Exception as e:
        click.echo(f"❌ Setup failed: {e}")

@cli.command()
def web():
    """Start the Web Interface for Natural Language KQL queries"""
    click.echo("🌐 Starting Natural Language KQL Web Interface")
    click.echo("Features:")
    click.echo("  - Beautiful web UI for natural language queries")
    click.echo("  - Interactive workspace setup")
    click.echo("  - Quick suggestion pills")
    click.echo("  - Real-time query results")
    click.echo("  - Example queries for different scenarios")
    click.echo()
    click.echo("📍 Web interface will be available at: http://localhost:8080")
    click.echo("🤖 Ready to process natural language KQL questions!")
    click.echo()
    click.echo("Press Ctrl+C to stop the server")
    
    try:
        subprocess.run([sys.executable, "web_app.py"])
    except KeyboardInterrupt:
        click.echo("\n🛑 Web Interface stopped")
    except Exception as e:
        click.echo(f"❌ Web Interface failed: {e}")

if __name__ == "__main__":
    cli()
