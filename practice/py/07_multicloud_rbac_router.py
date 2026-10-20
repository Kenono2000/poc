"""
Pattern 7: Quad-Mode Multi-Cloud Zero-Trust RBAC Router
=======================================================
Core Interview Point:
- Translates the exact same Shift-Left RBAC pre-filtering invariant across 4 clouds
  with zero-downtime runtime switching via `RETRIEVAL_BACKEND`:
  1. PostgreSQL (`pgvector`) : SQL GIN `WHERE d.allowed_roles ?| $2::text[]`
  2. Azure AI Search (`azure`): OData `allowed_roles/any(r: r eq 'role')`
  3. GCP Vertex AI (`gcp`)    : ScaNN Restricts `[{"namespace": "allowed_roles", "allowList": [...]}]`
  4. Databricks (`databricks`): Mosaic Unity Catalog `{"OR": [{"allowed_roles": role}]}`
"""

import json
from typing import Any


def build_rbac_filter(backend: str, user_roles: list[str]) -> Any:
    """Compile verified user roles into the native pre-filter syntax for each cloud."""
    roles = sorted({r.strip().lower() for r in user_roles if r.strip()})
    if not roles:
        return None  # Zero-Trust short-circuit invariant across all 4 clouds

    match backend:
        case "pgvector":
            return {"sql_where": "d.allowed_roles ?| $2::text[]", "bind_param_2": roles}
        case "azure":
            clauses = " or ".join(f"r eq '{r}'" for r in roles)
            return f"allowed_roles/any(r: {clauses})"
        case "gcp":
            # Vertex AI REST API requires 'allowList' (not 'allow') on *.vdb.vertexai.goog
            return [{"namespace": "allowed_roles", "allowList": roles}]
        case "databricks":
            return json.dumps({"OR": [{"allowed_roles": r} for r in roles]})
        case _:
            raise ValueError(f"Unsupported backend: {backend}")


if __name__ == "__main__":
    sample_roles = ["engineering", "finance"]
    for cloud in ("pgvector", "azure", "gcp", "databricks"):
        compiled = build_rbac_filter(cloud, sample_roles)
        print(f"[{cloud.upper():<10}] -> {compiled}")

    print(f"[EMPTY ROLES] -> {build_rbac_filter('azure', [])} (Short-circuited!)")
