#!/bin/bash

# Azure Monitor Logs Agent - Automated Deployment Script
# This script will deploy your application to Azure App Service

set -e

echo "🚀 Starting Azure App Service deployment for Azure Monitor Logs Agent..."

# Variables (you can modify these)
RESOURCE_GROUP="rg-azmonlogsagent"
APP_SERVICE_PLAN="asp-azmonlogsagent"
WEB_APP_NAME="azmonlogsagent-webapp"
LOCATION="East US"
GITHUB_REPO="https://github.com/noakup/AzMonLogsAgent"

echo "📋 Using the following configuration:"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   App Service Plan: $APP_SERVICE_PLAN"
echo "   Web App Name: $WEB_APP_NAME"
echo "   Location: $LOCATION"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first:"
    echo "   macOS: brew install azure-cli"
    echo "   Or visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Login to Azure
echo "🔐 Logging into Azure..."
az login

# Create Resource Group
echo "📦 Creating resource group..."
az group create --name $RESOURCE_GROUP --location "$LOCATION"

# Create App Service Plan
echo "🏗️  Creating App Service Plan..."
az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --sku B1 \
  --is-linux

# Create Web App
echo "🌐 Creating Web App..."
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --name $WEB_APP_NAME \
  --runtime "PYTHON|3.11"

# Configure App Settings
echo "⚙️  Configuring app settings..."
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $WEB_APP_NAME \
  --settings \
    PYTHON_VERSION=3.11 \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true \
    ENABLE_ORYX_BUILD=true \
    WEBSITE_RUN_FROM_PACKAGE=0

# Set startup command
echo "🎯 Setting startup command..."
az webapp config set \
  --resource-group $RESOURCE_GROUP \
  --name $WEB_APP_NAME \
  --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 app:app"

# Enable System-Assigned Managed Identity
echo "🔑 Enabling managed identity..."
az webapp identity assign \
  --resource-group $RESOURCE_GROUP \
  --name $WEB_APP_NAME

# Deploy from GitHub
echo "📤 Setting up GitHub deployment..."
az webapp deployment source config \
  --resource-group $RESOURCE_GROUP \
  --name $WEB_APP_NAME \
  --repo-url $GITHUB_REPO \
  --branch main \
  --manual-integration

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🌍 Your application will be available at:"
echo "   https://$WEB_APP_NAME.azurewebsites.net"
echo ""
echo "📝 Next steps:"
echo "1. Set Azure OpenAI configuration in the Azure Portal:"
echo "   - Go to your web app in Azure Portal"
echo "   - Navigate to Configuration > Application settings"
echo "   - Add these settings:"
echo "     * AZURE_OPENAI_ENDPOINT: https://your-openai-instance.openai.azure.com/"
echo "     * AZURE_OPENAI_DEPLOYMENT: your-gpt-4-deployment-name"
echo "     * AZURE_OPENAI_API_VERSION: 2024-02-15-preview"
echo ""
echo "2. Assign Log Analytics Reader role to the web app's managed identity"
echo ""
echo "3. Push any changes to your main branch to trigger automatic redeployment"
echo ""
echo "📊 Monitor your deployment:"
echo "   az webapp log tail --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME"
echo ""
echo "🎉 Happy querying!"