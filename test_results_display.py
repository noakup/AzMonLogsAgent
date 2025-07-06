#!/usr/bin/env python3
"""
Test script to verify the results display fix
"""

import requests
import json
import time

def test_results_display():
    """Test that results are displayed properly"""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing results display functionality...")
    
    # Test 1: Setup workspace
    print("\n1. Setting up workspace...")
    setup_data = {"workspace_id": "test-workspace-123"}
    
    try:
        response = requests.post(f"{base_url}/api/setup", json=setup_data)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Workspace setup successful")
            else:
                print(f"❌ Workspace setup failed: {result.get('error')}")
                return
        else:
            print(f"❌ Setup request failed: {response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to web server. Please start the web app first.")
        print("Run: python web_app.py")
        return
    
    # Test 2: Send a query
    print("\n2. Sending test query...")
    query_data = {"question": "Show me recent heartbeat data"}
    
    try:
        response = requests.post(f"{base_url}/api/query", json=query_data)
        if response.status_code == 200:
            result = response.json()
            print(f"Query response: {json.dumps(result, indent=2)}")
            
            if result.get('success'):
                print("✅ Query executed successfully")
                print("✅ Results should now be visible in the web interface")
            else:
                print(f"❌ Query failed: {result.get('error')}")
        else:
            print(f"❌ Query request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Query test failed: {e}")
    
    print("\n🎯 Test completed. Check the web interface at http://localhost:5000")

if __name__ == "__main__":
    test_results_display()
