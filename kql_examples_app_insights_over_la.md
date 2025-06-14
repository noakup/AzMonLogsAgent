# KQL Examples for Application Insights Data in Log Analytics Workspaces

This document contains example KQL queries for Application Insights data stored in Log Analytics workspaces (tables like AppRequests, AppExceptions, AppDependencies, etc.). Each example includes a natural language prompt and the corresponding KQL query.

---

## Request and Failure Analysis

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
| summarize failedCount=sumif(ItemCount, Success == false), impactedUsers=dcountif(UserId, Success == false) by OperationName
```

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

---

## Exception Analysis

**What are the 5 most common exceptions?**
```kql
AppExceptions
| summarize _count=sum(ItemCount) by ExceptionType
| top 5 by _count
| sort by _count desc
```

**Exception count by problem ID**
```kql
AppExceptions
| where TimeGenerated > ago(24h)
| summarize count_=sum(ItemCount), impactedUsers=dcount(UserId) by ProblemId
| order by count_ desc
```

**Exception count by problems during the last 24 hours**
```kql
AppExceptions
| where TimeGenerated > ago(24h)
| summarize count_=sum(ItemCount), impactedUsers=dcount(UserId) by ProblemId
| order by count_ desc
```

---

## Page Views and User Analysis

**Create a chart of page views count over the last 3 days**
```kql
AppPageViews
| where TimeGenerated > ago(3d)
| where ClientType == "Browser"
| summarize count_=sum(ItemCount) by bin(TimeGenerated, 1h)
| render timechart
```

---

## Request Duration and Timecharts

**Chart request duration in the last 4 hours**
```kql
AppRequests
| where TimeGenerated > ago(4h)
| summarize avg(DurationMs) by bin(TimeGenerated, 5m)
| render timechart
```

**Create a timechart of request counts, yesterday**
```kql
AppRequests
| where TimeGenerated > startofday(now()-24h) and TimeGenerated < endofday(now()-24h)
| summarize count_=sum(ItemCount) by bin(TimeGenerated, 1h)
| render timechart
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

---

## Traces and Logs

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

**Show traces with cloud_Role name containing "term" and a message with text "given text"**
```kql
AppTraces
| where AppRoleName contains "term" and Message contains "given text"
```

**Show all traces, requests and exceptions with cloud role name "the name"**
```kql
AppTraces
| union AppRequests | union AppExceptions
| where AppRoleName == "something"
```

---

## Custom Events

**Show custom-events with names that contain "this_text"**
```kql
AppEvents
| where Name contains "this_text"
```

**Show custom_events named abcd**
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

**Show all custom events from the last 30 minutes**
```kql
AppEvents
| where TimeGenerated > ago(30m)
```

---

## Advanced Correlation and Joins

**Summarize duration of availabilityresults and duration of pageviews joined by client city.**
```kql
AppAvailabilityResults
| join kind=inner (AppPageViews) on ClientCity
| summarize availabilityDuration=sum(DurationMs), AppPageViewsDuration=sum(DurationMs1) by ClientCity
```

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

---

## Miscellaneous and Utility Queries

**Show all requests containing "term"**
```kql
AppRequests
| where Name contains "term"
```

**What are the results codes of requests containing "term"**
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

**Count requests per operation name, except operation names starting with "subscription"**
```kql
AppRequests
| where OperationName !startswith "subscription"
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

**Show all exceptions by time**
```kql
AppExceptions
| order by TimeGenerated desc
```

**List exceptions with message containing "something"**
```kql
AppExceptions
| where Message contains "something"
```

**List exceptions with outer message containing "something"**
```kql
AppExceptions
| where OuterMessage contains "something"
```

**Exceptions of role some_role**
```kql
AppExceptions
| where AppRoleName == "some_role"
```

**Exceptions of role "some_role" and with severity 1**
```kql
AppExceptions
| where AppRoleName == "some_role"
| where SeverityLevel == 1
```

**Show exceptions with problem id "123"**
```kql
AppExceptions
| where ProblemId == "123"
```

**Show exceptions with problem id other than "123"**
```kql
AppExceptions
| where ProblemId != "123"
```

**Exceptions related to operation "get_value" in the last 3 hours**
```kql
AppExceptions
| where TimeGenerated > ago(3h)
| where OperationName == "get_Value"
```

**Show exceptions with type "poi"**
```kql
AppExceptions
| where ExceptionType == "poi"
```

**All exceptions with operation ID 1234**
```kql
AppExceptions
| where OperationId == "1234"
```

**Count exceptions by outer message, operation and role**
```kql
AppExceptions
| summarize count() by OuterMessage, OperationName, AppRoleName
```

**Count exceptions by message for exceptions of role "the_role"**
```kql
AppExceptions
| where AppRoleName contains "the_role"
| summarize count() by OuterMessage
```

**Top 3 browser exceptions**
```kql
AppExceptions
| where ClientType == 'Browser'
| summarize total_AppExceptions = sum(ItemCount) by ProblemId
| top 3 by total_AppExceptions desc
```
