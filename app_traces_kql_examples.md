# KQL Examples for Application Insights Traces in Log Analytics Workspaces

This document contains example KQL queries for the AppTraces table (Application Insights traces/logs) stored in Log Analytics workspaces. Each example includes a natural language prompt and the corresponding KQL query.

---

## Traces and Logs Analysis

**Show all traces with a message containing "some_text"**
```kql
AppTraces
| where Message contains "some_text"
```

**Show traces of operations named name1 or name2**
```kql
AppTraces
| where OperationName in ("Name1", "Name2")
```

**Show all traces where the message contains "asd" and "sdf"**
```kql
AppTraces
| where Message contains "asd" and Message contains "sdf"
```

**Show all traces where the message starts with "error"**
```kql
AppTraces
| where Message startswith "error"
```

**List all traces in the last hour, sort by time**
```kql
AppTraces
| where TimeGenerated > ago(1h)
| order by TimeGenerated desc
```

**Show all traces with the text "some_text"**
```kql
AppTraces
| where Message contains "some_text" or Properties contains "some_text"
```

**Get all traces with operation id 123 in the last 24 hours**
```kql
AppTraces
| where TimeGenerated > ago(24h)
| where OperationId == "123"
```

**All traces with cloud role name containing "abc"**
```kql
AppTraces
| where AppRoleName contains "abc"
```

**Count traces messages of messages containing "server1"**
```kql
AppTraces
| where Message contains "server1"
| summarize count() by Message
```

**Show all traces with operation name xyz from the last week**
```kql
AppTraces
| where TimeGenerated > ago(7d)
| where OperationName == "xyz"
```

**Find traces with severity level 3**
```kql
AppTraces
| where SeverityLevel == 3
```

**Show traces with role name containing "term" and a message with text "given text"**
```kql
AppTraces
| where AppRoleName contains "term" and Message contains "given text"
```

**Show all traces with role name "the name"**
```kql
AppTraces
| where AppRoleName == "the name"
```
