# 🌐 Web App Setup Guide

## Quick Start

### 1. **Start the Web Application**
```bash
# Navigate to project directory
cd /Users/orensalzberg/Documents/GitHub/AzMonLogsAgent

# Option A: Use the activation script (Recommended)
source activate_env.sh
python web_app.py

# Option B: Manual activation
source venv/bin/activate
python web_app.py
```

### 2. **Access the Web Interface**
- Open your browser and go to: **http://localhost:8080**
- The web app will be running on all network interfaces (0.0.0.0:8080)

## 🔧 Configuration Requirements

### **Azure Authentication Setup**

1. **Create environment file:**
   ```bash
   cp .env.template .env
   ```

2. **Configure your Azure credentials in `.env`:**
   ```bash
   # Azure OpenAI Configuration
   AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
   AZURE_OPENAI_KEY="your-api-key-here"
   AZURE_OPENAI_DEPLOYMENT="gpt-35-turbo"
   
   # Optional: Default workspace ID
   LOG_ANALYTICS_WORKSPACE_ID="your-workspace-guid-here"
   ```

### **Azure Log Analytics Access**

You'll need one of these authentication methods:

#### **Option A: Azure CLI (Recommended for development)**
```bash
# Install Azure CLI if not already installed
brew install azure-cli

# Login to Azure
az login

# Set subscription (if needed)
az account set --subscription "your-subscription-id"
```

#### **Option B: Service Principal**
Add to your `.env` file:
```bash
AZURE_CLIENT_ID="your-client-id"
AZURE_CLIENT_SECRET="your-client-secret"
AZURE_TENANT_ID="your-tenant-id"
```

#### **Option C: Managed Identity**
(When running on Azure resources like VM, App Service, etc.)

## 🎯 How to Use the Web App

### **Step 1: Setup Workspace**
1. Open http://localhost:8080
2. Enter your **Log Analytics Workspace ID** in the setup section
3. Click "Initialize Agent"

### **Step 2: Ask Natural Language Questions**
Examples you can try:
- "Show me failed requests in the last hour"
- "What are the top 5 errors from yesterday?"
- "Find slow requests over 5 seconds"
- "Show me all traces with exceptions"

### **Step 3: View Results**
- The web interface will show:
  - Generated KQL query
  - Query results in a formatted table
  - Explanations of the data

## 🚀 Production Deployment

### **For Production Use:**

1. **Update Flask configuration:**
   ```python
   # In web_app.py, change:
   app.run(debug=False, host='0.0.0.0', port=5000)
   ```

2. **Use a production WSGI server:**
   ```bash
   # Install gunicorn
   pip install gunicorn
   
   # Run with gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 web_app:app
   ```

3. **Set up reverse proxy** (nginx, Apache, etc.)

4. **Configure HTTPS** for security

## 🛠️ VS Code Integration

You can also run the web app directly from VS Code:

1. **Press:** `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. **Type:** "Tasks: Run Task"
3. **Select:** "Start Web App" or "Start Web App (with environment)"

## 📱 Features

Your web app includes:
- ✅ Natural language to KQL translation
- ✅ Interactive query interface
- ✅ Real-time results display
- ✅ Query explanation feature
- ✅ Modern, responsive UI
- ✅ Error handling and validation
- ✅ Multiple workspace support

## 🔍 Troubleshooting

### **Common Issues:**

1. **"Module not found" errors:**
   - Make sure virtual environment is activated
   - Run: `source venv/bin/activate`

2. **Azure authentication errors:**
   - Check your `.env` file configuration
   - Verify Azure CLI login: `az account show`

3. **Web app won't start:**
   - Check if port 8080 is available
   - Try a different port: `python -c "from web_app import app; app.run(debug=True, host='0.0.0.0', port=9000)"`

4. **Query failures:**
   - Verify workspace ID is correct
   - Check Azure permissions for Log Analytics

## 🆘 Getting Help

If you encounter issues:
1. Check the terminal output for error messages
2. Verify your Azure credentials and permissions
3. Ensure the workspace ID is correct
4. Check that all required packages are installed

---

**Ready to start?** Run `source activate_env.sh && python web_app.py` and visit http://localhost:5000!
