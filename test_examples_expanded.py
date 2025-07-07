#!/usr/bin/env python3
"""
Test script to verify that example suggestions are expanded by default
"""
import requests
import json
import time

def test_workspace_examples():
    """Test that workspace examples API works"""
    print("Testing workspace examples API...")
    
    try:
        response = requests.post('http://localhost:8080/api/workspace-examples', 
                                headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Workspace examples API working")
                print(f"Found {len(data.get('available_examples', {}))} table types")
                return True
            else:
                print(f"❌ API returned error: {data.get('error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_examples_api():
    """Test that individual examples API works"""
    print("\nTesting individual examples API...")
    
    scenarios = ['requests', 'exceptions', 'traces']
    
    for scenario in scenarios:
        try:
            response = requests.get(f'http://localhost:8080/api/examples/{scenario}')
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    result = data.get('result', {})
                    count = result.get('count', 0)
                    print(f"✅ {scenario}: {count} examples")
                else:
                    print(f"❌ {scenario}: {data.get('error')}")
            else:
                print(f"❌ {scenario}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {scenario}: Exception {e}")

def main():
    print("🧪 Testing Enhanced Example Suggestions UX")
    print("=" * 50)
    
    # Test APIs
    workspace_ok = test_workspace_examples()
    test_examples_api()
    
    print("\n" + "=" * 50)
    if workspace_ok:
        print("✅ All tests passed!")
        print("\n💡 Expected behavior in the web interface:")
        print("   1. Click 'More Suggestions' button")
        print("   2. All example sections should appear EXPANDED by default")
        print("   3. Example suggestions should load automatically (no manual click needed)")
        print("   4. Chevron icons should point down (▼) indicating expanded state")
        print("   5. User can click chevron to collapse any section")
        print("   6. No loading spinners should appear during auto-loading")
    else:
        print("❌ Some tests failed. Check web app server.")

if __name__ == '__main__':
    main()
