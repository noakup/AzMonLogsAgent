"""
Tool: NL to KQL for AppExceptions (exceptions)
Translates natural language questions specifically about exceptions (AppExceptions table) into KQL queries.
Add scenario-specific instructions and example queries below.
"""

def nl_to_kql_exceptions(nl_question):
    """
    Translate a natural language question about exceptions to KQL.
    Exception information is in the AppExceptions table.
    It is CRITICAL that you refer to the "app_exceptions_metadata.md" file to learn about the AppExceptions table 
    and columns, including column names, types and descriptions, which are different than the classis exceptions 
    table in Application Insights.
    It is also CRITICAL that you refer to "app_exceptions_kql_examples.md" for example queries.
    """
    # TODO: Add prompt engineering and example logic
    raise NotImplementedError("This tool is a skeleton. Add instructions and examples for exceptions queries.")

# Example usage:
# kql = nl_to_kql_exceptions("Show me the top 5 exception types in the last week")

