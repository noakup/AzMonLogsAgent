#!/usr/bin/env python3
"""
Demonstration of Enhanced Natural Language KQL Agent
Shows all the improvements including retry logic and timespan detection
"""

import asyncio
import sys
import os

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def show_banner():
    """Display feature banner"""
    print("🎉 Enhanced Natural Language KQL Agent")
    print("=" * 60)
    print("🚀 NEW FEATURES DEMONSTRATED:")
    print("   ✅ Smart Retry Logic - Improves translation success rate")
    print("   ✅ Timespan Detection - No more redundant time constraints")
    print("   ✅ Beautiful Web Interface - Modern, responsive UI")
    print("   ✅ Enhanced Translation - Uses actual KQL examples")
    print("   ✅ Multiple Interfaces - Web, CLI, API, MCP Server")
    print("=" * 60)
    print()

def demonstrate_retry_logic():
    """Show retry functionality"""
    print("🔄 RETRY LOGIC DEMONSTRATION")
    print("-" * 40)
    
    try:
        from enhanced_translation import translate_nl_to_kql_enhanced
        
        # Test with various complexity levels
        test_cases = [
            ("show me errors", "Simple query"),
            ("what are the top 5 slowest API calls in the last 2 hours?", "Complex query"),
            ("get me all the failed requests with duration over 1 second", "Very specific query")
        ]
        
        for i, (question, description) in enumerate(test_cases, 1):
            print(f"\n🧪 Test {i}: {description}")
            print(f"   Question: '{question}'")
            
            try:
                # This will use retry logic automatically
                result = translate_nl_to_kql_enhanced(question, max_retries=1)
                
                if result.startswith("// Error"):
                    print(f"   ❌ Failed: {result}")
                else:
                    print(f"   ✅ Success: {result[:60]}...")
                    
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                
    except ImportError as e:
        print(f"⚠️  Could not import translation module: {e}")
        print("   This is expected if dependencies aren't installed")

def demonstrate_timespan_detection():
    """Show timespan detection"""
    print("\n🕐 TIMESPAN DETECTION DEMONSTRATION")
    print("-" * 40)
    
    try:
        from nl_agent import KQLAgent
        
        agent = KQLAgent("demo-workspace")
        
        test_queries = [
            ("AppRequests | top 10 by TimeGenerated desc", "No time filter"),
            ("AppRequests | where TimeGenerated > ago(2h) | count", "Has ago() filter"),
            ("Heartbeat | where TimeGenerated >= datetime(2024-01-01)", "Has datetime() filter"),
            ("AppExceptions | where TimeGenerated between (ago(1d) .. ago(2h))", "Has between filter")
        ]
        
        for query, description in test_queries:
            timespan = agent.detect_query_timespan(query)
            status = "Apply 1-hour timespan" if timespan else "Use query's own timespan"
            print(f"   📝 {description}: {status}")
            
    except ImportError as e:
        print(f"⚠️  Could not import agent module: {e}")

def show_interface_options():
    """Show available interfaces"""
    print("\n🌐 AVAILABLE INTERFACES")
    print("-" * 40)
    
    interfaces = [
        ("🌐 Web Interface", "python launch_web.py", "Beautiful modern UI"),
        ("💻 CLI Agent", "python server_manager.py agent", "Terminal-based interaction"),
        ("🔌 REST API", "python server_manager.py http", "HTTP API server"),
        ("🤖 MCP Server", "python server_manager.py mcp", "AI assistant integration"),
        ("⚙️  Setup Tool", "python setup_azure_openai.py", "Configuration helper"),
        ("🚀 Interface Selector", "python start.py", "Choose your interface")
    ]
    
    for icon_name, command, description in interfaces:
        print(f"   {icon_name}")
        print(f"      Command: {command}")
        print(f"      Purpose: {description}")
        print()

def show_web_features():
    """Display web interface features"""
    print("🎨 WEB INTERFACE FEATURES")
    print("-" * 40)
    
    features = [
        "🎨 Modern Design - Gradient backgrounds, smooth animations",
        "📱 Mobile Responsive - Works on all devices",
        "🔄 Smart Retry Logic - Automatic translation retries",
        "💡 Quick Suggestions - Pre-built question pills",
        "📚 Example Categories - Browse KQL examples by scenario",
        "🔗 Workspace Setup - Easy connection and testing",
        "⚡ Real-time Results - Live query execution",
        "🧪 Connection Testing - Verify workspace connectivity",
        "🕐 Smart Timespan - Intelligent time filter detection"
    ]
    
    for feature in features:
        print(f"   {feature}")

def show_usage_examples():
    """Show example questions"""
    print("\n💬 EXAMPLE QUESTIONS TO TRY")
    print("-" * 40)
    
    examples = [
        "Show me failed requests from the last hour",
        "What are the top 5 slowest API calls?",
        "Get exceptions from today",
        "Show me dependency failures",
        "What is the error rate in the last 24 hours?",
        "Show me requests with response time over 5 seconds",
        "Get heartbeat data from the last 30 minutes",
        "Show me the most accessed pages today"
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"   {i}. \"{example}\"")

def main():
    """Main demonstration"""
    show_banner()
    
    print("🧪 RUNNING DEMONSTRATIONS...")
    print()
    
    # Demonstrate retry logic
    demonstrate_retry_logic()
    
    # Demonstrate timespan detection
    demonstrate_timespan_detection()
    
    # Show interface options
    show_interface_options()
    
    # Show web features
    show_web_features()
    
    # Show usage examples
    show_usage_examples()
    
    print("\n" + "=" * 60)
    print("🎯 QUICK START RECOMMENDATIONS")
    print("=" * 60)
    print("1. 🌐 Try the web interface first: python launch_web.py")
    print("2. 🔧 Setup Azure OpenAI if needed: python setup_azure_openai.py")
    print("3. 🧪 Test with simple questions first")
    print("4. 📚 Browse examples for complex query patterns")
    print("5. 💻 Use CLI for automation and scripting")
    print()
    print("🚀 The system is now enhanced with retry logic and improved reliability!")
    print("📍 Web interface available at: http://localhost:5000")
    print()

if __name__ == "__main__":
    main()
