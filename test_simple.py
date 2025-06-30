#!/usr/bin/env python3
"""
Simple test for the enhanced translation
"""

def test_basic():
    """Test basic functionality"""
    try:
        from enhanced_translation import translate_nl_to_kql_enhanced
        
        # Test with a simple question
        question = "what are the top 5 slowest API calls?"
        print(f"Testing question: {question}")
        
        result = translate_nl_to_kql_enhanced(question)
        print(f"Result: {result}")
        
        if result.startswith("// Error"):
            print("❌ Translation failed")
            return False
        else:
            print("✅ Translation successful")
            return True
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Enhanced Translation")
    print("=" * 40)
    test_basic()
