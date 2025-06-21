"""
Tool: NL to KQL for AppRequests (requests)
Translates natural language questions specifically about requests (AppRequests table) into KQL queries.
Add scenario-specific instructions and example queries below.
"""

def nl_to_kql_requests(nl_question):
    """
    Translate a natural language question about requests to KQL.
    Requests information is in the AppRequests table.
    It is CRITICAL that you refer to the "app_requests_metadata.md" file to learn about the AppRequests table 
    and columns, including column names, types and descriptions, which are different than the classis requests 
    table in Application Insights.
    It is also CRITICAL that you refer to "app_requests_kql_examples.md" for example queries.
    """
    # TODO: Add prompt engineering and example logic
    raise NotImplementedError("This tool is a skeleton. Add instructions and examples for requests queries.")

# Example usage:
# kql = nl_to_kql_requests("Show me the average request duration in the last 24 hours")

