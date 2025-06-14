# KQL Examples for Application Insights Resources

This document contains example KQL queries for Application Insights resources (accessed directly via the Application Insights resource in Azure, not via Log Analytics workspaces).

## Request Performance Metrics

### Average Response Time by Request
```kql
requests
| where timestamp > ago(24h)
| summarize avgDuration=avg(duration) by name
| order by avgDuration desc
```

### Failed Requests
```kql
requests
| where timestamp > ago(24h)
| where success == "False"
| summarize count() by name, resultCode
| order by count_ desc
```

### P95 Response Time
```kql
requests 
| where timestamp > ago(24h)
| summarize percentile(duration, 95) by bin(timestamp, 15m), name
| render timechart
```

## Dependency Analysis

### Slow Dependencies
```kql
dependencies
| where timestamp > ago(24h)
| summarize avgDuration=avg(duration) by type, target, name
| order by avgDuration desc
| take 20
```

### Failed Dependencies
```kql
dependencies
| where timestamp > ago(24h) 
| where success == "False"
| summarize count() by type, target, name, resultCode
| order by count_ desc
```

### Dependency Calls per Minute
```kql
dependencies
| where timestamp > ago(3h)
| summarize count() by bin(timestamp, 1m), target
| render timechart
```

## Exception Tracking

### Most Common Exceptions
```kql
exceptions
| where timestamp > ago(24h)
| summarize count() by type, method
| order by count_ desc
| take 20
```

### Exception Timeline
```kql
exceptions
| where timestamp > ago(7d)
| summarize count() by bin(timestamp, 1h), type
| render timechart
```

### Exceptions with Stack Traces
```kql
exceptions
| where timestamp > ago(24h)
| project timestamp, type, method, outerMessage, details
| order by timestamp desc
```

## Page View Analysis

### Most Visited Pages
```kql
pageViews
| where timestamp > ago(24h)
| summarize count() by url
| order by count_ desc
| take 20
```

### Page Load Time
```kql
pageViews
| where timestamp > ago(24h)
| summarize avgDuration=avg(duration) by url
| order by avgDuration desc
| take 20
```

### User Engagement
```kql
pageViews
| where timestamp > ago(7d)
| summarize userCount=dcount(user_Id) by bin(timestamp, 1d)
| render timechart
```

## Custom Events and Metrics

### Custom Event Count
```kql
customEvents
| where timestamp > ago(24h)
| summarize count() by name
| order by count_ desc
```

### Custom Metric Analysis
```kql
customMetrics
| where timestamp > ago(7d)
| summarize avg(value) by name, bin(timestamp, 1h)
| render timechart
```

## Availability Tests

### Failed Availability Tests
```kql
availabilityResults
| where timestamp > ago(24h)
| where success == "False"
| extend location=tostring(customDimensions["location"])
| summarize count() by name, location
| order by count_ desc
```

### Availability Test Response Time
```kql
availabilityResults
| where timestamp > ago(7d)
| extend location=tostring(customDimensions["location"])
| summarize avgDuration=avg(duration) by bin(timestamp, 1h), name, location
| render timechart
```

## Performance Counters

### CPU Usage
```kql
performanceCounters
| where timestamp > ago(3h)
| where categoryName == "Processor" and counterName == "% Processor Time"
| summarize avg(counterValue) by bin(timestamp, 5m), cloud_RoleInstance
| render timechart
```

### Memory Usage
```kql
performanceCounters
| where timestamp > ago(3h)
| where categoryName == "Memory" and counterName == "Available Bytes"
| summarize availableMB=avg(counterValue) / 1024 / 1024 by bin(timestamp, 5m), cloud_RoleInstance
| render timechart
```

## Cross-Table Analysis

### Failed Requests with Exceptions
```kql
requests
| where timestamp > ago(24h)
| where success == "False" 
| join kind=inner (
    exceptions
    | where timestamp > ago(24h)
) on operation_Id
| project timestamp, name, resultCode, type, method, outerMessage
| order by timestamp desc
```

### End-to-End Transaction Analysis
```kql
let startTime = ago(1h);
let endTime = now();
requests
| where timestamp between (startTime .. endTime)
| where name == "GET /api/data"
| project reqTimestamp=timestamp, operation_Id, duration
| join kind=inner (
    dependencies
    | where timestamp between (startTime .. endTime)
) on operation_Id
| summarize requestCount=dcount(operation_Id),
    avgRequestDuration=avg(duration),
    avgDependencyDuration=avg(duration1)
    by bin(reqTimestamp, 5m), target
| render timechart
```

## User and Session Analysis

### Active Users
```kql
pageViews
| where timestamp > ago(7d)
| summarize dcount(user_Id) by bin(timestamp, 1d)
| render columnchart
```

### Session Duration
```kql
pageViews
| where timestamp > ago(24h)
| summarize duration=max(timestamp) - min(timestamp) by session_Id
| extend durationInMinutes = duration / 1m
| summarize percentiles(durationInMinutes, 50, 75, 90, 95)
```

## Advanced Troubleshooting

### Correlation Between Metrics
```kql
let timeRange = 7d;
let timeBin = 1h;
requests
| where timestamp > ago(timeRange)
| summarize requestCount=count() by bin(timestamp, timeBin)
| join kind=inner (
    exceptions
    | where timestamp > ago(timeRange) 
    | summarize exceptionCount=count() by bin(timestamp, timeBin)
) on timestamp
| project timestamp, requestCount, exceptionCount
| extend errorRatio = 1.0 * exceptionCount / requestCount
| render timechart
```

### Detecting Anomalies
```kql
requests
| where timestamp > ago(7d)
| summarize count() by bin(timestamp, 15m)
| extend (anomalies, baseline, anomalyScore) = series_decompose_anomalies(count_, 1.5, -1, 'linefit')
| where anomalies > 0
| render timechart with(anomalycolumns=anomalies)
```

## Performance Optimization Queries

### Slow Database Calls
```kql
dependencies
| where timestamp > ago(24h)
| where type == "SQL" or target endswith ".database.windows.net"
| where duration > 100
| summarize count(), avg(duration), max(duration) by target, name
| order by avg_duration desc
```

### Top N Performance Issues
```kql
union requests, dependencies, pageViews
| where timestamp > ago(24h)
| summarize avgDuration=avg(duration) by type=iff(itemType=="request", "Request", iff(itemType=="dependency", "Dependency", "PageView")), name
| top 20 by avgDuration desc
| order by avgDuration desc
```

## Resource Usage and Billing

### Data Ingestion by Table
```kql
union withsource=TableName *
| where timestamp > ago(30d)
| summarize count() by TableName, bin(timestamp, 1d)
| render columnchart
```

### Request Count by Operation
```kql
requests
| where timestamp > ago(7d)
| summarize count() by operation_Name
| order by count_ desc
| render piechart
```
