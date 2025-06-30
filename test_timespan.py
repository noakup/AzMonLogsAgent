#!/usr/bin/env python3
"""
Test script for timespan detection functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nl_agent import KQLAgent

def test_timespan_detection():
    """Test the timespan detection function with various KQL queries"""
    
    agent = KQLAgent('test-workspace')
    
    test_cases = [
        # Query without time filters - should return 1
        ("AppRequests | top 10 by TimeGenerated desc", 1),
        
        # Query with ago() filter - should return None
        ("AppRequests | where TimeGenerated > ago(2h) | count", None),
        
        # Query with datetime filter - should return None
        ("Heartbeat | where TimeGenerated >= datetime(2024-01-01) | count", None),
        
        # Query with startofday filter - should return None
        ("AppRequests | where TimeGenerated > startofday(now()) | count", None),
        
        # Query with between filter - should return None
        ("AppRequests | where TimeGenerated between (ago(1d) .. ago(2h)) | count", None),
        
        # Simple count query - should return 1
        ("AppRequests | count", 1),
        
        # Empty query - should return 1
        ("", 1),
    ]
    
    print("🧪 Testing timespan detection function")
    print("=" * 60)
    
    for query, expected in test_cases:
        result = agent.detect_query_timespan(query)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        print(f"{status}")
        print(f"Query: {query or '(empty)'}")
        print(f"Expected: {expected}, Got: {result}")
        print("-" * 40)

if __name__ == "__main__":
    test_timespan_detection()
