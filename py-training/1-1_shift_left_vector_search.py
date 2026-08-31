import asyncio
import sys
from pathlib import Path
from typing import Any

import asyncpg
import numpy as np
from openai import AsyncOpenAI

sys.path.insert(0, str(Path(__file__).parent.parent / "py-libraries"))
from utilities import expand_user_roles, load_config, truncate_and_normalize

openai_api_key, _ = load_config(str(Path(__file__).parent / ".env"))
openai_client = AsyncOpenAI(api_key=openai_api_key)

async def get_matryoshka_embedding(text: str, target_dim: int = 1536) -> list[float]:
    response = await openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    raw_vector = response.data[0].embedding
    return truncate_and_normalize(raw_vector, target_dim=target_dim)

async def insert_document_chunk(
    pool: asyncpg.Pool,
    content: str,
    allowed_roles: list[str]
):
    vector_1536 = await get_matryoshka_embedding(content, target_dim=1536)
    query = """
        INSERT INTO document_embeddings (content, allowed_roles, embedding)
        VALUES ($1, $2::jsonb, $3::vector)
    """
    async with pool.acquire() as conn:
        await conn.execute(query, content, allowed_roles, str(vector_1536))

async def shift_left_vector_search(
    pool: asyncpg.Pool,
    query_vector: list[float],
    user_roles: list[str],
    limit: int = 5
) -> list[dict[str, Any]]:
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
    _, database_url = load_config(str(Path(__file__).parent / ".env"))

    print("Connecting to database...")
    pool = await asyncpg.create_pool(dsn=database_url)

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

    except (asyncpg.PostgresError, ValueError) as e:
        print(f"An error occurred: {e}")
    finally:
        await pool.close()
        print("Database connection closed.")

async def search_with_rbac(
    pool: asyncpg.Pool,
    user_query: str,
    user_roles: list[str],
    limit: int = 5
) -> list[dict[str, Any]]:
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

def test_matryoshka_normalization():
    raw_embedding = [0.05] * 3072
    result = truncate_and_normalize(raw_embedding, target_dim=1536)
    assert len(result) == 1536
    l2_norm = np.linalg.norm(np.array(result, dtype=np.float32))
    np.testing.assert_almost_equal(l2_norm, 1.0, decimal=5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (asyncpg.PostgresError, ValueError) as e:
        print(f"Main execution skipped or failed: {e}")
