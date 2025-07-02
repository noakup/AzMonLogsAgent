#!/usr/bin/env python3
"""
Debug the translation error
"""

def test_enhanced_translation():
    """Test the enhanced translation directly"""
    try:
        from enhanced_translation import translate_nl_to_kql_enhanced
        
        question = "Show me failed requests from the last hour"
        print(f"Testing question: '{question}'")
        print("-" * 50)
        
        result = translate_nl_to_kql_enhanced(question)
        print(f"Result: {result}")
        
        if result.startswith("// Error"):
            print("❌ Translation failed")
            print("This is likely an Azure OpenAI API issue")
            return False
        else:
            print("✅ Translation successful")
            return True
            
    except Exception as e:
        print(f"❌ Exception during translation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_nl_agent_import():
    """Test what the nl_agent is actually importing"""
    try:
        import sys
        sys.path.insert(0, '.')
        
        # Check what the nl_agent is importing
        from nl_agent import translate_nl_to_kql
        print("✅ nl_agent import successful")
        
        question = "Show me failed requests from the last hour"
        result = translate_nl_to_kql(question)
        print(f"nl_agent result: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ nl_agent import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 Debugging Translation Error")
    print("=" * 60)
    
    print("\n1️⃣ Testing enhanced translation directly:")
    test_enhanced_translation()
    
    print("\n2️⃣ Testing what nl_agent imports:")
    test_nl_agent_import()
