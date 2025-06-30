#!/usr/bin/env python3
"""
Debug the explain results feature
"""

import json
import asyncio
from nl_agent import KQLAgent

async def test_explain_results():
    """Test the explain results functionality"""
    print("🧪 Testing Explain Results Feature")
    print("=" * 50)
    
    # Create test query result
    test_result = {
        "type": "query_success",
        "kql_query": "AppRequests | where ResultCode >= 400 | take 10",
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
    agent = KQLAgent("test-workspace")
    
    try:
        print("📊 Test query result created with 5 failed requests")
        print(f"Query: {test_result['kql_query']}")
        
        # Test explanation
        print("\n🧠 Calling explain_results...")
        explanation = await agent.explain_results(test_result, "Show me failed requests")
        
        print(f"\n✅ Explanation result:")
        print(f"Type: {type(explanation)}")
        print(f"Length: {len(explanation) if explanation else 'None'}")
        print(f"Content: {explanation}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_explain_results())
