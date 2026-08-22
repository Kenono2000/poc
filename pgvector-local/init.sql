-- 1. Create extension (Idempotent)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create table (Idempotent)
-- Removed DROP TABLE to prevent data loss.
-- Added IF NOT EXISTS to safely skip if the table already exists.
CREATE TABLE IF NOT EXISTS enterprise_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    allowed_roles JSONB NOT NULL, 
    embedding VECTOR(1536) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create index (Idempotent)
CREATE INDEX IF NOT EXISTS idx_document_embeddings
ON enterprise_documents USING hnsw (embedding vector_cosine_ops);

-- 4. Query data (Read-only, naturally idempotent)
SELECT id, LEFT(title, 80) AS title, allowed_roles, vector_dims(embedding)
FROM enterprise_documents LIMIT 3;