# Azure Kubernetes Service Schema

## Overview

We create 3 tables:
- AKSKubernetesAudit (corresponds to the kube-audit diagnostic setting)
- AKSKubernetesAuditAdmin (corresponds to the kube-audit-admin diagnostic setting)
- AKSControlPlane (corresponds to non-audit diagnostic settings)

**AKSControlPlane** consumes from multiple categories, so the manifest needs special treatment to allow combining all of those different `dataType` values together. For each different incoming category we need to duplicate the schema in manifest, with these differences:

1. Use these 4 properties instead of “name”
```
"workflowName": "<uniqueName>Workflow",
"transformName": "<uniqueName>",
"physicalName": "<schemaName>",
"logicalName": "<schemaName>",
```

2. Add `"isChangeColumnInternalNameAllowed": true,` in schema metadata

3. In the 2nd copy of the schema and rest of copies, add
```
"outputSchema": {
  "name": "<schemaName>",
  "version": <version of the first copy, that don’t have this outputSchema>
},
```

4. Each copy should have different dataTypeId for each different category stream.

## Testing

The CI process tests using the sample input and output json files. To exercise transforms locally, you can simulate some of this process with code like the following:

```
let auditAdminTable = datatable(properties:dynamic, ['time']:datetime) [
  dynamic({
            "log": "{\"kind\":\"Event\",\"apiVersion\":\"audit.k8s.io/v1\",\"level\":\"Metadata\",\"auditID\":\"99b31d64-f8fb-444b-b6ce-c9daa08dc0ba\",\"stage\":\"ResponseComplete\",\"requestURI\":\"/apis/coordination.k8s.io/v1/namespaces/kube-system/leases/external-attacher-leader-disk-csi-azure-com\",\"verb\":\"update\",\"user\":{\"username\":\"aksService\",\"groups\":[\"system:masters\",\"system:authenticated\"]},\"sourceIPs\":[\"172.31.30.22\"],\"userAgent\":\"Go-http-client/2.0\",\"objectRef\":{\"resource\":\"leases\",\"namespace\":\"kube-system\",\"name\":\"external-attacher-leader-disk-csi-azure-com\",\"uid\":\"8263e3a3-b320-41fe-aa6d-1a38297360ff\",\"apiGroup\":\"coordination.k8s.io\",\"apiVersion\":\"v1\",\"resourceVersion\":\"356651\"},\"responseStatus\":{\"metadata\":{},\"code\":200},\"requestReceivedTimestamp\":\"2023-01-10T22:13:00.640063Z\",\"stageTimestamp\":\"2023-01-10T22:13:00.646142Z\",\"annotations\":{\"authorization.k8s.io/decision\":\"allow\",\"authorization.k8s.io/reason\":\"\"}}\n",
            "stream": "stdout",
            "pod": "kube-apiserver-68df4876bd-74k6n"
        }), "2023-01-10T22:13:00.0000000Z",
  dynamic({
            "log": "{\"kind\":\"Event\",\"apiVersion\":\"audit.k8s.io/v1\",\"level\":\"RequestResponse\",\"auditID\":\"b5a18ac9-ab03-44e5-8ad6-86a81fcd233b\",\"stage\":\"ResponseComplete\",\"requestURI\":\"/api/v1/nodes/aks-agentpool-20062077-vmss000002?fieldManager=kubectl-label\",\"verb\":\"patch\",\"user\":{\"username\":\"aksService\",\"groups\":[\"system:masters\",\"system:authenticated\"]},\"sourceIPs\":[\"127.0.0.1\"],\"userAgent\":\"kubectl/v1.24.6 (linux/amd64) kubernetes/6c23b67\",\"objectRef\":{\"resource\":\"nodes\",\"name\":\"aks-agentpool-20062077-vmss000002\",\"apiVersion\":\"v1\"},\"responseStatus\":{\"metadata\":{},\"code\":200},\"requestObject\":\"skipped-too-big-size-object\",\"responseObject\":\"skipped-too-big-size-object\",\"requestReceivedTimestamp\":\"2023-01-10T22:52:33.367799Z\",\"stageTimestamp\":\"2023-01-10T22:52:33.388283Z\",\"annotations\":{\"authorization.k8s.io/decision\":\"allow\",\"authorization.k8s.io/reason\":\"\"}}\n",
            "stream": "stdout",
            "pod": "kube-apiserver-68df4876bd-74k6n"
        }), "2023-01-10T22:52:33.0000000Z"
];
auditAdminTable
| extend parsed_log=parse_json(tostring(properties.log))
| project
TimeGenerated=todatetime(["time"]),
Level=parsed_log.level,
AuditId=parsed_log.auditID,
Stage=parsed_log.stage,
RequestUri=parsed_log.requestURI,
Verb=parsed_log.verb,
UserName=parsed_log.user.username,
User=parsed_log.user,
SourceIps=parsed_log.sourceIPs,
UserAgent=parsed_log.userAgent,
ObjectRef=parsed_log.objectRef,
ResponseStatus=parsed_log.responseStatus,
RequestObject=parsed_log.requestObject,
ResponseObject=parsed_log.responseObject,
RequestReceivedTime=parsed_log.requestReceivedTimestamp,
StageReceivedTime=parsed_log.stageTimestamp,
Annotations=parsed_log.annotations,
PodName=properties.pod
```