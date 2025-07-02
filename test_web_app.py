#!/usr/bin/env python3
"""
Simple test to verify the web application can start
"""

import sys
import os

# Test Flask import
try:
    import flask
    print(f"✅ Flask is available - version: {flask.__version__}")
except ImportError:
    print("❌ Flask is not installed")
    print("Installing Flask...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
    import flask
    print(f"✅ Flask installed - version: {flask.__version__}")

# Test our web app import
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    print("🧪 Testing web app import...")
    import web_app
    print("✅ Web app imports successfully")
    
    print("🧪 Testing template directory...")
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    index_file = os.path.join(templates_dir, 'index.html')
    
    if os.path.exists(templates_dir):
        print("✅ Templates directory exists")
    else:
        print("❌ Templates directory missing")
        
    if os.path.exists(index_file):
        print("✅ index.html template exists")
    else:
        print("❌ index.html template missing")
        
    print("🌐 Web app appears ready to run!")
    print("📍 Run 'python web_app.py' to start the server")
    
except Exception as e:
    print(f"❌ Error testing web app: {e}")
    import traceback
    traceback.print_exc()
