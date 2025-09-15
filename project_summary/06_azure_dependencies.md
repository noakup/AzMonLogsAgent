# Azure Dependencies

| Service | Usage | Related Code |
|---------|-------|--------------|
| Azure OpenAI | Natural language → KQL translation (LLM inference) | `nl_to_kql.py`, `logs_agent.py`, `setup_azure_openai.py` |
| Azure Monitor Logs | Execute KQL against Log Analytics | `azure_agent/monitor_client.py` |
| (Optional) App Insights Tables | Domain examples & schema grounding | `app_insights_*`, `NGSchema/` |

## Environment Variables (Typical)
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT` (model deployment name)
- `LOG_ANALYTICS_WORKSPACE_ID`
- `LOG_ANALYTICS_SHARED_KEY` (if using shared key auth)
- `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` (if using AAD)

## Authentication Modes
1. Managed Identity (preferred in Azure)
2. Service Principal (env vars)
3. Shared Workspace Key (fallback)

## Rate & Error Considerations
- Retry translation if malformed KQL.
- Backoff on 429 from Azure OpenAI.
- Paginate / chunk large result sets.
