from typing import List, Dict, Any

# Mock database records
DOCUMENTS = [
    {
        "id": "doc_01",
        "title": "Q3 Executive Financial Report",
        "content": "Operating profit rose by 14% this quarter.",
        "allowed_roles": ["finance_executive", "c_suite"]
    },
    {
        "id": "doc_02",
        "title": "Engineering Microservice Architecture",
        "content": "All internal services communicate via RabbitMQ.",
        "allowed_roles": ["engineer", "architect"]
    },
    {
        "id": "doc_03",
        "title": "General Employee Handbook",
        "content": "Paid time off policies and company standards.",
        "allowed_roles": ["employee", "engineer", "finance_executive"]
    }
]

def filter_authorized_documents(documents: List[Dict[str, Any]], user_roles: List[str]) -> List[Dict[str, Any]]:
    """
    Simulate PostgreSQL JSONB intersection: WHERE allowed_roles ?| ARRAY[user_roles]
    Return only documents where at least one role in `user_roles` exists in `doc['allowed_roles']`.
    """
    authorized_docs = []
    
    # --- WRITE YOUR IMPLEMENTATION HERE ---
    for doc in documents:
        if any(role in doc["allowed_roles"] for role in user_roles):
            authorized_docs.append(doc)
    # --------------------------------------
    
    return authorized_docs

# Test Case:
user_claims = ["engineer"]
filtered = filter_authorized_documents(DOCUMENTS, user_claims)
print([doc["title"] for doc in filtered])
# Expected output: ['Engineering Microservice Architecture', 'General Employee Handbook']