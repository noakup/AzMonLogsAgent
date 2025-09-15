#!/usr/bin/env python3
"""
Azure OpenAI Configuration Setup Script
Run this to configure your Azure OpenAI credentials for the KQL agent
"""

import os

def configure_azure_openai():
    """Interactive configuration of Azure OpenAI settings"""
    print("🔧 Azure OpenAI Configuration Setup")
    print("=" * 50)
    
    print("\nPlease provide your Azure OpenAI credentials:")
    print("(You can find these in your Azure OpenAI resource in the Azure portal)")
    
    # Get endpoint
    endpoint = input("\n📡 Azure OpenAI Endpoint (e.g., https://your-resource.openai.azure.com/): ").strip()
    if not endpoint:
        print("❌ Endpoint is required!")
        return False
    
    # Get API key
    api_key = input("🔑 Azure OpenAI API Key: ").strip()
    if not api_key:
        print("❌ API Key is required!")
        return False
    
    # Get deployment name
    deployment = input("🚀 Deployment Name (default: gpt-35-turbo): ").strip()
    if not deployment:
        deployment = "gpt-35-turbo"
    
    # Create .env file
    env_content = f"""# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT={endpoint}
AZURE_OPENAI_KEY={api_key}
AZURE_OPENAI_DEPLOYMENT={deployment}
"""
    
    try:
        with open(".env", "w", encoding="utf-8") as f:
            f.write(env_content)
        
        print(f"\n✅ Configuration saved to .env file!")
        print(f"📡 Endpoint: {endpoint}")
        print(f"🚀 Deployment: {deployment}")
        print(f"🔑 API Key: {api_key[:10]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to save configuration: {e}")
        return False

def test_configuration():
    """Test the Azure OpenAI configuration"""
    print("\n🧪 Testing Azure OpenAI connection...")
    
    try:
        # Load the .env file
        from dotenv import load_dotenv
        load_dotenv()
        
        from main import translate_nl_to_kql
        
        # Test with a simple question
        result = translate_nl_to_kql("show me heartbeat data")
        
        if result.startswith("// Error"):
            print(f"❌ Test failed: {result}")
            return False
        else:
            print(f"✅ Test successful! Generated KQL: {result}")
            return True
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    success = configure_azure_openai()
    
    if success:
        print("\n" + "=" * 50)
        if test_configuration():
            print("\n🎉 Azure OpenAI is configured and working!")
            print("\nYou can now use the natural language agent:")
            print("  python logs_agent.py")
            print("  python server_manager.py agent")
        else:
            print("\n⚠️  Configuration saved but test failed.")
            print("Please check your credentials and try again.")
    else:
        print("\n❌ Configuration failed. Please try again.")
