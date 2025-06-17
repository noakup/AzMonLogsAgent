# Application requests
 Application requests are logged in the "AppRequests" Log analytics table. 
 The information in this table can be used to analyze request duration, success rates, operations, origin, number of users impacted etc.

## AppRequests Table structure
| Column | Type | Description |
|---|---|---|
| AppRoleInstance | string | Role instance of the application. |
| AppRoleName | string | Role name of the application. |
| AppVersion | string | Version of the application. |
| _BilledSize | real | The record size in bytes |
| ClientBrowser | string | Browser running on the client device. |
| ClientCity | string | City where the client device is located. |
| ClientCountryOrRegion | string | Country or region where the client device is located. |
| ClientIP | string | IP address of the client device. |
| ClientModel | string | Model of the client device. |
| ClientOS | string | Operating system of the client device. |
| ClientStateOrProvince | string | State or province where the client device is located. |
| ClientType | string | Type of the client device. |
| DurationMs | real | Number of milliseconds it took the application to handle the request. |
| Id | string | Application-generated, unique request ID. |
| IKey | string | Instrumentation key of the Azure resource. |
| _IsBillable | string | Specifies whether ingesting the data is billable. When _IsBillable is false ingestion isn't billed to your Azure account |
| ItemCount | int | Number of telemetry items represented by a single sample item. |
| Measurements | dynamic | Application-defined measurements. |
| Name | string | Human-readable name of the request. |
| OperationId | string | Application-defined operation ID. |
| OperationName | string | Application-defined name of the overall operation. The OperationName values typically match the Name values for AppRequests. |
| ParentId | string | ID of the parent operation. |
| Properties | dynamic | Application-defined properties. |
| ReferencedItemId | string | Id of the item with additional details about the request. |
| ReferencedType | string | Name of the table with additional details about the request. |
| ResourceGUID | string | Unique, persistent identifier of an Azure resource. |
| _ResourceId | string | A unique identifier for the resource that the record is associated with |
| ResultCode | string | Result code returned by the application after handling the request. |
| SDKVersion | string | Version of the SDK used by the application to generate this telemetry item. |
| SessionId | string | Application-defined session ID. |
| Source | string | Friendly name of the request source, when known. Source is based on the metadata supplied by the caller. |
| SourceSystem | string | The type of agent the event was collected by. For example, OpsManager for Windows agent, either direct connect or Operations Manager, Linux for all Linux agents, or Azure for Azure Diagnostics |
| _SubscriptionId | string | A unique identifier for the subscription that the record is associated with |
| Success | bool | Indicates whether the application handled the request successfully. |
| SyntheticSource | string | Synthetic source of the operation. |
| TenantId | string | The Log Analytics workspace ID |
| TimeGenerated | datetime | Date and time when request processing started. |
| Type | string | The name of the table |
| Url | string | URL of the request. |
| UserAccountId | string | Application-defined account associated with the user. |
| UserAuthenticatedId | string | Persistent string that uniquely represents each authenticated user in the application. |
| UserId | string | Anonymous ID of a user accessing the application. |
