#!/usr/bin/env powershell
# Test script to verify web app functionality

Write-Host "🧪 Testing Web App Results Display..." -ForegroundColor Green

# Start web app in background
Write-Host "`n1. Starting web application..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-Command", "cd 'c:\GitHub\NoaAzMonAgent'; python web_app.py" -WindowStyle Hidden

# Wait for server to start
Write-Host "⏳ Waiting for server to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Test if server is running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000" -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Web server is running" -ForegroundColor Green
        Write-Host "🌐 Open http://localhost:5000 in your browser" -ForegroundColor Cyan
        Write-Host "📝 Try asking a question to test the results display" -ForegroundColor Cyan
    }
} catch {
    Write-Host "❌ Web server is not responding" -ForegroundColor Red
    Write-Host "💡 Try running: python web_app.py" -ForegroundColor Yellow
}

Write-Host "`n✅ Test script completed" -ForegroundColor Green
