-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table definition
CREATE TABLE IF NOT EXISTS document_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content TEXT NOT NULL,
    allowed_roles JSONB NOT NULL,
    embedding vector(1536) -- Matryoshka dimension truncation from 3072 to 1536
);

-- 1. Vector Proximity Index (HNSW using Cosine Distance)
CREATE INDEX IF NOT EXISTS idx_documents_hnsw_embedding 
ON document_embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 2. Role-Intersection Index (GIN on JSONB array)
CREATE INDEX IF NOT EXISTS idx_documents_gin_roles 
ON document_embeddings 
USING gin (allowed_roles);

-----------------------------------------------------------------

-- Clean previous run
TRUNCATE document_embeddings;

-- Seed mock documents (using dummy 1536-dim unit vectors for demonstration)
INSERT INTO document_embeddings (content, allowed_roles, embedding) VALUES
(
    'Q3 Board Memo: Planned acquisition targets and executive compensation.',
    '["executive", "board_member"]'::jsonb,
    (SELECT array_agg(0.01)::vector(1536) FROM generate_series(1, 1536))
),
(
    'Q3 Earnings Breakdown: Preliminary gross margin and revenue variances.',
    '["finance_analyst", "executive"]'::jsonb,
    (SELECT array_agg(0.02)::vector(1536) FROM generate_series(1, 1536))
),
(
    'Engineering Roadmap: Core platform microservice migration plan.',
    '["engineering", "product_manager"]'::jsonb,
    (SELECT array_agg(0.03)::vector(1536) FROM generate_series(1, 1536))
);

-----------------------------------------------------------------

-- Insecure: Fetches Top-K records globally into application memory
SELECT id, content, allowed_roles, embedding <=> (array_fill(0.1::float8, ARRAY[1536]))::vector AS distance
FROM document_embeddings
ORDER BY distance ASC
LIMIT 5;

-----------------------------------------------------------------

-- Secure: Pushes role-containment directly into the index scan
SELECT id, content, allowed_roles, embedding <=> (array_fill(0.1::float8, ARRAY[1536]))::vector AS distance
FROM document_embeddings
WHERE allowed_roles ?| ARRAY['engineering', 'devops']
ORDER BY distance ASC
LIMIT 5;

-----------------------------------------------------------------

--  python -c "print('[' + ', '.join(['0.1']*1536) + ']')"
SET enable_seqscan = off; -- Turn off sequential scans

EXPLAIN ANALYZE
SELECT id, content, allowed_roles, embedding <=> (array_fill(0.1::float8, ARRAY[1536]))::vector AS distance
FROM document_embeddings
WHERE allowed_roles ?| ARRAY['finance_analyst', 'engineering']
ORDER BY distance ASC
LIMIT 5;

