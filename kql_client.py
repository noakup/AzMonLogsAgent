"""
Simple client to test the KQL Query Server and display results in table format
"""
import requests
import json
from typing import Dict, Any

def display_table(table_data: Dict[str, Any]):
    """Display a single table in a simple format"""
    columns = table_data.get('columns', [])
    rows = table_data.get('rows', [])
    
    if not columns or not rows:
        print("No data returned")
        return
    
    # Print column names
    print(" | ".join(columns))
    
    # Print separator line
    print("-" * (len(" | ".join(columns))))
    
    # Print rows
    for row in rows:
        row_str = " | ".join(str(cell) if cell is not None else "NULL" for cell in row)
        print(row_str)

def query_server(workspace_id: str, query: str, timespan: str = None):
    """Send a query to the KQL server and display results"""
    url = "http://localhost:8080/query"
    
    payload = {
        "workspace_id": workspace_id,
        "query": query
    }
    
    if timespan:
        payload["timespan"] = timespan
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        # Check for errors
        if result.get('error'):
            print(f"Error: {result['error']}")
            return
          # Display tables
        tables = result.get('tables', [])
        if not tables:
            print("No tables returned")
            return
        
        for i, table in enumerate(tables):
            if i > 0:  # Add spacing between multiple tables
                print()
            display_table(table)
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Make sure the server is running on http://localhost:8080")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    # Example usage
    workspace_id = input("Enter your Log Analytics Workspace ID: ").strip()
    if not workspace_id:
        print("Workspace ID is required")
        exit(1)
    
    print("\nExample queries you can try:")
    print("1. Heartbeat | where TimeGenerated > ago(1h) | take 5")
    print("2. Usage | where TimeGenerated > ago(1d) | summarize sum(Quantity)")
    print("3. AppRequests | where TimeGenerated > ago(1h) | take 10")
    
    query = input("\nEnter your KQL query: ").strip()
    if not query:
        print("Query is required")
        exit(1)
    
    print(f"\nExecuting query: {query}")
    print("=" * 60)
    
    query_server(workspace_id, query)
