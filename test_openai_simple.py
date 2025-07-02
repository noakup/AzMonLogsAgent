#!/usr/bin/env python3
"""
Simple test of Azure OpenAI API call
"""

import os
import requests
import json

def test_openai():
    """Test Azure OpenAI API directly"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_KEY")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo")
    
    print(f"🔧 Testing Azure OpenAI Configuration")
    print(f"Endpoint: {endpoint}")
    print(f"Deployment: {deployment}")
    print(f"API Key: {'SET' if api_key else 'NOT SET'}")
    
    if not endpoint or not api_key:
        print("❌ Missing configuration")
        return
    
    # Use appropriate API version for o4-mini models
    if "o1" in deployment.lower() or "o4" in deployment.lower():
        api_version = "2024-12-01-preview"
        print("🔧 Using o4-mini compatible API version")
    else:
        api_version = "2024-09-01-preview"
        print("🔧 Using standard API version")
    
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    print(f"URL: {url}")
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    # Test with o4-mini compatible format
    if "o1" in deployment.lower() or "o4" in deployment.lower():
        data = {
            "messages": [
                {"role": "user", "content": "Explain this data: 5 failed requests with response codes 404 and 500"}
            ],
            "max_completion_tokens": 300
        }
    else:
        data = {
            "messages": [
                {"role": "system", "content": "You are a data analyst."},
                {"role": "user", "content": "Explain this data: 5 failed requests with response codes 404 and 500"}
            ],
            "temperature": 0.3,
            "max_tokens": 300
        }
    
    print(f"Request data: {json.dumps(data, indent=2)}")
    
    try:
        print("\n🔄 Making API call...")
        response = requests.post(url, headers=headers, data=json.dumps(data))
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"✅ Success!")
            print(f"Response: {content}")
            print(f"Length: {len(content)}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_openai()
