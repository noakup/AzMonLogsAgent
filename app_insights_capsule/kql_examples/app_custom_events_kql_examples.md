# KQL Examples for Application Insights Custom Events in Log Analytics Workspaces

This document contains example KQL queries for the AppEvents table (Application Insights custom events) stored in Log Analytics workspaces. Each example includes a natural language prompt and the corresponding KQL query.

---

## Custom Events Analysis

**Show events with names that contain "this_text"**
```kql
AppEvents
| where Name contains "this_text"
```

**Show app events named abcd**
```kql
AppEvents
| where Name == "abcd"
```

**List all custom events of user "a_user", by time**
```kql
AppEvents
| where UserId == "a_user"
| order by TimeGenerated desc
```

**Show events from the last 30 minutes**
```kql
AppEvents
| where TimeGenerated > ago(30m)
```
