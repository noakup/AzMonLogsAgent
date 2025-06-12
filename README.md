# Azure Monitor MCP Agent

A Python agent for querying Azure Monitor Log Analytics using both direct KQL and natural language (NL) questions. Supports both CLI and web service interfaces. NL questions are translated to KQL using Azure OpenAI. Results are displayed in a user-friendly table format.

## Features
- Query Azure Log Analytics with KQL or natural language (NL)
- NL-to-KQL translation via Azure OpenAI (REST API, no SDK dependency)
- CLI and Flask-based web service interface
- Azure authentication using Azure CLI credentials
- Environment-based configuration for secrets and endpoints
- Defensive error handling and robust result parsing
- Example-driven prompt system for NL-to-KQL (few-shot)
- Results formatted as tables for easy reading

## Requirements
- Python 3.8+
- Azure CLI (for authentication)
- Azure Log Analytics Workspace
- Azure OpenAI resource (for NL-to-KQL translation)

## Installation
1. Clone this repository and enter the directory:
   ```powershell
   git clone <your-repo-url>
   cd NoaAzMonAgent
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Set environment variables for Azure OpenAI (see code comments for required variables).

## Usage

### CLI
Run a KQL query:
```powershell
python main.py query --workspace-id <WORKSPACE_ID> --query "Heartbeat | take 5"
```

Ask a question in natural language:
```powershell
python main.py query --workspace-id <WORKSPACE_ID> --ask "Show me the total ingestion volume in MB in the last 24 hours based on the Usage table"
```

### Web Service
Start the Flask web service:
```powershell
python web_service.py
```

## Security
- **Never commit secrets**: Use environment variables for keys and endpoints.
- Review `.gitignore` before publishing to GitHub.

## License
MIT License
