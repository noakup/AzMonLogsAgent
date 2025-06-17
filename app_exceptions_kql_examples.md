# KQL Examples for Application Insights Exceptions in Log Analytics Workspaces

This document contains example KQL queries for the AppExceptions table (Application Insights exceptions) stored in Log Analytics workspaces. Each example includes a natural language prompt and the corresponding KQL query.

---

## Exception Analysis

**What are the 5 most common exceptions?**
```kql
AppExceptions
| summarize _count=sum(ItemCount) by ExceptionType
| top 5 by _count
| sort by _count desc
```

**Exception count and impacted user by problem ID**
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
