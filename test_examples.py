#!/usr/bin/env python3
"""
Test script for the enhanced examples functionality
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_extract_example_descriptions():
    """Test the extract_example_descriptions method"""
    
    try:
        from nl_agent import NaturalLanguageAgent
        
        # Create a test agent instance
        agent = NaturalLanguageAgent("test-workspace")
        
        # Test extracting descriptions from requests examples
        descriptions = agent.extract_example_descriptions("requests")
        
        print("📚 Testing extract_example_descriptions method:")
        print(f"Found {len(descriptions)} descriptions for 'requests' scenario:")
        
        for i, desc in enumerate(descriptions, 1):
            print(f"  {i}. {desc}")
        
        print()
        
        # Test with other scenarios
        scenarios = ["exceptions", "traces", "dependencies", "performance"]
        
        for scenario in scenarios:
            descs = agent.extract_example_descriptions(scenario)
            print(f"📊 {scenario.title()}: {len(descs)} descriptions found")
        
        print("\n✅ Test completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Starting test...")
    test_extract_example_descriptions()
