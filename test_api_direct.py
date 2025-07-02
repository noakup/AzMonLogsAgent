#!/usr/bin/env python3
"""
Direct test of Azure OpenAI API call to debug the issue
"""

import os
import requests
import json

def test_azure_openai_direct():
    """Test the Azure OpenAI API directly"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_KEY")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo")
    
    print(f"Endpoint: {endpoint}")
    print(f"Deployment: {deployment}")
    print(f"API Key: {'Set' if api_key else 'Not set'}")
    
    if not endpoint or not api_key:
        print("❌ Missing credentials")
        return
      # Use appropriate API version for o1-mini models
    if "o1" in deployment.lower() or "o4" in deployment.lower():
        api_version = "2024-12-01-preview"  # o4-mini requires this version or later
        print("🔧 Using o1-mini compatible API version (2024-12-01-preview)")
    else:
        api_version = "2024-08-01-preview"
        print("🔧 Using standard API version")
    
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    print(f"URL: {url}")
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    # Test with o1-mini compatible format
    if "o1" in deployment.lower() or "o4" in deployment.lower():
        data = {
            "messages": [
                {"role": "user", "content": "Generate a simple KQL query to show the top 5 slowest requests using the AppRequests table with DurationMs column"}
            ],
            "max_completion_tokens": 500
        }
    else:
        data = {
            "messages": [
                {"role": "system", "content": "You are a KQL expert."},
                {"role": "user", "content": "Generate a simple KQL query to show the top 5 slowest requests"}
            ],
            "temperature": 0.1,
            "max_tokens": 500
        }
    
    print(f"Request data: {json.dumps(data, indent=2)}")
    
    try:
        print("\n🔄 Making API call...")
        response = requests.post(url, headers=headers, data=json.dumps(data))
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"✅ Success: {content}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    print("🧪 Direct Azure OpenAI API Test")
    print("=" * 50)
    test_azure_openai_direct()
