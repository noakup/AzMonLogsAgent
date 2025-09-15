# KQL Examples for Application Insights Dependencies in Log Analytics Workspaces

This document contains example KQL queries for the AppDependencies table (Application Insights dependencies) stored in Log Analytics workspaces. Each example includes a natural language prompt and the corresponding KQL query.

---

## Dependency Analysis

**Count dependency failures by type in the last 3 days**
```kql
AppDependencies
| where TimeGenerated > ago(3d)
| where Success == false
| summarize _count=sum(ItemCount) by ExceptionType
| sort by _count desc
```

**Failed browser dependency count by target in the past day**
```kql
AppDependencies
| where TimeGenerated > ago(1d)
| where ClientType == "Browser"
| summarize failedCount=sumif(ItemCount, Success == false) by Target
```

**Chart dependencies count over time for the last 6 hours**
```kql
AppDependencies
| where TimeGenerated > ago(6h)
| summarize count_=sum(ItemCount) by bin(TimeGenerated, 5m)
| render timechart
```

**What dependencies failed in browser calls the last hour and how many users were impacted? Group by target**
```kql
AppDependencies
| where TimeGenerated > ago(1h)
| summarize failedCount=sumif(ItemCount, Success == false), impactedUsers=dcountif(UserId, Success == false) by Target
| order by failedCount desc
```

**Count failed dependencies by result code**
```kql
AppDependencies
| where TimeGenerated > ago(24h)
| where Success == false
| summarize _count=sum(ItemCount) by ResultCode
| sort by _count desc
```
