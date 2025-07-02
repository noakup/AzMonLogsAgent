#!/usr/bin/env python3
"""
Quick verification of the enhanced examples implementation
"""

def test_example_parsing():
    """Test the example parsing logic directly"""
    
    import os
    
    # Test the file mapping
    file_map = {
        'requests': 'app_requests_kql_examples.md',
        'exceptions': 'app_exceptions_kql_examples.md', 
        'traces': 'app_traces_kql_examples.md',
        'dependencies': 'app_dependencies_kql_examples.md',
        'custom_events': 'app_custom_events_kql_examples.md',
        'performance': 'app_performance_kql_examples.md',
        'usage': 'usage_kql_examples.md'
    }
    
    print("🧪 Testing Example File Parsing")
    print("=" * 40)
    
    for scenario, filename in file_map.items():
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        if os.path.exists(filepath):
            try:
                descriptions = []
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract descriptions using the same logic as in nl_agent.py
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('**') and line.endswith('**') and len(line) > 4:
                        description = line[2:-2].strip()
                        skip_words = ['example', 'analysis', 'queries', 'insights', 'metadata', 'kql']
                        if not any(skip_word in description.lower() for skip_word in skip_words):
                            descriptions.append(description)
                
                # Limit to first 10
                descriptions = descriptions[:10]
                
                print(f"📊 {scenario.title()}: {len(descriptions)} suggestions")
                for i, desc in enumerate(descriptions[:3], 1):  # Show first 3
                    print(f"   {i}. {desc}")
                if len(descriptions) > 3:
                    print(f"   ... and {len(descriptions) - 3} more")
                print()
                
            except Exception as e:
                print(f"❌ Error processing {scenario}: {e}")
        else:
            print(f"⚠️  File not found: {filename}")
    
    print("✅ Test completed!")

if __name__ == "__main__":
    test_example_parsing()
