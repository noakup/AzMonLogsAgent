#!/usr/bin/env python3
"""
Web Interface Launcher for Natural Language KQL Agent
"""

import os
import sys
import subprocess

def check_flask():
    """Check if Flask is installed and install if needed"""
    try:
        import flask
        print(f"✅ Flask is available - version: {flask.__version__}")
        return True
    except ImportError:
        print("📦 Installing Flask...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
            import flask
            print(f"✅ Flask installed - version: {flask.__version__}")
            return True
        except Exception as e:
            print(f"❌ Failed to install Flask: {e}")
            return False

def main():
    print("🌐 Natural Language KQL Web Interface Launcher")
    print("=" * 60)
    
    # Check Flask
    if not check_flask():
        input("Press Enter to exit...")
        return
    
    # Check templates
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    index_file = os.path.join(templates_dir, 'index.html')
    
    if not os.path.exists(index_file):
        print("❌ Web template files missing")
        input("Press Enter to exit...")
        return
    
    print("✅ All dependencies ready")
    print()
    print("📍 Web interface will be available at: http://localhost:5000")
    print("🤖 Features:")
    print("   - Beautiful web UI for natural language queries")
    print("   - Interactive workspace setup")
    print("   - Quick suggestion pills")
    print("   - Real-time query results")
    print("   - Example queries for different scenarios")
    print()
    print("🚀 Starting web server...")
    print("   Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        # Import and run web app
        from web_app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n🛑 Web Interface stopped")
    except Exception as e:
        print(f"❌ Error starting web interface: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
