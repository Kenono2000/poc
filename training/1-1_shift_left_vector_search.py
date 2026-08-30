import asyncio
import os
import numpy as np
import asyncpg
from openai import AsyncOpenAI
from dotenv import load_dotenv
from typing import List, Dict, Any, Union
# pipreqs . --force

load_dotenv()

openai_client = AsyncOpenAI()

ROLE_HIERARCHY = {
    "admin": ["admin", "executive", "finance_analyst", "engineering"],
    "finance_lead": ["finance_lead", "finance_analyst"],
    "engineering": ["engineering"]
}

def expand_user_roles(raw_roles: List[str]) -> List[str]:
    expanded = set()
    for role in raw_roles:
        expanded.update(ROLE_HIERARCHY.get(role, [role]))
    return list(expanded)

async def get_matryoshka_embedding(text: str, target_dim: int = 1536) -> List[float]:
    """Fetches a 3072-dim embedding and truncates it to 1536 dimensions."""
    response = await openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    raw_vector = response.data[0].embedding
    return truncate_and_normalize(raw_vector, target_dim=target_dim)

def truncate_and_normalize(
    embedding: Union[List[float], np.ndarray], 
    target_dim: int = 1536
) -> List[float]:
    """
    Slices a Matryoshka vector to target_dim and re-normalizes to unit length (L2 norm = 1.0).
    
    Args:
        embedding: Raw floating-point vector (e.g., 3072 dimensions).
        target_dim: Target dimensional prefix (default 1536).
        
    Returns:
        List[float]: Sliced, unit-normalized vector ready for pgvector insertion/querying.
    """
    # 1. Truncate vector to target prefix dimension
    vec = np.asarray(embedding[:target_dim], dtype=np.float32)
    
    # 2. Compute Euclidean (L2) norm: sqrt(sum(x_i^2))
    norm = np.linalg.norm(vec)
    
    # 3. Guard against zero vectors (prevent division by zero)
    if norm == 0.0:
        return vec.tolist()
    
    # 4. Unit-normalize: ||v||_2 = 1.0
    normalized_vec = vec / norm
    
    return normalized_vec.tolist()

async def insert_document_chunk(
    pool: asyncpg.Pool, 
    content: str, 
    allowed_roles: List[str]
):
    """Generates a truncated vector and persists it with GIN-indexed roles."""
    vector_1536 = await get_matryoshka_embedding(content, target_dim=1536)
    
    query = """
        INSERT INTO document_embeddings (content, allowed_roles, embedding)
        VALUES ($1, $2::jsonb, $3::vector)
    """
    async with pool.acquire() as conn:
        await conn.execute(query, content, allowed_roles, str(vector_1536))

async def shift_left_vector_search(
    pool: asyncpg.Pool, 
    query_vector: List[float], 
    user_roles: List[str], 
    limit: int = 5
) -> List[Dict[str, Any]]:
    effective_roles = expand_user_roles(user_roles)
    
    query = """
        SELECT id, content, allowed_roles, embedding <=> $1::vector AS distance
        FROM document_embeddings
        WHERE allowed_roles ?| $2::text[]
        ORDER BY distance ASC
        LIMIT $3;
    """
    
    async with pool.acquire() as conn:
        records = await conn.fetch(query, str(query_vector), effective_roles, limit)
        return [dict(record) for record in records]

async def main():
    db_url = os.getenv("DATABASE_URL")
    
    print("Connecting to database...")
    pool = await asyncpg.create_pool(dsn=db_url)
    
    try:
        mock_query_vector = [0.1] * 1536 
        mock_user_roles = ["finance_analyst"]
        
        print("Executing shift-left vector search...")
        results = await shift_left_vector_search(
            pool=pool,
            query_vector=mock_query_vector,
            user_roles=mock_user_roles,
            limit=5
        )
        
        if results:
            print(f"Found {len(results)} documents:")
            for row in results:
                print(f"- ID: {row['id']}, Distance: {row['distance']}, Content: {row['content'][:50]}...")
        else:
            print("No documents found matching the roles.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await pool.close()
        print("Database connection closed.")

async def search_with_rbac(
    pool: asyncpg.Pool,
    user_query: str,
    user_roles: List[str],
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Performs Shift-Left vector search using a truncated query vector."""
    query_vector = await get_matryoshka_embedding(user_query, target_dim=1536)
    
    query = """
        SELECT id, content, allowed_roles, embedding <=> $1::vector AS distance
        FROM document_embeddings
        WHERE allowed_roles ?| $2::text[]
        ORDER BY distance ASC
        LIMIT $3;
    """
    async with pool.acquire() as conn:
        records = await conn.fetch(query, str(query_vector), user_roles, limit)
        return [dict(r) for r in records]

#  python -m pytest .\1-1_shift_left_vector_search.py::test_matryoshka_normalization
def test_matryoshka_normalization():
    # Mock raw 3072-dimensional vector
    raw_embedding = [0.05] * 3072
    
    # Apply truncation to 1536
    result = truncate_and_normalize(raw_embedding, target_dim=1536)
    
    # Invariant 1: Dimensionality matches target
    assert len(result) == 1536
    
    # Invariant 2: Vector length equals 1.0 (within float32 precision)
    l2_norm = np.linalg.norm(np.array(result, dtype=np.float32))
    np.testing.assert_almost_equal(l2_norm, 1.0, decimal=5)

if __name__ == "__main__":
    # Run main integration
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Main execution skipped or failed: {e}")
