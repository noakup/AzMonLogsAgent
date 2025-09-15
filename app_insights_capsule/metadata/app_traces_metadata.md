# Application traces
Application traces are logged in the "AppTraces" Log analytics table. 
The information in this table can be used to analyze traces by the message, severity, role name etc.

## AppTraces Table structure
| Column name | Data Type | Description |
|-------------|-----------|-------------|
| AppRoleInstance | string | Role instance of the application. |
| AppRoleName  | string | Role name of the application.  |
| AppVersion | string | Version of the application. |
| _BilledSize  | real | The record size in bytes. |
| ClientBrowser | string | Browser running on the client device. |
| ClientCity | string | City where the client device is located. |
| ClientCountryOrRegion | string | Country or region where the client device is located.  |
| ClientIP  | string | IP address of the client device.  |
| ClientModel  | string | Model of the client device. |
| ClientOS  | string | Operating system of the client device.  |
| ClientStateOrProvince | string | State or province where the client device is located.  |
| ClientType | string | Type of the client device.  |
| IKey | string | Instrumentation key of the Azure resource. |
| _IsBillable  | string | Specifies whether ingesting the data is billable. When false, ingestion isn't billed to your account. |
| ItemCount | int | Number of telemetry items represented by a single sample item.  |
| Measurements | dynamic | Application-defined measurements. |
| Message | string | Trace message. |
| OperationId  | string | Application-defined operation ID. |
| OperationName | string | Application-defined name of the overall operation. Typically matches Name values for AppRequests. |
| ParentId  | string | ID of the parent operation. |
| Properties | dynamic | Application-defined properties. |
| ReferencedItemId | string | ID of the item with additional details about the trace. |
| ReferencedType  | string | Name of the table with additional details about the trace. |
| ResourceGUID | string | Unique, persistent identifier of an Azure resource. |
| _ResourceId  | string | A unique identifier for the resource that the record is associated with. |
| SDKVersion | string | Version of the SDK used by the application to generate this telemetry item. |
| SessionId | string | Application-defined session ID. |
| SeverityLevel | int | Severity level of the trace. |
| SourceSystem | string | Type of agent the event was collected by (e.g., OpsManager, Linux, Azure).  |
| _SubscriptionId | string | A unique identifier for the subscription that the record is associated with. |
| SyntheticSource | string | Synthetic source of the operation. |
| TenantId  | string | The Log Analytics workspace ID. |
| TimeGenerated | datetime  | Date and time when trace was recorded.  |
| Type | string | The name of the table. |
| UserAccountId | string | Application-defined account associated with the user.  |
| UserAuthenticatedId | string | Persistent string that uniquely represents each authenticated user in the application. |
| UserId | string | Anonymous ID of a user accessing the application. |
