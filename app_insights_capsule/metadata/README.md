# App Insights Metadata

This folder contains metadata files that describe the structure, columns, and schema details for Azure Application Insights tables.

## Contents

- **`app_requests_metadata.md`** - AppRequests table schema and column descriptions
- **`app_exceptions_metadata.md`** - AppExceptions table schema and column descriptions  
- **`app_traces_metadata.md`** - AppTraces table schema and column descriptions

## Purpose

These metadata files provide:
- **Table schemas** - Complete column lists with data types
- **Column descriptions** - Detailed explanations of what each field contains
- **Data examples** - Sample values to understand field formats
- **Query guidance** - Important notes about using specific columns

## Usage

These files are referenced by:
- `nl_to_kql.py` - For schema-aware KQL generation
- `main.py` - In the AI agent prompts for context

## Related

- **KQL Examples**: See `../kql_examples/` for practical query examples

---
*Part of the Azure Monitor Natural Language KQL Agent project*
