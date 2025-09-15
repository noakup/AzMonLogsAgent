# Data & Control Flow (ASCII Overview)

```
User (Web / REST / CLI / MCP)
        |
        v
   Interface Layer (web_app / rest_api / main / mcp_server)
        |
        v
     KQLAgent (logs_agent.py)
        |        \
        |         -> Loads examples / metadata
        v
  NL→KQL Translator (nl_to_kql.py)
        |
        v
  Azure OpenAI (LLM inference)
        |
        v
 Candidate KQL Query
        |
        v
  KQL Client (kql_client.py)
        |
        v
 Azure Monitor Client (monitor_client.py)
        |
        v
 Azure Monitor Logs API
        |
        v
   Raw Results (tables)
        |
        v
  KQLAgent Post-Processing (formatting, summary)
        |
        v
  Interface Response (HTML / JSON / Stream)
```
