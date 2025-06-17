# KQL Examples for Application Insights Data in Log Analytics Workspaces

This document contains example KQL queries for Application Insights requests stored in Log Analytics workspaces. Each example includes a natural language prompt and the corresponding KQL query.

**How many requests failed over the last day**
```kql
AppRequests
| where TimeGenerated > ago(1d)
| summarize failedCount=sumif(ItemCount, Success == false)
```

**Chart failed requests over the last hour**
```kql
AppRequests
| where TimeGenerated > ago(1h)
| summarize failedCount=sumif(ItemCount, Success == false) by bin(TimeGenerated, 1m)
| render timechart
```

**How many requests over the last day?**
```kql
AppRequests
| where TimeGenerated > ago(1d)
| summarize failedCount=sum(ItemCount)
```

**What are the top 3 failed response codes in the last week?**
```kql
AppRequests
| where TimeGenerated > ago(7d)
| where Success == false
| summarize _count=sum(ItemCount) by ResultCode
| top 3 by _count
| sort by _count desc
```

**Which operations failed in the last day**
```kql
AppRequests
| where TimeGenerated > ago(1d)
| summarize failedCount=sumif(ItemCount, Success == false) by OperationName
```

**Failed operations in the past day and how many users were impacted**
```kql
AppRequests
| where TimeGenerated > ago(1d)
| where Success == false
| summarize failedCount=sum(ItemCount), impactedUsers=dcount(UserId) by OperationName
| order by impactedUsers
```

**Show how many requests are in each performance-bucket**
```kql
AppRequests
| summarize requestCount=sum(ItemCount), avgDuration=avg(DurationMs) by PerformanceBucket
| order by avgDuration asc // sort by average request duration
| project-away avgDuration // no need to display avgDuration, we used it only for sorting results
| render barchart
```

**Chart Request count over the last day**
```kql
AppRequests
| where TimeGenerated > ago(1d)
| summarize totalCount=sum(ItemCount) by bin(TimeGenerated, 30m)
| render timechart
```

**Calculate request count and duration by operations**
```kql
AppRequests
| summarize RequestsCount=sum(ItemCount), AverageDuration=avg(DurationMs), percentiles(DurationMs, 50, 95, 99) by OperationName
| order by RequestsCount desc // order from highest to lower (descending)
```

**Show me the top 10 failed requests**
```kql
AppRequests
| where Success == false
| summarize failedCount=sum(ItemCount) by Name
| top 10 by failedCount desc
| render barchart
```

**Chart request duration in the last 4 hours**
```kql
AppRequests
| where TimeGenerated > ago(4h)
| summarize avg(DurationMs) by bin(TimeGenerated, 10m)
| render timechart
```

**Create a timechart of request counts, yesterday**
```kql
AppRequests
| where TimeGenerated > startofday(now()-24h) and TimeGenerated < endofday(now()-24h)
| summarize count_=sum(ItemCount) by bin(TimeGenerated, 1h)
| render timechart
```

**Find which exceptions led to failed requests in the past hour**
```kql
AppRequests
| where TimeGenerated > ago(1h) and Success == false
| join kind= inner (
	AppExceptions
	| where TimeGenerated > ago(1h)
  ) on OperationId
| project exceptionType = Type, failedMethod = Method, requestName = Name, requestDuration = DurationMs
```


**How many requests were handled hourly, today**
```kql
AppRequests
| where TimeGenerated > startofday(now()) and TimeGenerated < now()
| summarize count_=sum(ItemCount) by bin(TimeGenerated, 1h)
| sort by TimeGenerated asc
```

**Calculate request duration 50, 95 and 99 percentiles**
```kql
AppRequests
| where TimeGenerated > ago(1d)
| summarize percentiles(DurationMs, 50, 95, 99)
```

**Show all requests containing "term"**
```kql
AppRequests
| where Name contains "term"
```

**What are the result codes of requests containing "term"**
```kql
AppRequests
| where Name contains "term"
| summarize count() by ResultCode
```

**List requests to url with "value"**
```kql
AppRequests
| where Url contains "Value"
```

**Requests named abc**
```kql
AppRequests
| where Name == "abc"
```

**Show all requests from new to old**
```kql
AppRequests
| order by TimeGenerated desc
```

**Show all requests from old to new**
```kql
AppRequests
| order by TimeGenerated asc
```

**Count the total number of requests every half hour**
```kql
AppRequests
| summarize totalCount=sum(ItemCount) by bin(TimeGenerated, 30m)
```

**Show requests of operations with abc**
```kql
AppRequests
| where OperationName contains "abc"
```

**Show requests of role name admin**
```kql
AppRequests
| where AppRoleName == "admin"
```

**All requests related to operation "123"**
```kql
AppRequests
| where OperationId == "123"
```

**Find requests with operation name other than "abc"**
```kql
AppRequests
| where OperationName != "abc"
```

**Find all requests with operation name that doesn't start with "qwe"**
```kql
AppRequests
| where OperationName !startswith "qwe"
```

**Count requests per operation name, except operation names starting with "sub"**
```kql
AppRequests
| where OperationName !startswith "sub"
| summarize count() by OperationName
```

**What are the top 5 operations?**
```kql
AppRequests
| summarize count() by OperationName
| top 5 by count_
```

**Count requests by client IP**
```kql
AppRequests
| summarize count() by ClientIP
| order by count_ desc
```

**Count requests from each city**
```kql
AppRequests
| summarize count() by ClientCity, ClientStateOrProvince, ClientCountryOrRegion
| order by count_ desc
```

**Requests by source country today**
```kql
AppRequests
| where TimeGenerated > ago(1d)
| summarize count() by ClientCountryOrRegion
| order by count_ desc
```

**Create a pie chart of the top 10 countries by traffic**
```kql
AppRequests
| summarize CountByCountry=count() by ClientCountryOrRegion
| top 10 by CountByCountry
| render piechart
```

**Show requests that returned 500 in the last 12 hours**
```kql
AppRequests
| where TimeGenerated > ago(12h)
| where ResultCode == 500
```

**Show all requests that didn't return 200 in the last hour**
```kql
AppRequests
| where TimeGenerated > ago(1h)
| where ResultCode != 200
```

**Count requests by URL**
```kql
AppRequests
| summarize count() by Url
```
