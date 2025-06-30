#!/usr/bin/env python3
"""
Test the /api/explain endpoint directly
"""

import requests
import json

def test_explain_endpoint():
    """Test the explain endpoint directly"""
    print("🧪 Testing /api/explain Endpoint")
    print("=" * 50)
    
    # Test query result
    test_result = {
        "type": "query_success",
        "kql_query": "AppRequests | where ResultCode >= 400 | take 10",
        "data": {
            "type": "table_data",
            "tables": [
                {
                    "name": "table_0",
                    "columns": ["TimeGenerated", "Name", "ResultCode", "DurationMs"],
                    "rows": [
                        ["2024-06-30T10:15:00Z", "/api/users", 404, 125],
                        ["2024-06-30T10:16:00Z", "/api/orders", 500, 2500],
                        ["2024-06-30T10:17:00Z", "/api/users", 404, 98],
                        ["2024-06-30T10:18:00Z", "/api/reports", 500, 4200],
                        ["2024-06-30T10:19:00Z", "/api/users", 404, 156]
                    ],
                    "row_count": 5
                }
            ]
        },
        "message": "Query executed successfully"
    }
    
    payload = {
        "query_result": test_result,
        "original_question": "Show me failed requests"
    }
    
    url = "http://localhost:5000/api/explain"
    
    try:
        print(f"📡 Making POST request to {url}")
        print(f"📦 Payload size: {len(json.dumps(payload))} bytes")
        
        response = requests.post(
            url, 
            headers={'Content-Type': 'application/json'},
            json=payload,
            timeout=30
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success Response:")
            print(f"   Success: {data.get('success')}")
            print(f"   Explanation: '{data.get('explanation', 'NO EXPLANATION')}'")
            print(f"   Explanation Length: {len(data.get('explanation', ''))}")
            print(f"   Timestamp: {data.get('timestamp')}")
        else:
            print(f"❌ Error Response:")
            print(f"   Text: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Web app not running on localhost:5000")
    except requests.exceptions.Timeout:
        print("❌ Timeout: Request took too long")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_explain_endpoint()
