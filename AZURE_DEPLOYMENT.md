# Azure Deployment Guide for Azure Monitor Logs Agent

## Prerequisites
1. Azure account with active subscription
2. Azure CLI installed locally
3. Git repository (already set up)

## Deployment Steps

### 1. Install Azure CLI (if not already installed)
```bash
# macOS
brew install azure-cli

# Or download from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
```

### 2. Login to Azure
```bash
az login
```

### 3. Create Resource Group
```bash
az group create --name rg-azmonlogsagent --location "East US"
```

### 4. Create App Service Plan
```bash
az appservice plan create \
  --name asp-azmonlogsagent \
  --resource-group rg-azmonlogsagent \
  --sku B1 \
  --is-linux
```

### 5. Create Web App
```bash
az webapp create \
  --resource-group rg-azmonlogsagent \
  --plan asp-azmonlogsagent \
  --name azmonlogsagent-webapp \
  --runtime "PYTHON|3.11" \
  --deployment-source-url https://github.com/noakup/AzMonLogsAgent \
  --deployment-source-branch main
```

### 6. Configure App Settings
```bash
# Set Python version
az webapp config appsettings set \
  --resource-group rg-azmonlogsagent \
  --name azmonlogsagent-webapp \
  --settings PYTHON_VERSION=3.11

# Set startup command
az webapp config set \
  --resource-group rg-azmonlogsagent \
  --name azmonlogsagent-webapp \
  --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 main_azure:app"

# Enable build automation
az webapp config appsettings set \
  --resource-group rg-azmonlogsagent \
  --name azmonlogsagent-webapp \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true ENABLE_ORYX_BUILD=true
```

### 7. Configure Azure OpenAI (Required for Explain Feature)
```bash
# Set your Azure OpenAI configuration
az webapp config appsettings set \
  --resource-group rg-azmonlogsagent \
  --name azmonlogsagent-webapp \
  --settings \
    AZURE_OPENAI_ENDPOINT="https://your-openai-instance.openai.azure.com/" \
    AZURE_OPENAI_DEPLOYMENT="your-gpt-4-deployment-name" \
    AZURE_OPENAI_API_VERSION="2024-02-15-preview"
```

### 8. Enable System-Assigned Managed Identity
```bash
az webapp identity assign \
  --resource-group rg-azmonlogsagent \
  --name azmonlogsagent-webapp
```

### 9. Deploy from GitHub
```bash
az webapp deployment source config \
  --resource-group rg-azmonlogsagent \
  --name azmonlogsagent-webapp \
  --repo-url https://github.com/noakup/AzMonLogsAgent \
  --branch main \
  --manual-integration
```

## Post-Deployment Configuration

### 1. Assign Azure Monitor Reader Role
After deployment, assign the web app's managed identity the "Log Analytics Reader" role on your Log Analytics workspaces.

### 2. Test the Application
Visit: `https://azmonlogsagent-webapp.azurewebsites.net`

### 3. Configure Custom Domain (Optional)
```bash
az webapp config hostname add \
  --resource-group rg-azmonlogsagent \
  --webapp-name azmonlogsagent-webapp \
  --hostname your-custom-domain.com
```

## Environment Variables to Set in Azure Portal

1. **AZURE_OPENAI_ENDPOINT** - Your Azure OpenAI endpoint
2. **AZURE_OPENAI_DEPLOYMENT** - Your GPT-4 deployment name  
3. **AZURE_OPENAI_API_VERSION** - API version (e.g., "2024-02-15-preview")

## Monitoring and Logs

View application logs:
```bash
az webapp log tail --resource-group rg-azmonlogsagent --name azmonlogsagent-webapp
```

## Updating the Application

The app will automatically redeploy when you push changes to the main branch of your GitHub repository.

## Scaling

To scale up for production:
```bash
az appservice plan update \
  --resource-group rg-azmonlogsagent \
  --name asp-azmonlogsagent \
  --sku S1
```

## Security Considerations

1. Enable HTTPS Only
2. Configure Authentication if needed
3. Set up Application Insights for monitoring
4. Configure network restrictions if required

## Troubleshooting

1. Check application logs in Azure Portal
2. Verify all environment variables are set
3. Ensure managed identity has proper permissions
4. Check that requirements-azure.txt includes all dependencies