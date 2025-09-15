# KQL Examples for Application Insights Page Views in Log Analytics Workspaces

This document contains example KQL queries for the AppPageViews table (Application Insights page views) stored in Log Analytics workspaces. Each example includes a natural language prompt and the corresponding KQL query.

---

## Page View Analysis

**Create a chart of page views count over the last 3 days**
```kql
AppPageViews
| where TimeGenerated > ago(3d)
| where ClientType == "Browser"
| summarize count_=sum(ItemCount) by bin(TimeGenerated, 1h)
| render timechart
```
