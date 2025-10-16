-- Multi-provider embedding storage
-- Each model gets its own column, switch providers instantly via config

-- Rename existing column to be explicit about model
ALTER TABLE segments 
RENAME COLUMN embedding TO embedding_gte_qwen;

-- Add columns for other providers (same dimensions = same column type)
ALTER TABLE segments 
ADD COLUMN IF NOT EXISTS embedding_openai vector(1536);

-- Add metadata to track which embeddings are populated
ALTER TABLE segments 
ADD COLUMN IF NOT EXISTS has_gte_qwen boolean GENERATED ALWAYS AS (embedding_gte_qwen IS NOT NULL) STORED,
ADD COLUMN IF NOT EXISTS has_openai boolean GENERATED ALWAYS AS (embedding_openai IS NOT NULL) STORED;

-- Create indexes for each provider
CREATE INDEX IF NOT EXISTS idx_segments_embedding_gte_qwen 
ON segments USING ivfflat (embedding_gte_qwen vector_cosine_ops) 
WITH (lists = 100)
WHERE embedding_gte_qwen IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_segments_embedding_openai 
ON segments USING ivfflat (embedding_openai vector_cosine_ops) 
WITH (lists = 100)
WHERE embedding_openai IS NOT NULL;

-- View to see embedding coverage
CREATE OR REPLACE VIEW embedding_coverage AS
SELECT 
    COUNT(*) as total_segments,
    COUNT(embedding_gte_qwen) as gte_qwen_count,
    COUNT(embedding_openai) as openai_count,
    ROUND(100.0 * COUNT(embedding_gte_qwen) / COUNT(*), 1) as gte_qwen_pct,
    ROUND(100.0 * COUNT(embedding_openai) / COUNT(*), 1) as openai_pct
FROM segments
WHERE text IS NOT NULL AND text != '';

COMMENT ON COLUMN segments.embedding_gte_qwen IS 'GTE-Qwen2-1.5B embeddings (1536 dims) - local/free';
COMMENT ON COLUMN segments.embedding_openai IS 'OpenAI text-embedding-3-large (1536 dims) - API/paid';
