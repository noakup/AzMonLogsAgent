#!/usr/bin/env python3
"""
Direct test of Azure OpenAI with the fixed configuration
"""

import os
import requests
import json

def test_fixed_openai():
    """Test Azure OpenAI with the fixed configuration"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_KEY")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo")
    
    print(f"🔧 Testing Fixed Azure OpenAI Configuration")
    print(f"Endpoint: {endpoint}")
    print(f"Deployment: {deployment}")
    print(f"API Key: {'SET' if api_key else 'NOT SET'}")
    
    if not endpoint or not api_key:
        print("❌ Missing configuration")
        return
    
    # Use the same fixed configuration as the explain feature
    api_version = "2024-09-01-preview"
    print(f"API Version: {api_version}")
    
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    print(f"URL: {url}")
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    # Use the same simplified format as the fixed explain feature
    data = {
        "messages": [
            {"role": "system", "content": "You are a data analyst expert. Provide clear, concise explanations."},
            {"role": "user", "content": "Analyze this data: 3 failed requests with response codes 404 and 500. Provide a 2-sentence explanation."}
        ],
        "temperature": 0.3,
        "max_tokens": 300
    }
    
    print(f"Request data: {json.dumps(data, indent=2)}")
    
    try:
        print("\n🔄 Making API call...")
        response = requests.post(url, headers=headers, data=json.dumps(data))
        print(f"Status code: {response.status_code}")
        print(f"Raw response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response JSON: {json.dumps(result, indent=2)}")
            
            if 'choices' in result and result['choices']:
                content = result["choices"][0]["message"]["content"]
                print(f"✅ Success!")
                print(f"Response: {content}")
                print(f"Length: {len(content)}")
            else:
                print(f"❌ No choices in response")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_fixed_openai()
