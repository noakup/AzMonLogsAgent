#!/usr/bin/env python3
"""
Enhanced Natural Language to KQL Translation
This version actually uses the example files to provide context to the AI
"""

import os
import requests
import json

def load_examples_and_metadata():
    """Load KQL examples and metadata for better translation context"""
    context_files = {
        "requests_examples": "app_requests_kql_examples.md",
        "requests_metadata": "app_requests_metadata.md", 
        "exceptions_examples": "app_exceptions_kql_examples.md",
        "exceptions_metadata": "app_exceptions_metadata.md",
        "traces_examples": "app_traces_kql_examples.md",
        "traces_metadata": "app_traces_metadata.md",
        "performance_examples": "app_performance_kql_examples.md"
    }
    
    context = {}
    for key, filename in context_files.items():
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
                # Take first 2000 characters to avoid token limits
                context[key] = content[:2000] + "..." if len(content) > 2000 else content
        else:
            context[key] = "File not found"
    
    return context

def translate_nl_to_kql_enhanced(nl_question, max_retries=2):
    """
    Enhanced translation that actually uses example files for context
    Includes retry logic for better reliability
    """
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_KEY")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo")
    
    if not endpoint or not api_key:
        return "// Error: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY must be set"
    
    # Try translation with retries
    for attempt in range(max_retries + 1):
        try:
            result = _attempt_translation(nl_question, endpoint, api_key, deployment, attempt)
            
            # Check if the result is a valid KQL query (not an error)
            if not result.startswith("// Error"):
                if attempt > 0:
                    print(f"✅ Translation succeeded on attempt {attempt + 1}")
                return result
            elif attempt < max_retries:
                print(f"🔄 Translation attempt {attempt + 1} failed, retrying...")
                continue
            else:
                return result  # Return the error after all retries
                
        except Exception as e:
            if attempt < max_retries:
                print(f"🔄 Translation attempt {attempt + 1} failed with exception, retrying...")
                continue
            else:
                return f"// Error translating NL to KQL after {max_retries + 1} attempts: {str(e)}"
    
    return "// Error: All translation attempts failed"

def _attempt_translation(nl_question, endpoint, api_key, deployment, attempt_number):
    """
    Single translation attempt - separated for retry logic
    """
    print(f"🔍 Enhanced translation called with: '{nl_question}' (attempt {attempt_number + 1})")
    
    # Load context from example files
    context = load_examples_and_metadata()
    
    # Build comprehensive system prompt with examples
    system_prompt = f"""You are a KQL (Kusto Query Language) expert. Convert natural language questions to valid KQL queries for Azure Log Analytics.

EXAMPLE KQL QUERIES FOR CONTEXT:

App Requests Examples:
{context.get('requests_examples', 'No examples available')}

App Exceptions Examples:
{context.get('exceptions_examples', 'No examples available')}

App Traces Examples:
{context.get('traces_examples', 'No examples available')}

Performance Examples:
{context.get('performance_examples', 'No examples available')}

IMPORTANT RULES:
1. Return ONLY the KQL query, no explanation or markdown formatting
2. Use proper KQL syntax and functions
3. Handle time ranges appropriately (ago(), datetime(), etc.)
4. Use correct table names (AppRequests, AppExceptions, AppTraces, etc.) and the correct columns (e.g., DurationMs for AppRequests)
5. NEVER use the classic Application Insights query syntax (request, exception, traces, or duration columns)
6. Include proper aggregations and sorting for meaningful results
7. Consider performance by limiting results when appropriate (take, top)"""

    print(f"🔍 Loaded .env file")
    print(f"🔍 Endpoint: {endpoint}")
    print(f"🔍 Deployment: {deployment}")
    print(f"🔍 API Key: {'Set' if api_key else 'Not set'}")
    
    # Determine API version based on model
    if "o1" in deployment.lower() or "o4" in deployment.lower():
        api_version = "2024-12-01-preview"  # Newer API version for o1/o4 models
    else:
        api_version = "2024-09-01-preview"   # Standard API version
    
    print(f"🔄 Making API call to: {endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}")
    print(f"🔄 Using deployment: {deployment}")
    
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }

    user_prompt = f"""
Question: {nl_question}

Based on the examples above, generate a KQL query. Response format: just the KQL query, nothing else.
"""

    # o1-mini models have different parameter requirements
    if "o1" in deployment.lower() or "o4" in deployment.lower():
        data = {
            "messages": [
                {"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}
            ],
            "max_completion_tokens": 500
            # Note: o1 models don't support temperature, system messages, or streaming
        }
    else:
        data = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1 + (attempt_number * 0.05),  # Slightly increase temperature on retries
            "max_tokens": 500
        }    
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response.raise_for_status()
    result = response.json()
    kql = result["choices"][0]["message"]["content"].strip()
    
    # Clean up the response
    if kql.startswith("```kql"):
        kql = kql.replace("```kql", "").replace("```", "").strip()
    
    # Basic validation - check if it looks like a valid KQL query
    if not kql or len(kql.strip()) < 5:
        return "// Error: Empty or invalid response from AI"
    
    # Check for common error indicators
    error_indicators = ["sorry", "cannot", "unable", "error", "apologize"]
    if any(indicator in kql.lower() for indicator in error_indicators):
        return f"// Error: AI returned error response: {kql}"
    
    return kql

if __name__ == "__main__":
    # Test the enhanced translation
    test_questions = [
        "what are the top 5 slowest API calls?",
        "show me failed requests from the last hour", 
        "get exceptions from today",
        "show me request duration over time"
    ]
    
    print("🧪 Testing Enhanced NL to KQL Translation")
    print("=" * 50)
    
    for question in test_questions:
        print(f"\n❓ Question: {question}")
        result = translate_nl_to_kql_enhanced(question)
        print(f"📝 KQL: {result}")
        print("-" * 30)
