# KQL Examples for Application Insights Performance Counters in Log Analytics Workspaces

This document contains example KQL queries for the AppPerformanceCounters table (Application Insights performance metrics) stored in Log Analytics workspaces. Each example includes a natural language prompt and the corresponding KQL query.

---

## Performance and Resource Metrics

**Calculate the average process CPU percentage**
```kql
AppPerformanceCounters
| where TimeGenerated > ago(1h)
| where Name == "% Processor Time" and Category == "Process"
| summarize avg(Value)
```

**Find the average available memory in MB on the last 2 hours**
```kql
AppPerformanceCounters
| where TimeGenerated > ago(2h)
| where Name == "Available Bytes"
| summarize MB=avg(Value)/1024/1024
```

**Chart average process storage IO rate in bytes per second, in the last day**
```kql
AppPerformanceCounters
| where TimeGenerated > ago(1d)
| where Name == "IO Data Bytes/sec"
| summarize avg(Value) by bin(TimeGenerated, 5m)
| render timechart
```
