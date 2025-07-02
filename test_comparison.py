#!/usr/bin/env python3
"""
Test script to compare old vs new translation methods
"""

import sys
sys.path.append('.')

def test_old_translation():
    """Test the old translation method"""
    print("🔧 Testing OLD translation method...")
    try:
        from main import translate_nl_to_kql as old_translate
        question = "what are the top 5 slowest API calls?"
        
        for i in range(3):
            print(f"\n🔄 Attempt {i+1}:")
            result = old_translate(question)
            print(f"Result: {result}")
            
    except Exception as e:
        print(f"❌ Old method failed: {e}")

def test_new_translation():
    """Test the enhanced translation method"""  
    print("\n🚀 Testing ENHANCED translation method...")
    try:
        from enhanced_translation import translate_nl_to_kql_enhanced as new_translate
        question = "what are the top 5 slowest API calls?"
        
        for i in range(3):
            print(f"\n🔄 Attempt {i+1}:")
            result = new_translate(question)
            print(f"Result: {result}")
            
    except Exception as e:
        print(f"❌ New method failed: {e}")

if __name__ == "__main__":
    print("🧪 NL to KQL Translation Comparison")
    print("=" * 60)
    
    test_old_translation()
    test_new_translation()
    
    print("\n" + "=" * 60)
    print("💡 The enhanced version should be more consistent!")
    print("💡 It uses actual examples from your .md files!")
