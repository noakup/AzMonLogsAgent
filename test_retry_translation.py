#!/usr/bin/env python3
"""
Test the retry functionality for natural language translation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_translation import translate_nl_to_kql_enhanced

def test_retry_functionality():
    """Test the retry logic"""
    
    print("🧪 Testing Enhanced Translation with Retry Logic")
    print("=" * 60)
    
    test_cases = [
        {
            "question": "show me failed requests from the last hour",
            "expected_type": "valid_kql"
        },
        {
            "question": "what are the top 5 slowest API calls?",
            "expected_type": "valid_kql"
        },
        {
            "question": "this is a completely nonsensical question that should fail",
            "expected_type": "any"  # May succeed or fail
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['question']}")
        print("-" * 40)
        
        try:
            result = translate_nl_to_kql_enhanced(test_case['question'])
            
            if result.startswith("// Error"):
                print(f"❌ Translation failed: {result}")
            else:
                print(f"✅ Translation succeeded: {result}")
                
        except Exception as e:
            print(f"❌ Exception occurred: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 Retry functionality test complete!")
    
    # Test with specific retry count
    print("\n🔄 Testing with custom retry count...")
    try:
        result = translate_nl_to_kql_enhanced("show me errors", max_retries=1)
        print(f"📝 Result with 1 retry: {result}")
    except Exception as e:
        print(f"❌ Error with custom retry: {e}")

if __name__ == "__main__":
    test_retry_functionality()
