# KQL Examples for Container Insights logs

This document contains example KQL queries for the ContainerLogV2 table which stores container logs. Each example includes a natural language prompt and the corresponding KQL query.

---

**calculate error rate by workload last 30m**
```kql
ContainerLogV2
| where TimeGenerated > ago(30m)
| extend Labels = KubernetesMetadata.podLabels
| extend WorkloadName = tostring(coalesce(Labels['app.kubernetes.io/name'], Labels['app'], PodName))
| extend IsError = LogLevel in~ ('CRITICAL','ERROR') or LogSource=='stderr'
| summarize Errors=countif(IsError), Total=count() by WorkloadName, PodNamespace
| extend ErrorRatePct = 100.0 * Errors / iff(Total==0,1,Total)
| order by ErrorRatePct desc
```

**How long are pods pending in finance namespace?**
```kql
KubePodInventory
| where TimeGenerated > ago(1h)
| where Namespace == 'finance' and PodStatus == 'Pending'
| summarize FirstSeen=min(TimeGenerated), LastSeen=max(TimeGenerated), Samples=count() by PodName
| extend PendingMinutes = datetime_diff('minute', LastSeen, FirstSeen)
| order by PendingMinutes desc
```

**find latency over 750ms for payments workload in the last hour**
```kql
ContainerLogV2
| where TimeGenerated > ago(1h)
| extend Labels = KubernetesMetadata.podLabels
| extend WorkloadName = tostring(coalesce(Labels['app.kubernetes.io/name'], Labels['app'], PodName))
| where WorkloadName =~ 'payments'
| extend Plain = tostring(LogMessage)
| extend LatencyMs = toint(extract('latency[=:]\\s?([0-9]+)ms', 1, Plain))
| where LatencyMs > 750
| project TimeGenerated, PodNamespace, PodName, ContainerName, LatencyMs, Plain
```