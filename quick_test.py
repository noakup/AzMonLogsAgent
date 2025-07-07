#!/usr/bin/env python3
"""
Test the examples loading fix
"""
import requests
import time

def test_quick():
    print("🧪 Quick test of examples loading...")
    
    # Test one scenario
    response = requests.get('http://localhost:8080/api/examples/requests')
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ API working - examples should load now")
            print(f"Found {len(data.get('result', {}).get('suggestions', []))} suggestions")
        else:
            print(f"❌ API error: {data.get('error')}")
    else:
        print(f"❌ HTTP error: {response.status_code}")
    
    print("\n💡 Now test in browser:")
    print("1. Go to http://localhost:8080")
    print("2. Click 'More Suggestions'")
    print("3. All sections should auto-expand with examples")

if __name__ == '__main__':
    test_quick()
