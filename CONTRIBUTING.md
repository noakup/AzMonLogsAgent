# 🤝 Contributing to Azure Monitor MCP Agent

Thank you for your interest in contributing to the Azure Monitor MCP Agent! This guide will help you get started.

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Git
- Azure OpenAI Service account (for AI features)
- Azure Log Analytics workspace (for testing)

### 1. Clone the Repository
```bash
git clone https://github.com/noakup/NoaAzMonAgent.git
cd NoaAzMonAgent
```

### 2. Set Up Development Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.template .env

# Edit .env with your Azure credentials (see setup section below)
```

### 3. Configure Azure Services

#### Azure OpenAI Setup
Add these to your `.env` file:
```env
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-35-turbo
```

#### Azure Log Analytics Setup
You'll need a Log Analytics Workspace ID for testing:
```env
# Optional: Add your test workspace ID
LOG_ANALYTICS_WORKSPACE_ID=your-workspace-guid-here
```

### 4. Test Your Setup
```bash
# Start the web application
python web_app.py

# Open browser to http://localhost:8080
# Test with your Log Analytics Workspace ID
```

## 🛠️ Development Workflow

### Creating a Feature
1. **Create a new branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes:**
   ```bash
   # Test specific functionality
   python test_your_feature.py
   
   # Test web interface
   python web_app.py
   ```

4. **Commit and push:**
   ```bash
   git add .
   git commit -m "feat: description of your feature"
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request:**
   - Go to the GitHub repository
   - Click "New Pull Request"
   - Fill out the PR template
   - Request review

## 📁 Project Structure

```
├── web_app.py              # Main web application
├── logs_agent.py             # Natural language processing
├── templates/              # Web UI templates
│   └── index.html          # Main web interface
├── azure_agent/            # Azure integration
│   └── monitor_client.py   # Log Analytics client
├── app_*_kql_examples.md   # KQL example files
├── requirements.txt        # Python dependencies
└── .env.template          # Environment template
```

## 🎯 Areas for Contribution

### High Priority
- **New KQL Example Categories**: Add examples for specific Azure services
- **UI/UX Improvements**: Enhance the web interface design
- **Performance Optimization**: Improve query performance and caching
- **Error Handling**: Better error messages and recovery

### Medium Priority
- **Documentation**: Improve guides and API documentation
- **Testing**: Add more comprehensive tests
- **Features**: New functionality like saved queries, dashboards
- **Integrations**: Support for other AI models or Azure services

### Getting Started Tasks
- **Fix typos or improve documentation**
- **Add new KQL examples**
- **Improve CSS styling**
- **Add validation for user inputs**

## 🧪 Testing

### Manual Testing
1. **Web Interface:**
   ```bash
   python web_app.py
   # Test at http://localhost:8080
   ```

2. **Natural Language Translation:**
   ```bash
   python test_translation.py
   ```

3. **Azure Integration:**
   ```bash
   python test_query.py
   ```

### Automated Testing
```bash
# Run all tests
python -m pytest

# Run specific test
python test_specific_feature.py
```

## 📝 Coding Standards

### Python Style
- Follow PEP 8
- Use meaningful variable names
- Add docstrings to functions
- Keep functions focused and small

### Commit Messages
Use conventional commits:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation
- `style:` for formatting changes
- `refactor:` for code refactoring
- `test:` for adding tests

### Example:
```bash
git commit -m "feat: add support for custom KQL queries in UI"
git commit -m "fix: resolve timeout issue in Azure Log Analytics queries"
git commit -m "docs: update setup instructions for Azure OpenAI"
```

## 🐛 Reporting Issues

1. **Check existing issues** to avoid duplicates
2. **Use the issue template** when creating new issues
3. **Provide detailed information:**
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details
   - Error messages or logs

## 💡 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and general discussion
- **Code Review**: PRs are reviewed promptly

## 🔐 Security

- **Never commit API keys or credentials**
- **Use `.env` file for sensitive data**
- **Review `.gitignore` to ensure secrets aren't tracked**

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

**Thank you for contributing! 🎉**

Your contributions help make the Azure Monitor MCP Agent better for everyone.
