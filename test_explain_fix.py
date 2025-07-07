#!/usr/bin/env python3
"""
Test script to verify the explain endpoint fix
"""
import requests
import json

def test_explain_endpoint():
    """Test the /api/explain endpoint with sample data"""
    
    # Sample query result (simplified version of what the user reported)
    sample_result = {
        'type': 'query_success',
        'data': {
            'type': 'table_data',
            'tables': [{
                'columns': ['TenantId', 'TimeGenerated', 'Message', 'SeverityLevel'],
                'has_data': True,
                'row_count': 3517,
                'rows': [
                    ['81a662b5-8541-481b-977d-5d956616ac5e', '2025-07-07 06:57:59.622471+00:00', 'New Request Received', 0],
                    ['81a662b5-8541-481b-977d-5d956616ac5e', '2025-07-07 06:58:01.123456+00:00', 'Processing Request', 1],
                    ['81a662b5-8541-481b-977d-5d956616ac5e', '2025-07-07 06:58:02.987654+00:00', 'Request Complete', 0]
                ]
            }]
        }
    }
    
    url = "http://localhost:8080/api/explain"
    payload = {
        'query_result': sample_result,
        'original_question': 'Show me recent trace logs'
    }
    
    print("🧪 Testing /api/explain endpoint fix...")
    print(f"📡 POST {url}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Success! Explanation endpoint is working correctly.")
                print(f"📝 Explanation preview: {result.get('explanation', '')[:200]}...")
            else:
                print(f"❌ API returned error: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    test_explain_endpoint()
