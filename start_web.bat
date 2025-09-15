@echo off
echo 🌐 Starting Natural Language KQL Web Interface
echo ===============================================
echo.
echo Features:
echo   - Beautiful web UI for natural language queries
echo   - Interactive workspace setup
echo   - Quick suggestion pills
echo   - Real-time query results
echo   - Example queries for different scenarios
echo.
echo 📍 Web interface will be available at: http://localhost:8080
echo 🤖 Ready to process natural language KQL questions!
echo.
echo Press Ctrl+C to stop the server
echo.

REM Install Flask if not available
python -c "import flask" 2>nul || pip install flask

REM Start the web application
python web_app.py

echo.
echo 🛑 Web Interface stopped
pause
