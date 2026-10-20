"""
Pattern 1: Shift-Left In-Database Zero-Trust Vector RBAC
========================================================
Core Interview Point:
- Standard RAG post-filters in Python AFTER top-K retrieval -> causes Recall Starvation
  and loads unauthorized vectors into RAM.
- Shift-Left RBAC filters permissions BEFORE vector distance scoring (GIN + HNSW),
  and short-circuits immediately if `user_roles` is empty.
"""

from dataclasses import dataclass
import math

KNOWN_ROLES = {"admin", "finance", "engineering", "public"}

# Production PostgreSQL query pattern (GIN pre-filter + HNSW cosine distance):
PGVECTOR_RBAC_SQL = """
SELECT d.document_id, c.content, 1 - (c.embedding <=> $1::vector) AS similarity
FROM document_chunks c
JOIN documents d ON c.document_id = d.id
WHERE d.allowed_roles ?| $2::text[]   -- 1. GIN Index RBAC pre-filter ($2 parameterized)
ORDER BY c.embedding <=> $1::vector   -- 2. HNSW Index scan on authorized subset only
LIMIT $3;
"""


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    content: str
    allowed_roles: set[str]
    embedding: list[float]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def sanitize_roles(raw_roles: list[str]) -> set[str]:
    """Defense-in-depth: strip unknown or injected role strings before query binding."""
    return {r.strip().lower() for r in raw_roles if r.strip().lower() in KNOWN_ROLES}


def post_filter_search(query_vec: list[float], chunks: list[Chunk], user_roles: list[str], top_k: int = 1) -> list[Chunk]:
    """❌ ANTI-PATTERN: Ranks globally first, then filters in Python (causes Recall Starvation)."""
    roles = sanitize_roles(user_roles)
    top_global = sorted(chunks, key=lambda c: cosine_similarity(query_vec, c.embedding), reverse=True)[:top_k]
    return [c for c in top_global if c.allowed_roles & roles]


def shift_left_rbac_search(query_vec: list[float], chunks: list[Chunk], user_roles: list[str], top_k: int = 1) -> list[Chunk]:
    """✅ ZERO-TRUST PATTERN: Short-circuits empty roles & pre-filters BEFORE vector ranking."""
    roles = sanitize_roles(user_roles)
    if not roles:
        return []  # Zero-Trust invariant: never touch storage without verified roles

    authorized = (c for c in chunks if c.allowed_roles & roles)
    return sorted(authorized, key=lambda c: cosine_similarity(query_vec, c.embedding), reverse=True)[:top_k]


if __name__ == "__main__":
    db = [
        Chunk("EXEC-COMP-01", "CEO bonus is $5M", {"admin"}, [0.99, 0.01]),
        Chunk("ENG-RUNBOOK-01", "Deploy microservice via Helm", {"engineering"}, [0.85, 0.15]),
    ]
    query = [1.0, 0.0]

    # Engineer searches for top_k=1:
    bad = post_filter_search(query, db, ["engineering"], top_k=1)
    good = shift_left_rbac_search(query, db, ["engineering"], top_k=1)

    print(f"❌ Post-Filter (Recall Starvation): {[c.doc_id for c in bad]}  <-- Dropped top-1 admin doc, returned 0!")
    print(f"✅ Shift-Left In-DB RBAC          : {[c.doc_id for c in good]} <-- Pre-filtered, returned authorized top-1!")
    print(f"🛡️ Empty Roles Short-Circuit      : {shift_left_rbac_search(query, db, [])}")
