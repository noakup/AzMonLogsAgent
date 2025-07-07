#!/usr/bin/env python3
"""
Simple test to check the examples loading behavior
"""
import requests
import json
import time

def test_examples_loading():
    print("🧪 Testing examples loading behavior...")
    
    # Test different scenarios
    scenarios = ['requests', 'exceptions', 'traces', 'dependencies', 'page_views']
    
    for scenario in scenarios:
        print(f"\n📊 Testing {scenario}...")
        try:
            response = requests.get(f'http://localhost:8080/api/examples/{scenario}')
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    suggestions = data.get('result', {}).get('suggestions', [])
                    print(f"✅ {scenario}: {len(suggestions)} suggestions")
                    for i, suggestion in enumerate(suggestions[:2]):  # Show first 2
                        print(f"   {i+1}. {suggestion}")
                else:
                    print(f"❌ {scenario}: Error - {data.get('error')}")
            else:
                print(f"❌ {scenario}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {scenario}: Exception - {e}")

def test_workspace_discovery():
    print("\n🔍 Testing workspace discovery...")
    try:
        response = requests.post('http://localhost:8080/api/workspace-examples', 
                                headers={'Content-Type': 'application/json'})
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                examples = data.get('available_examples', {})
                print(f"✅ Workspace discovery: {len(examples)} table types")
                for table_name in examples.keys():
                    print(f"   - {table_name}")
            else:
                print(f"❌ Workspace discovery: Error - {data.get('error')}")
        else:
            print(f"❌ Workspace discovery: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Workspace discovery: Exception - {e}")

if __name__ == '__main__':
    test_workspace_discovery()
    test_examples_loading()
    print("\n" + "="*50)
    print("💡 Now open http://localhost:8080 and click 'More Suggestions'")
    print("   Check the browser console for debug logs")
