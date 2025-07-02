#!/bin/bash

# Azure Monitor Logs Agent - Environment Activation Script
# This script activates the Python virtual environment and sets up the PATH

# Add Homebrew to PATH
eval "$(/opt/homebrew/bin/brew shellenv)"

# Add Python 3.12 to PATH
export PATH="/opt/homebrew/opt/python@3.12/libexec/bin:$PATH"

# Activate the virtual environment
source venv/bin/activate

echo "✅ Environment activated successfully!"
echo "📍 Python version: $(python --version)"
echo "📦 Virtual environment: $(which python)"
echo ""
echo "To run the web application, you can use:"
echo "  python web_app.py"
echo ""
echo "To deactivate the environment, type: deactivate"
