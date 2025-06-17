# KQL Examples for Application Insights Multi-Entity Queries in Log Analytics Workspaces

This document contains example KQL queries that join or correlate multiple Application Insights tables (such as AppRequests, AppExceptions, AppTraces, AppDependencies, etc.) in Log Analytics workspaces. Each example includes a natural language prompt and the corresponding KQL query.

---

## Multi-Entity Analysis

**What logs are associated with failures over the last 30 minutes**
```kql
AppTraces
| where TimeGenerated > ago(30m)
| join kind=inner (
    AppRequests
    | where TimeGenerated > ago(30m)
    | where Success == False
) on OperationId
```

**What traces are associated with the most recent request failures**
```kql
AppTraces
| where TimeGenerated > ago(30m)
| where OperationId in (
    AppRequests
    | where TimeGenerated > ago(30m)
    | where Success == False
    | project OperationId
)
```

**What exceptions are associated with the most recent failures over the last 30 minutes?**
```kql
AppExceptions
| where TimeGenerated > ago(30m)
| where OperationId in (
    AppRequests
    | where TimeGenerated > ago(30m)
    | where Success == False
)
```

**Show all traces, requests and exceptions with cloud role name "the name"**
```kql
AppTraces
| union AppRequests | union AppExceptions
| where AppRoleName == "something"
```

**Summarize duration of availabilityresults and duration of pageviews joined by client city.**
```kql
AppAvailabilityResults
| join kind=inner (AppPageViews) on ClientCity
| summarize availabilityDuration=sum(DurationMs), AppPageViewsDuration=sum(DurationMs1) by ClientCity
```