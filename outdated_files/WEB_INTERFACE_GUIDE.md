# 🌐 Natural Language KQL Web Interface

A beautiful, modern web interface for querying Azure Log Analytics using natural language. This interface provides an intuitive way to interact with your Azure Monitor data without needing to know KQL syntax.

## 🚀 Getting Started

### Quick Start
1. **Launch the web interface:**
   ```powershell
   python launch_web.py
   ```

2. **Open your browser:**
   Navigate to: http://localhost:5000

3. **Setup your workspace:**
   - Enter your Log Analytics Workspace ID
   - Click "Connect" to initialize the agent
   - Test the connection to verify everything works

4. **Start asking questions:**
   - Type your question in natural language
   - Click "Ask Question" or press Enter
   - View the results in real-time

## 🎨 Features

### Modern UI Design
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Beautiful Gradients**: Modern color scheme with smooth transitions
- **Interactive Elements**: Hover effects and smooth animations
- **Clean Layout**: Organized sections for easy navigation

### Smart Query Interface
- **Natural Language Input**: Ask questions in plain English
- **Quick Suggestions**: Pre-built question pills for common queries
- **Example Categories**: Browse examples by scenario (requests, exceptions, etc.)
- **Real-time Results**: Live query execution with formatted output

### Intelligent Features
- **Smart Timespan Detection**: Automatically handles queries with time filters
- **Connection Testing**: Verify workspace connectivity
- **Error Handling**: Clear error messages and troubleshooting
- **Status Indicators**: Visual feedback for connection state

## 💬 Example Questions

### Performance Monitoring
- "Show me failed requests from the last hour"
- "What are the top 5 slowest API calls?"
- "Show me requests with response time over 5 seconds"

### Error Analysis
- "Show me recent exceptions"
- "What are the most common error messages?"
- "Show me dependency failures"

### Usage Analytics
- "Get heartbeat data from the last 30 minutes"
- "Show me the most accessed pages"
- "What is the error rate in the last 24 hours?"

### Time-based Queries
- "Show me requests from yesterday"
- "Get exceptions from the last 2 hours"
- "Show me data between 9 AM and 5 PM today"

## 📚 Quick Suggestion Pills

The interface includes ready-to-use suggestion pills:
- **Failed Requests**: Find requests that returned errors
- **Slowest APIs**: Identify performance bottlenecks
- **Recent Exceptions**: View latest application errors
- **Heartbeat Data**: Check system health status
- **Dependency Failures**: Monitor external service issues
- **Error Rate**: Calculate error percentages

## 🔧 Technical Details

### Architecture
- **Frontend**: Pure HTML/CSS/JavaScript (no frameworks)
- **Backend**: Flask web server
- **Agent**: Natural Language KQL Agent
- **Translation**: Azure OpenAI powered NL-to-KQL conversion

### API Endpoints
- `POST /api/setup` - Initialize workspace
- `POST /api/query` - Process natural language questions
- `POST /api/test-connection` - Test workspace connectivity
- `GET /api/examples/{scenario}` - Get example queries
- `GET /api/status` - Check agent status

### Smart Features
- **Timespan Detection**: Automatically detects if queries have time filters
- **Error Recovery**: Graceful handling of translation and execution errors
- **Result Formatting**: Clean, readable output formatting
- **Session Management**: Maintains workspace state across requests

## 🛠️ Customization

### Styling
The CSS can be customized in `templates/index.html`:
- **Colors**: Modify the gradient variables
- **Layout**: Adjust spacing and sizing
- **Animations**: Customize transitions and effects

### Suggestions
Add custom suggestion pills by editing the JavaScript:
```javascript
<div class="suggestion-pill" onclick="setQuestion('Your custom question')">Custom Query</div>
```

### Examples
Add new example categories by:
1. Creating new `.md` files with KQL examples
2. Adding the category to the web interface
3. Updating the backend to handle the new category

## 🔍 Troubleshooting

### Common Issues

**Web interface won't start:**
- Check if Flask is installed: `pip install flask`
- Verify port 5000 is available
- Run `python launch_web.py` for detailed error messages

**Can't connect to workspace:**
- Verify your Workspace ID is correct
- Check Azure CLI authentication: `az login`
- Test connection using the "Test Connection" button

**Translation not working:**
- Verify `.env` file has Azure OpenAI configuration
- Check API key and endpoint are correct
- Test with `python setup_azure_openai.py`

**No results returned:**
- Check if your workspace has data
- Try simpler queries first
- Use the example queries to verify functionality

### Debug Mode
Run with debug enabled:
```powershell
python -c "
from web_app import app
app.run(debug=True, host='0.0.0.0', port=5000)
"
```

## 📱 Mobile Support

The web interface is fully responsive and works well on mobile devices:
- **Touch-friendly**: Large buttons and touch targets
- **Responsive Layout**: Adapts to screen size
- **Mobile Keyboard**: Optimized input experience
- **Swipe Gestures**: Natural mobile interactions

## 🎯 Best Practices

### Query Optimization
- Be specific in your questions for better results
- Use time ranges to limit data scope
- Start with examples and modify as needed

### Performance
- Use connection testing before running complex queries
- Be patient with large result sets
- Consider using time filters for better performance

### Security
- Never commit your `.env` file with API keys
- Use Azure RBAC for workspace access control
- Keep your Azure OpenAI keys secure

## 🚀 Advanced Usage

### Integration with Other Tools
The web interface can be extended to integrate with:
- **Dashboards**: Embed queries in monitoring dashboards
- **Alerts**: Use queries as basis for alert rules
- **Reports**: Generate automated reports from queries
- **APIs**: Use the backend API for programmatic access

### Custom Scenarios
Create custom example files for your specific use cases:
1. Create `my_custom_examples.md`
2. Add KQL examples with descriptions
3. Update the web interface to include your category
4. Share with your team for consistent querying

## 📈 Future Enhancements

Planned features for future versions:
- **Query History**: Save and reuse previous queries
- **Favorites**: Bookmark frequently used queries
- **Export Options**: Download results as CSV/JSON
- **Collaboration**: Share queries with team members
- **Advanced Filtering**: UI-based result filtering
- **Visualization**: Charts and graphs for numeric data

---

**🎉 Enjoy exploring your Azure Monitor data with natural language!**
