# 📂 Application Insights KQL Examples

This folder contains KQL examples and metadata files specifically for Application Insights data in Log Analytics workspaces.

## 📋 Contents

### **KQL Example Files**
- `app_requests_kql_examples.md` - HTTP requests analysis examples
- `app_exceptions_kql_examples.md` - Error and exception tracking examples
- `app_traces_kql_examples.md` - Application trace and log analysis examples
- `app_dependencies_kql_examples.md` - External service monitoring examples
- `app_page_views_kql_examples.md` - Page view analysis examples
- `app_custom_events_kql_examples.md` - Custom event tracking examples
- `app_performance_kql_examples.md` - Performance metrics examples
- `app_multiple_entities_kql_examples.md` - Multi-table join examples

### **Metadata Files**
Metadata files are located in the `../metadata/` folder:
- `../metadata/app_requests_metadata.md` - AppRequests table schema and column descriptions
- `../metadata/app_exceptions_metadata.md` - AppExceptions table schema and column descriptions
- `../metadata/app_traces_metadata.md` - AppTraces table schema and column descriptions

## 🎯 **Purpose**

These files serve as:
- **Reference material** for understanding Application Insights table structures
- **Example queries** for common monitoring scenarios
- **Training data** for natural language to KQL translation
- **Documentation** for developers working with Application Insights in Log Analytics

## 🔧 **Usage**

These files are referenced by:
- `nl_to_kql.py` - For AI-powered translation context
- `logs_agent.py` - For example browsing functionality
- `web_app.py` - For web interface example categories
- Various NL-to-KQL tools - For scenario-specific translations

## 📝 **Note**

All examples are designed for **Application Insights data in Log Analytics workspaces**, which uses different table and column names compared to classic Application Insights (e.g., `AppRequests` instead of `requests`, `TimeGenerated` instead of `timestamp`).

---
*Organized on September 14, 2025*
