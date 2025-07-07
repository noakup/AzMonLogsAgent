#!/usr/bin/env python3
"""
Test script to verify the explain endpoint fix with workspace setup
"""
import requests
import json

def setup_workspace(workspace_id):
    """Setup workspace first"""
    url = "http://localhost:8080/api/setup"
    payload = {'workspace_id': workspace_id}
    
    print(f"🔧 Setting up workspace: {workspace_id}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Workspace setup successful")
                return True
            else:
                print(f"❌ Workspace setup failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error during setup: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Setup error: {str(e)}")
        return False

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
                'row_count': 3,
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
                explanation = result.get('explanation', '')
                print(f"📝 Explanation (first 300 chars): {explanation[:300]}...")
                if len(explanation) > 300:
                    print("   ... (truncated)")
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
    # Setup workspace first
    workspace_id = "81a662b5-8541-481b-977d-5d956616ac5e"
    if setup_workspace(workspace_id):
        test_explain_endpoint()
    else:
        print("❌ Cannot test explain endpoint without workspace setup")
