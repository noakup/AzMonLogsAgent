#!/usr/bin/env python3
"""
Simple test of the explain functionality
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nl_agent import KQLAgent

async def test_explain_simple():
    """Test the explain functionality with a simple case"""
    print("🧪 Testing Explain Functionality")
    print("=" * 50)
    
    # Create a simple test result
    test_result = {
        "type": "query_success",
        "kql_query": "AppRequests | where ResultCode >= 400 | take 5",
        "data": {
            "type": "table_data",
            "tables": [
                {
                    "name": "table_0",
                    "columns": ["TimeGenerated", "Name", "ResultCode", "DurationMs"],
                    "rows": [
                        ["2024-06-30T10:15:00Z", "/api/users", 404, 125],
                        ["2024-06-30T10:16:00Z", "/api/orders", 500, 2500],
                        ["2024-06-30T10:17:00Z", "/api/users", 404, 98],
                        ["2024-06-30T10:18:00Z", "/api/reports", 500, 4200],
                        ["2024-06-30T10:19:00Z", "/api/users", 404, 156]
                    ],
                    "row_count": 5
                }
            ]
        },
        "message": "Query executed successfully"
    }
    
    # Create agent
    agent = KQLAgent("test-workspace-id")
    
    print("📊 Created test query result with 5 failed requests")
    print("🧠 Calling explain_results...")
    
    try:
        explanation = await agent.explain_results(test_result, "Show me failed requests")
        print(f"\n✅ Explanation received:")
        print(f"Length: {len(explanation) if explanation else 0}")
        print(f"Content: {explanation}")
        
        if explanation and len(explanation) > 50:
            print("\n🎉 SUCCESS: Explanation generated successfully!")
        else:
            print("\n⚠️ WARNING: Explanation is too short or empty")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_explain_simple())
