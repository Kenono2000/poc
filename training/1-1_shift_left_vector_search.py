import asyncio
import os
from dotenv import load_dotenv
import asyncpg
from typing import List, Dict, Any

load_dotenv()

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

if __name__ == "__main__":
    asyncio.run(main())
