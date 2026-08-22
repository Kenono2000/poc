# gmail_tool.py
import os
from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.utils import build_resource_service, get_gmail_credentials

def search_emails(query: str, max_results: int = 5):
    credentials = get_gmail_credentials(
        token_file="C:/Users/YourName/.hermes/secrets/token.json",
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
        client_secrets_file="C:/Users/YourName/.hermes/secrets/credentials.json",
    )
    api_resource = build_resource_service(credentials=credentials)
    toolkit = GmailToolkit(api_resource=api_resource)
    
    # Get the search tool from the toolkit
    tools = toolkit.get_tools()
    search_tool = next(t for t in tools if t.name == "gmail_search")
    
    return search_tool.invoke({"query": query, "max_results": max_results})

if __name__ == "__main__":
    import sys
    print(search_emails(sys.argv[1]))