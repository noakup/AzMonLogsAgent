# usage_kql_examples.md

This file contains example natural language prompts and their corresponding KQL queries for the Azure Log Analytics Usage table.

## Example

**Prompt:**
Show me the total ingestion volume in MB in the last 24 hours based on the Usage table

**KQL:**
Usage | summarize sum(Quantity)

---

Add more prompt/KQL pairs below as needed.
