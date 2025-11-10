#!/usr/bin/env python3
"""
Startup script for KQL servers
"""

import click
import subprocess
import sys
import os

# Optional imports for embedding index maintenance
try:
    from embedding_index import build_domain_index, load_or_build_domain_index  # type: ignore
except Exception:
    build_domain_index = None  # type: ignore
    load_or_build_domain_index = None  # type: ignore

def _collect_container_public_shots() -> list[dict[str,str]]:
    """Load container public shots."""
    csv_path = os.path.join(os.getcwd(), "containers_capsule", "public_shots.csv")
    import csv
    out: list[dict[str,str]] = []
    if not os.path.exists(csv_path):
        print(f"[collect-container] warning: CSV not found at {csv_path}")
        return out
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            has_header = header and {h.lower() for h in header} >= {"prompt","query"}
            if not has_header and header:
                f.seek(0)
                reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                prompt = row[0].strip()
                query = row[1].strip().replace('""','"')
                if prompt and query:
                    out.append({"question": prompt, "kql": query})
    except Exception as e:
        print(f"[collect-container] csv_parse_error path={csv_path} error={e}")
    # Deduplicate by lowercased question
    seen = set()
    deduped = []
    for ex in out:
        key = ex["question"].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(ex)
    print(f"[collect-container] loaded_csv examples={len(out)} deduped={len(deduped)}")
    return deduped

def _collect_appinsights_examples() -> list[dict[str,str]]:
    """Aggregate Application Insights domain examples across known files."""
    base = os.path.join(os.getcwd(), "app_insights_capsule", "kql_examples")
    files = [
        "app_requests_kql_examples.md",
        "app_exceptions_kql_examples.md",
        "app_traces_kql_examples.md",
        "app_dependencies_kql_examples.md",
        "app_performance_kql_examples.md",
    ]
    import re
    examples: list[dict[str,str]] = []
    for fname in files:
        path = os.path.join(base, fname)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        q_pat = re.compile(r"^\*\*(.+?)\*\*$", re.MULTILINE)
        questions = q_pat.findall(text)
        kql_blocks = re.findall(r"```kql\n([\s\S]*?)\n```", text, re.IGNORECASE)
        for i, q in enumerate(questions):
            kql = kql_blocks[i] if i < len(kql_blocks) else ""
            examples.append({"question": q.strip(), "kql": kql.strip()})
    return examples

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

@cli.command("embed-index-purge")
@click.option("--domain", type=click.Choice(["containers","appinsights","all"]), default="all", help="Domain to purge or 'all'.")
def embed_index_purge(domain: str):
    """Delete persistent embedding index files (containers/appinsights/all)."""
    index_dir = os.environ.get("EMBED_INDEX_DIR", "embedding_index")
    if not os.path.isdir(index_dir):
        click.echo(f"ℹ️ Index directory '{index_dir}' does not exist; nothing to purge.")
        return
    targets = []
    if domain in ("containers","all"):
        targets.append(os.path.join(index_dir, "domain_containers_embedding_index.json"))
    if domain in ("appinsights","all"):
        targets.append(os.path.join(index_dir, "domain_appinsights_embedding_index.json"))
    removed = 0
    for t in targets:
        if os.path.exists(t):
            try:
                os.remove(t)
                removed += 1
                click.echo(f"🗑️ Removed {t}")
            except Exception as exc:
                click.echo(f"❌ Failed to remove {t}: {exc}")
    if removed == 0:
        click.echo("ℹ️ No index files found to remove for selected domain(s).")
    else:
        click.echo(f"✅ Purge complete. Removed {removed} file(s).")

@cli.command("embed-index-rebuild")
@click.option("--domain", type=click.Choice(["containers","appinsights","all"]), default="all", help="Domain to rebuild or 'all'.")
def embed_index_rebuild(domain: str):
    """Force rebuild of embedding index for selected domain(s)."""
    if not build_domain_index:
        click.echo("❌ embedding_index module unavailable; rebuild not possible.")
        return
    total = 0
    if domain in ("containers","all"):
        container_public_shots = _collect_container_public_shots()
        if not container_public_shots:
            click.echo("⚠️ Containers CSV missing or empty; building an empty containers index (no examples).")
        print(f"---------------- [embed-index] building containers index with: {container_public_shots} examples")
        build_domain_index("containers", container_public_shots)
        click.echo(f"🔄 Rebuilt containers index with {len(container_public_shots)} examples (empty OK).")
        total += 1
    if domain in ("appinsights","all"):
        ex_app = _collect_appinsights_examples()
        if not ex_app:
            click.echo("⚠️ AppInsights examples missing or empty; building an empty appinsights index (no examples).")
        build_domain_index("appinsights", ex_app)
        click.echo(f"🔄 Rebuilt appinsights index with {len(ex_app)} examples (empty OK).")
        total += 1
    if total == 0:
        click.echo("ℹ️ No domains processed.")
    else:
        click.echo("✅ Rebuild complete.")

if __name__ == "__main__":
    cli()
