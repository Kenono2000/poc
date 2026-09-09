-- Schema Setup: Dual Indexing for Vector Proximity + Role Overlap
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    content TEXT NOT NULL,
    allowed_roles JSONB NOT NULL,
    embedding vector(1536) -- Matryoshka-truncated dimensions
);

-- HNSW Vector Index (Cosine Distance)
CREATE INDEX IF NOT EXISTS idx_chunks_hnsw_cosine 
ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- GIN Index for O(1) Role Set-Intersection
CREATE INDEX IF NOT EXISTS idx_chunks_gin_roles 
ON document_chunks 
USING gin (allowed_roles);

-- Shift-Left Retrieval Query
SELECT 
    id, 
    content, 
    allowed_roles, 
    embedding <=> $1::vector AS cosine_distance
FROM document_chunks
WHERE allowed_roles ?| $2::text[] -- In-engine RBAC gate
ORDER BY cosine_distance ASC
LIMIT $3;