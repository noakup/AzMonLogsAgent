# 🎉 Azure Monitor Natural #### 📊 **KQL Examples & 1. **🌐 Web Interface** - Full-featured UI at `http://localhost:8080`etadata**
- **`app_insights_capsule/`** - Application Insights documentation capsule
  - **`kql_examples/`** - KQL examples (8 files)
    - Entity-specific KQL examples (requests, exceptions, traces, dependencies, etc.)
    - Multi-entity query examples
  - **`metadata/`** - Application Insights table schema documentation (3 files)
    - Table schema documentation (AppRequests, AppExceptions, AppTraces metadata)
- **`usage_kql_examples.md`** - General Log Analytics usage examplesuage KQL Agent

## 📋 Project Overview

A comprehensive Azure Log Analytics natural language query system that translates plain English questions into KQL queries. Features multiple interfaces (web, CLI, API) and intelligent query processing with Azure OpenAI integration.

## 🏗️ Core Architecture

### **Main Components**

#### 🌐 **Web Interface System**
- **`web_app.py`** - Flask web application (445 lines)
- **`templates/index.html`** - Modern responsive UI
- **Features**: Interactive workspace setup, real-time results, suggestion pills

#### 🤖 **Natural Language Processing**
- **`logs_agent.py`** - Core NL agent with timespan detection (524 lines)
- **`nl_to_kql.py`** - Context-aware translation engine (230 lines)
- **Features**: Smart time detection, example-driven translation, error recovery

#### 🔧 **Core Infrastructure** 
- **`azure_agent/monitor_client.py`** - Azure SDK wrapper
- **`main.py`** - Legacy CLI interface (250 lines)
- **`server_manager.py`** - Multi-interface launcher (132 lines)
- **`start.py`** - Interface selector (146 lines)

#### � **KQL Examples & Metadata**
- **`app_*_kql_examples.md`** - Entity-specific KQL examples (8 files)
- **`app_*_metadata.md`** - Table schema documentation (3 files)
- **`usage_kql_examples.md`** - General usage examples

#### 🔌 **MCP Server Integration**
- **`my-first-mcp-server/`** - Model Context Protocol server
  - **`rest_api.py`** - HTTP API server
  - **`mcp_server.py`** - MCP protocol implementation

#### ⚙️ **Configuration & Setup**
- **`setup_azure_openai.py`** - Environment configuration
- **`.env.template`** - Environment variable template
- **`requirements.txt`** - Python dependencies

## 🚀 **Current Functionality**

### ✅ **Working Features**
1. **� Web Interface** - Full-featured UI at `http://localhost:5000`
2. **� CLI Agent** - Interactive terminal interface  
3. **� HTTP API** - REST endpoints for integration
4. **🤖 MCP Server** - AI assistant integration
5. **🧠 Smart Translation** - Context-aware NL-to-KQL conversion
6. **⏰ Time Detection** - Automatic timespan handling
7. **� Example System** - Curated query examples
8. **🔧 Environment Setup** - Automated configuration

### 🏁 **Usage Methods**

#### Quick Start (Recommended)
```powershell
# Direct web interface  
python web_app.py
```

#### All Available Commands
```powershell
# Interface Options
python web_app.py                    # Web UI
python server_manager.py agent       # CLI agent
python server_manager.py http        # REST API
python server_manager.py mcp         # MCP server

# Setup & Testing
python setup_azure_openai.py         # Configure environment
python server_manager.py test        # Test functionality
```

## 📁 **File Status Analysis**

### **Active Core Files** (Keep)
- `main.py` - Legacy CLI interface (still referenced)
- `logs_agent.py` - Core agent logic
- `web_app.py` - Web interface
- `server_manager.py` - Server management
- `nl_to_kql.py` - Translation engine
- `setup_azure_openai.py` - Setup utility
- `azure_agent/monitor_client.py` - Azure integration
- `templates/index.html` - Web UI template
- `my-first-mcp-server/` - MCP implementation
- All `app_*_kql_examples.md` and `app_*_metadata.md` files
- `requirements.txt`, `.env.template` - Configuration

### **Reference Files** (Keep)
- `README.md` - Project documentation
- `CONTRIBUTING.md` - Contribution guidelines
- `usage_kql_examples.md` - Example queries
