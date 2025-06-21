"""
Tool: NL to KQL for AppTraces (traces and logs)
Translates natural language questions specifically about traces/logs (AppTraces table) into KQL queries.
Add scenario-specific instructions and example queries below.
"""

def nl_to_kql_traces(nl_question):
    """
    Translate a natural language question about traces to KQL.
    Traces information is in the AppTraces table.
    It is CRITICAL that you refer to the "app_traces_metadata.md" file to learn about the AppTraces table 
    and columns, including column names, types and descriptions, which are different than the classis traces 
    table in Application Insights.
    It is also CRITICAL that you refer to "app_traces_kql_examples.md" for example queries.
    """
    # TODO: Add prompt engineering and example logic
    raise NotImplementedError("This tool is a skeleton. Add instructions and examples for traces/logs queries.")

# Example usage:
# kql = nl_to_kql_traces("Show me all traces with severity level 3 in the last 24 hours")

