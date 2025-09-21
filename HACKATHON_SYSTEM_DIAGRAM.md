# 🏗️ Azure Monitor NL-KQL Agent - System Architecture

## High-Level System Design

```mermaid
flowchart TD
    %% User Interfaces Layer
    subgraph UI["🌐 Multi-Modal User Interfaces"]
        WebUI["🖥️ Modern Web UI<br/>(Flask + Interactive Tables)"]
        CLI["💻 CLI Agent<br/>(Interactive Terminal)"]
        API["🔌 REST API<br/>(Integration Layer)"]
        MCP["🤖 MCP Server<br/>(AI Assistant Integration)"]
    end

    %% Core Processing Engine
    subgraph CORE["🧠 Intelligent Processing Core"]
        NLAgent["🎯 Natural Language Agent<br/>(Context-Aware Translation)"]
        Translator["⚡ NL→KQL Engine<br/>(GPT-4 + Pattern Matching)"]
        QueryEngine["🔍 Query Execution Engine<br/>(Validation + Retry Logic)"]
        SchemaEngine["📊 Workspace Schema Discovery<br/>(Dynamic Table Analysis)"]
    end

    %% External Services
    subgraph AZURE["☁️ Azure Cloud Services"]
        OpenAI["🤖 Azure OpenAI GPT-4<br/>(Smart Translation)"]
        LogAnalytics["📈 Azure Log Analytics<br/>(KQL Query Execution)"]
        Monitor["📡 Azure Monitor APIs<br/>(Workspace Management)"]
    end

    %% Knowledge Base
    subgraph KB["📚 Intelligent Knowledge Base"]
        Examples["💡 Curated Query Examples<br/>(100+ Patterns Across 8+ Services)"]
        Schemas["🗂️ NGSchema Repository<br/>(Table Metadata & Relationships)"]
        Context["🎯 Context Engine<br/>(Workspace-Aware Suggestions)"]
    end

    %% Data Flow
    UI --> NLAgent
    NLAgent --> Translator
    NLAgent --> SchemaEngine
    Translator --> OpenAI
    NLAgent --> QueryEngine
    QueryEngine --> LogAnalytics
    SchemaEngine --> Monitor
    
    %% Knowledge Integration
    NLAgent --> Examples
    NLAgent --> Schemas
    SchemaEngine --> Context
    Context --> NLAgent

    %% Response Flow
    LogAnalytics --> QueryEngine
    QueryEngine --> NLAgent
    OpenAI --> Translator
    Monitor --> SchemaEngine
    NLAgent --> UI

    %% Styling
    classDef userInterface fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef coreEngine fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef azureService fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef knowledge fill:#fff3e0,stroke:#e65100,stroke-width:2px

    class WebUI,CLI,API,MCP userInterface
    class NLAgent,Translator,QueryEngine,SchemaEngine coreEngine
    class OpenAI,LogAnalytics,Monitor azureService
    class Examples,Schemas,Context knowledge
```

## 🎯 Key Architecture Highlights

### **🚀 Multi-Interface Design**
- **Web UI**: Interactive tables, real-time suggestions, visual query building
- **CLI Agent**: Power users, automation, scripting integration
- **REST API**: Enterprise integration, third-party applications
- **MCP Server**: AI assistant integration (Claude, ChatGPT, etc.)

### **🧠 Intelligent Core Engine**
- **Context-Aware Translation**: Understands workspace schema and user intent
- **Smart Retry Logic**: Automatically fixes common query errors
- **Dynamic Schema Discovery**: Real-time workspace analysis and suggestion generation
- **Pattern Matching**: Combines AI with rule-based optimization

### **☁️ Azure Cloud Integration**
- **GPT-4 Powered**: Advanced natural language understanding
- **Native Azure APIs**: Direct integration with Log Analytics and Monitor
- **Scalable Architecture**: Enterprise-ready with proper error handling

### **📚 Knowledge-Driven Approach**
- **100+ Curated Examples**: Covering Application Insights, Security, Infrastructure
- **NGSchema Integration**: Comprehensive table metadata and relationships
- **Workspace Intelligence**: Context-aware suggestions based on actual data
