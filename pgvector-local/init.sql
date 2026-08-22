CREATE EXTENSION IF NOT EXISTS vector;
DROP TABLE IF EXISTS enterprise_documents;
CREATE TABLE enterprise_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    allowed_roles JSONB NOT NULL, 
    embedding VECTOR(1536) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_document_embeddings
ON enterprise_documents USING hnsw (embedding vector_cosine_ops);
SELECT id, LEFT(title, 80) AS title, allowed_roles, vector_dims(embedding)
FROM enterprise_documents LIMIT 3;