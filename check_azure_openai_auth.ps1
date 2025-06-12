# check_azure_openai_auth.ps1
# PowerShell script to check Azure OpenAI endpoint, deployment, and key

$endpoint = $env:AZURE_OPENAI_ENDPOINT
$deployment = $env:AZURE_OPENAI_DEPLOYMENT
$key = $env:AZURE_OPENAI_KEY
$apiVersion = "2024-02-15-preview"

Write-Host "Endpoint: $endpoint"
Write-Host "Deployment: $deployment"
Write-Host "Key (first 5 chars): $($key.Substring(0,5))..."

$body = @{
    "messages" = @(
        @{ "role" = "system"; "content" = "You are an expert in KQL." },
        @{ "role" = "user"; "content" = "Show me all records." }
    )
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "$endpoint/openai/deployments/$deployment/chat/completions?api-version=$apiVersion" `
    -Headers @{ "api-key" = $key; "Content-Type" = "application/json" } `
    -Method Post -Body $body

Write-Host "Response:"
$response | ConvertTo-Json -Depth 5
