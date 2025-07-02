#!/usr/bin/env python3
"""
Demo script showcasing enhanced table display features
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta

def create_demo_data():
    """Create comprehensive demo data showcasing all table features"""
    
    # Demo 1: Application Requests Analysis
    requests_demo = {
        "type": "query_success",
        "kql_query": "AppRequests | where TimeGenerated > ago(1h) | where Success == false | project TimeGenerated, Name, Url, DurationMs, ResultCode | take 10",
        "data": {
            "type": "table_data",
            "tables": [
                {
                    "table_number": 1,
                    "row_count": 8,
                    "columns": ["TimeGenerated", "Name", "Url", "DurationMs", "ResultCode", "Success"],
                    "rows": [
                        ["2024-12-29T14:30:15.123Z", "GET /api/users", "https://myapp.com/api/users", 5420, 500, False],
                        ["2024-12-29T14:29:45.867Z", "POST /api/login", "https://myapp.com/api/login", 8230, 401, False],
                        ["2024-12-29T14:29:30.234Z", "GET /api/data", "https://myapp.com/api/data", 12500, 503, False],
                        ["2024-12-29T14:28:55.456Z", "DELETE /api/resource", "https://myapp.com/api/resource/123", 890, 404, False],
                        ["2024-12-29T14:28:20.789Z", "PUT /api/update", "https://myapp.com/api/update", 15600, 500, False],
                        ["2024-12-29T14:27:45.012Z", "GET /api/search", "https://myapp.com/api/search?q=test", 7890, 408, False],
                        ["2024-12-29T14:27:10.345Z", "POST /api/submit", "https://myapp.com/api/submit", 4560, 422, False],
                        ["2024-12-29T14:26:35.678Z", "GET /api/profile", "https://myapp.com/api/profile/user123", 3240, 403, False]
                    ],
                    "has_data": True
                }
            ],
            "total_tables": 1
        },
        "message": "✅ Query executed successfully"
    }
    
    # Demo 2: Multi-table Performance Summary
    performance_demo = {
        "type": "query_success",
        "kql_query": "union (AppRequests | summarize AvgDuration=avg(DurationMs), Count=count() by bin(TimeGenerated, 1h)), (AppExceptions | summarize Count=count() by bin(TimeGenerated, 1h))",
        "data": {
            "type": "table_data",
            "tables": [
                {
                    "table_number": 1,
                    "row_count": 6,
                    "columns": ["Hour", "Avg Duration (ms)", "Request Count", "Success Rate %"],
                    "rows": [
                        ["2024-12-29T14:00:00Z", 245.7, 1250, 94.2],
                        ["2024-12-29T13:00:00Z", 312.4, 1180, 91.8],
                        ["2024-12-29T12:00:00Z", 189.3, 1420, 96.7],
                        ["2024-12-29T11:00:00Z", 456.8, 980, 87.3],
                        ["2024-12-29T10:00:00Z", 234.1, 1340, 95.1],
                        ["2024-12-29T09:00:00Z", 278.9, 1150, 93.4]
                    ],
                    "has_data": True
                },
                {
                    "table_number": 2,
                    "row_count": 4,
                    "columns": ["Exception Type", "Count", "Percentage", "First Seen", "Last Seen"],
                    "rows": [
                        ["System.NullReferenceException", 45, 36.3, "2024-12-29T09:15:23Z", "2024-12-29T14:28:12Z"],
                        ["System.ArgumentException", 28, 22.6, "2024-12-29T09:45:17Z", "2024-12-29T14:12:45Z"],
                        ["System.TimeoutException", 32, 25.8, "2024-12-29T10:22:33Z", "2024-12-29T14:25:18Z"],
                        ["System.UnauthorizedAccessException", 19, 15.3, "2024-12-29T11:08:41Z", "2024-12-29T13:56:27Z"]
                    ],
                    "has_data": True
                }
            ],
            "total_tables": 2
        },
        "message": "✅ Query executed successfully"
    }
    
    # Demo 3: No data scenario
    no_data_demo = {
        "type": "query_success",
        "kql_query": "AppRequests | where TimeGenerated > now() | take 10",
        "data": {
            "type": "no_data",
            "message": "No data returned - query time range is in the future"
        },
        "message": "✅ Query executed successfully"
    }
    
    # Demo 4: Query error scenario
    error_demo = {
        "type": "query_error",
        "kql_query": "NonExistentTable | where Column == 'value' | take 5",
        "error": "Table 'NonExistentTable' could not be resolved. Available tables: AppRequests, AppExceptions, AppTraces, AppDependencies",
        "message": "❌ Query execution failed"
    }
    
    # Demo 5: Complex data types showcase
    datatypes_demo = {
        "type": "query_success",
        "kql_query": "AppRequests | extend JsonData=parse_json(Properties) | project TimeGenerated, Success, DurationMs, JsonData, CustomDimensions",
        "data": {
            "type": "table_data",
            "tables": [
                {
                    "table_number": 1,
                    "row_count": 5,
                    "columns": ["TimeGenerated", "Success", "DurationMs", "UserAgent", "IP Address", "Custom Data"],
                    "rows": [
                        ["2024-12-29T14:30:15Z", True, 125.6, "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "192.168.1.100", None],
                        ["2024-12-29T14:29:45Z", False, 5420.8, "Chrome/120.0.0.0 Safari/537.36", "10.0.0.25", '{"userId": 12345}'],
                        ["2024-12-29T14:29:30Z", True, 89.2, "PostmanRuntime/7.26.8", "127.0.0.1", None],
                        ["2024-12-29T14:28:55Z", True, 234.7, "Mozilla/5.0 (Macintosh; Intel Mac OS X)", "172.16.0.5", '{"feature": "beta"}'],
                        ["2024-12-29T14:28:20Z", False, 8960.3, "curl/7.68.0", "203.0.113.42", '{"debug": true}']
                    ],
                    "has_data": True
                }
            ],
            "total_tables": 1
        },
        "message": "✅ Query executed successfully"
    }
    
    return {
        "requests_analysis": requests_demo,
        "performance_summary": performance_demo,
        "no_data_example": no_data_demo,
        "error_example": error_demo,
        "datatypes_showcase": datatypes_demo
    }

def generate_demo_html():
    """Generate HTML demo file showcasing table features"""
    
    demo_data = create_demo_data()
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Table Display Demo</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }}
        
        .demo-container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }}
        
        .demo-header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        
        .demo-section {{
            margin-bottom: 40px;
            padding: 20px;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            background: #f8f9fa;
        }}
        
        .demo-title {{
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        
        .json-display {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre;
        }}
    </style>
</head>
<body>
    <div class="demo-container">
        <div class="demo-header">
            <h1>📊 Enhanced Table Display Demo</h1>
            <p>Showcasing the beautiful table rendering capabilities of the Azure Monitor MCP Agent</p>
        </div>
"""
    
    for demo_name, demo_data_item in demo_data.items():
        html_content += f"""
        <div class="demo-section">
            <h2 class="demo-title">{demo_name.replace('_', ' ').title()}</h2>
            <div class="json-display">{json.dumps(demo_data_item, indent=2)}</div>
        </div>
"""
    
    html_content += """
    </div>
    
    <script>
        console.log('📊 Enhanced Table Display Demo loaded successfully!');
        console.log('🔗 Visit http://localhost:5000 to test the live interface');
    </script>
</body>
</html>
"""
    
    return html_content

