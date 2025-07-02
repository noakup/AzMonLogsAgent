#!/usr/bin/env python3
"""
Test script to debug the natural language to KQL translation
"""

import os
import sys
from main import translate_nl_to_kql

def test_environment():
    """Test Azure OpenAI environment variables"""
    print("🔍 Checking Azure OpenAI Configuration:")
    
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_KEY") 
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo")
    
    print(f"AZURE_OPENAI_ENDPOINT: {'✅ Set' if endpoint else '❌ Not set'}")
    print(f"AZURE_OPENAI_KEY: {'✅ Set' if api_key else '❌ Not set'}")
    print(f"AZURE_OPENAI_DEPLOYMENT: {deployment}")
    
    if not endpoint or not api_key:
        print("\n❌ Missing required environment variables!")
        print("Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY")
        return False
    
    return True

def test_translation(question):
    """Test translating a question to KQL"""
    print(f"\n🔄 Testing translation for: '{question}'")
    
    try:
        result = translate_nl_to_kql(question)
        print(f"📝 Result: {result}")
        
        if result.startswith("// Error"):
            print("❌ Translation failed")
            return False
        else:
            print("✅ Translation successful")
            return True
            
    except Exception as e:
        print(f"❌ Exception during translation: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Azure OpenAI Translation Test")
    print("=" * 50)
    
    # Test environment
    if not test_environment():
        sys.exit(1)
    
    # Test questions
    test_questions = [
        "what are the top 5 slowest API calls?",
        "show me failed requests from the last hour",
        "get heartbeat data",
        "show me exceptions in the last day"
    ]
    
    success_count = 0
    for question in test_questions:
        if test_translation(question):
            success_count += 1
    
    print(f"\n📊 Results: {success_count}/{len(test_questions)} translations successful")
