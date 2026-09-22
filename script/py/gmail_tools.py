# gmail_tool.py
import os

from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)


def _get_gmail_credentials():
    token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
    credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
    scopes = ["https://www.googleapis.com/auth/gmail.modify"]
    return get_gmail_credentials(
        token_file=token_path,
        scopes=scopes,
        client_secrets_file=credentials_path,
    )


def search_emails(query: str, max_results: int = 5):
    credentials = _get_gmail_credentials()
    api_resource = build_resource_service(credentials=credentials)
    toolkit = GmailToolkit(api_resource=api_resource)
    
    tools = toolkit.get_tools()
    search_tool = next(t for t in tools if t.name == "gmail_search")
    
    return search_tool.invoke({"query": query, "max_results": max_results})


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python gmail_tools.py <search_query>")
        sys.exit(1)
    print(search_emails(sys.argv[1]))