def main():
    """Main demo function"""
    print("🎨 Enhanced Table Display - Demo Generator")
    print("=" * 60)
    
    # Generate demo data
    demo_data = create_demo_data()
    
    print("📊 Generated demo scenarios:")
    for scenario, data in demo_data.items():
        print(f"   • {scenario.replace('_', ' ').title()}")
        if data['type'] == 'query_success' and 'data' in data:
            if data['data']['type'] == 'table_data':
                tables = data['data']['tables']
                total_rows = sum(table['row_count'] for table in tables)
                print(f"     - {len(tables)} table(s), {total_rows} total rows")
            else:
                print(f"     - {data['data']['type']}")
        elif data['type'] == 'query_error':
            print(f"     - Error scenario: {data['error'][:50]}...")
    
    # Generate HTML demo file
    print(f"\n🎨 Generating HTML demo file...")
    html_content = generate_demo_html()
    
    with open('table_display_demo.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Demo file created: table_display_demo.html")
    
    # Save demo data as JSON
    print(f"\n💾 Saving demo data as JSON...")
    with open('demo_data.json', 'w', encoding='utf-8') as f:
        json.dump(demo_data, f, indent=2)
    
    print(f"✅ Demo data saved: demo_data.json")
    
    print(f"\n🎯 Demo Summary:")
    print(f"   • 5 different scenarios showcasing table features")
    print(f"   • Complex data types (strings, numbers, booleans, nulls)")
    print(f"   • Multi-table results")
    print(f"   • Error handling examples")
    print(f"   • Performance data visualization")
    
    print(f"\n🔗 Test the enhanced table display:")
    print(f"   • Open: http://localhost:5000")
    print(f"   • Try queries like: 'Show me failed requests from the last hour'")
    print(f"   • See beautiful HTML tables instead of plain text!")
    
    print(f"\n🎨 View static demo:")
    print(f"   • Open: table_display_demo.html in your browser")
    print(f"   • See all demo data structures and examples")

if __name__ == "__main__":
    main()
