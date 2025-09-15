# Component Responsibilities

| Component | File(s) | Purpose |
|-----------|---------|---------|
| Web UI | `web_app.py`, `templates/` | Flask interface for interactive querying. |
| REST API | `rest_api.py` | Programmatic HTTP access to translation + execution. |
| CLI / Agent Launcher | `main.py`, `server_manager.py` | Command-line usage and multi-interface control. |
| MCP Server | `my-first-mcp-server/mcp_server.py` | Exposes capabilities via Model Context Protocol. |
| KQLAgent | `logs_agent.py` | Orchestrates NL input → translation → execution → formatting. |
| Translator | `nl_to_kql.py` | Builds prompts, injects examples/schema, retries invalid outputs. |
| KQL Client | `kql_client.py` | Normalizes and prepares KQL queries. |
| Azure Monitor Client | `azure_agent/monitor_client.py` | Handles Azure Monitor Logs API calls. |
| Setup | `setup_azure_openai.py` | Environment & Azure OpenAI configuration helper. |
| Examples & Capsules | `app_insights_capsule/`, `app_insights_kql_examples/` | Curated example KQL queries for grounding. |
| Metadata | `app_insights_metadata/`, `NGSchema/` | Table schema & field vocabularies. |
| Config Templates | `.env.template` | Environment variable reference. |
| Usage Examples | `usage_kql_examples.md` | General-purpose KQL patterns. |
