#!/usr/bin/env python3
"""
Natural Language KQL Agent - Interface Selector
Choose how you want to interact with Azure Log Analytics
"""

import os
import sys
import subprocess

def print_banner():
    print("🤖 Natural Language KQL Agent")
    print("=" * 50)
    print("Query Azure Log Analytics with Natural Language!")
    print("=" * 50)
    print()

def print_options():
    print("Choose your interface:")
    print()
    print("1. 🌐 Web Interface (Recommended)")
    print("   Beautiful, interactive web UI")
    print("   ↳ Best for: Interactive exploration, beginners")
    print()
    print("2. 💻 Command Line Agent")
    print("   Terminal-based interactive agent")
    print("   ↳ Best for: CLI users, scripting")
    print()
    print("3. 🔌 REST API Server")
    print("   HTTP API for programmatic access")
    print("   ↳ Best for: Integration, automation")
    print()
    print("4. 🤖 MCP Server")
    print("   Model Context Protocol for AI assistants")
    print("   ↳ Best for: Claude Desktop, AI workflows")
    print()
    print("5. ⚙️  Setup & Configuration")
    print("   Configure Azure OpenAI and test connections")
    print("   ↳ Best for: First-time setup")
    print()
    print("6. 📚 Browse Examples")
    print("   View KQL examples by category")
    print("   ↳ Best for: Learning KQL patterns")
    print()
    print("0. 🚪 Exit")
    print()

def launch_interface(choice):
    commands = {
        '1': ['python', 'launch_web.py'],
        '2': ['python', 'server_manager.py', 'agent'],
        '3': ['python', 'server_manager.py', 'http'],
        '4': ['python', 'server_manager.py', 'mcp'],
        '5': ['python', 'setup_azure_openai.py'],
        '6': ['python', '-c', '''
import os
print("📚 Available Example Categories:")
print()
examples = [
    ("app_requests_kql_examples.md", "HTTP Requests Analysis"),
    ("app_exceptions_kql_examples.md", "Error & Exception Tracking"),
    ("app_traces_kql_examples.md", "Application Trace Analysis"),
    ("app_dependencies_kql_examples.md", "External Service Monitoring"),
    ("app_performance_kql_examples.md", "Performance Metrics"),
    ("usage_kql_examples.md", "Usage Analytics")
]

for file, desc in examples:
    if os.path.exists(file):
        print(f"✅ {desc}")
        print(f"   File: {file}")
    else:
        print(f"❌ {desc} (missing)")
    print()

print("To view examples, open the .md files in your editor or use the web interface.")
''']
    }
    
    if choice in commands:
        try:
            print(f"🚀 Starting interface...")
            subprocess.run(commands[choice])
        except KeyboardInterrupt:
            print("\n🛑 Interface stopped")
        except Exception as e:
            print(f"❌ Error starting interface: {e}")
            input("Press Enter to continue...")
    elif choice == '0':
        print("👋 Goodbye!")
        return False
    else:
        print("❌ Invalid choice. Please try again.")
        input("Press Enter to continue...")
    
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import flask
        import azure.identity
        import azure.monitor.query
        return True
    except ImportError as e:
        print(f"⚠️  Missing dependencies: {e}")
        print("Installing required packages...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            print("✅ Dependencies installed successfully")
            return True
        except Exception as install_error:
            print(f"❌ Failed to install dependencies: {install_error}")
            print("Please run: pip install -r requirements.txt")
            return False

def main():
    print_banner()
    
    # Check dependencies
    if not check_dependencies():
        input("Press Enter to exit...")
        return
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  No .env file found!")
        print("You'll need to configure Azure OpenAI for natural language features.")
        print("Choose option 5 (Setup & Configuration) to get started.")
        print()
    
    while True:
        print_options()
        choice = input("Enter your choice (0-6): ").strip()
        print()
        
        if not launch_interface(choice):
            break
        
        print()
        print("-" * 50)
        print()

if __name__ == "__main__":
    main()
