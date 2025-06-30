#!/usr/bin/env python3
"""
Complete test of the explain feature including workspace setup
"""

import requests
import json
import time

def test_complete_flow():
    """Test the complete flow from workspace setup to explanation"""
    print("🧪 Testing Complete Explain Flow")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # Step 1: Setup workspace
    print("🔧 Step 1: Setting up workspace...")
    workspace_id = "12345678-1234-1234-1234-123456789012"  # Test workspace ID
    
    setup_response = requests.post(
        f"{base_url}/api/setup",
        json={"workspace_id": workspace_id},
        timeout=10
    )
    
    print(f"Setup Status: {setup_response.status_code}")
    if setup_response.status_code == 200:
        setup_data = setup_response.json()
        print(f"Setup Success: {setup_data.get('success')}")
        print(f"Setup Message: {setup_data.get('message')}")
    else:
        print(f"Setup Error: {setup_response.text}")
        print("⚠️ Continuing with test anyway...")
    
    # Step 2: Test the explain endpoint
    print("\n🧠 Step 2: Testing explain endpoint...")
    
    test_result = {
        "type": "query_success",
        "kql_query": "AppRequests | where ResultCode >= 400 | take 5",
        "data": {
            "type": "table_data",
            "tables": [
                {
                    "name": "table_0",
                    "columns": ["TimeGenerated", "Name", "ResultCode", "DurationMs"],
                    "rows": [
                        ["2024-06-30T10:15:00Z", "/api/users", 404, 125],
                        ["2024-06-30T10:16:00Z", "/api/orders", 500, 2500],
                        ["2024-06-30T10:17:00Z", "/api/users", 404, 98]
                    ],
                    "row_count": 3
                }
            ]
        }
    }
    
    explain_payload = {
        "query_result": test_result,
        "original_question": "Show me failed requests"
    }
    
    try:
        explain_response = requests.post(
            f"{base_url}/api/explain",
            json=explain_payload,
            timeout=30
        )
        
        print(f"Explain Status: {explain_response.status_code}")
        
        if explain_response.status_code == 200:
            explain_data = explain_response.json()
            print(f"Explain Success: {explain_data.get('success')}")
            
            if explain_data.get('success'):
                explanation = explain_data.get('explanation', '')
                print(f"Explanation Length: {len(explanation)}")
                print(f"Explanation: {explanation}")
                
                if explanation and len(explanation) > 20:
                    print("\n🎉 SUCCESS: Explain functionality is working!")
                else:
                    print("\n⚠️ WARNING: Explanation is empty or too short")
            else:
                print(f"Explain Error: {explain_data.get('error')}")
        else:
            print(f"Explain HTTP Error: {explain_response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ Timeout: Request took too long")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_complete_flow()
