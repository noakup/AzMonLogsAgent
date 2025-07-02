#!/usr/bin/env python3
"""
Simple test to verify the example extraction works
"""
import os

def test_extraction():
    """Test extraction of examples"""
    
    # Test file mapping
    file_map = {
        'requests': 'app_requests_kql_examples.md',
        'exceptions': 'app_exceptions_kql_examples.md', 
        'traces': 'app_traces_kql_examples.md',
        'dependencies': 'app_dependencies_kql_examples.md',
        'custom_events': 'app_custom_events_kql_examples.md',
        'performance': 'app_performance_kql_examples.md',
        'usage': 'usage_kql_examples.md'
    }
    
    scenario = 'requests'
    filename = file_map.get(scenario)
    print(f"Testing extraction for scenario: {scenario}")
    print(f"Looking for file: {filename}")
    
    if not filename:
        print("❌ No filename found")
        return
    
    filepath = os.path.join(os.path.dirname(__file__), filename)
    print(f"Full path: {filepath}")
    
    if not os.path.exists(filepath):
        print("❌ File does not exist")
        return
    
    print("✅ File exists, attempting to read...")
    
    try:
        descriptions = []
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"File content length: {len(content)} characters")
        
        # Split by lines and look for patterns like "**Description**"
        lines = content.split('\n')
        print(f"Total lines: {len(lines)}")
        
        bold_lines = []
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for lines that start with ** and end with ** (markdown bold)
            if line.startswith('**') and line.endswith('**') and len(line) > 4:
                bold_lines.append((i, line))
        
        print(f"Found {len(bold_lines)} bold lines:")
        for line_num, line in bold_lines[:10]:  # Show first 10
            print(f"  Line {line_num}: {line}")
        
        # Filter descriptions
        for line_num, line in bold_lines:
            # Remove the ** markers
            description = line[2:-2].strip()
            # Skip if it looks like a header
            skip_words = ['example', 'analysis', 'queries', 'insights', 'metadata', 'kql']
            if not any(skip_word in description.lower() for skip_word in skip_words):
                descriptions.append(description)
        
        print(f"\n📚 Extracted {len(descriptions)} descriptions:")
        for i, desc in enumerate(descriptions[:10], 1):  # Show first 10
            print(f"  {i}. {desc}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_extraction()
