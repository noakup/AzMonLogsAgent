#!/usr/bin/env python3
print("=== Testing Enhanced Translation ===")

try:
    from enhanced_translation import translate_nl_to_kql_enhanced
    print("✅ Import successful")
    
    # Test with a simple question
    question = "Show me failed requests from the last hour"
    print(f"Testing: {question}")
    
    result = translate_nl_to_kql_enhanced(question)
    print(f"Result: {result}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
