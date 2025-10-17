-- Refactor answer_cache to use flexible embedding storage like segment_embeddings
-- Migration 012: Remove model-specific columns, use JSONB for embeddings

-- Drop old table and recreate with flexible schema
DROP TABLE IF EXISTS answer_cache CASCADE;

CREATE TABLE answer_cache (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_embedding JSONB NOT NULL, -- Store embedding as JSONB with model_key
    style VARCHAR(20) NOT NULL DEFAULT 'concise', -- 'concise' or 'detailed'
    answer_md TEXT NOT NULL,
    citations JSONB NOT NULL,
    confidence NUMERIC(3,2),
    notes TEXT,
    used_chunk_ids TEXT[],
    source_clips JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    accessed_at TIMESTAMP DEFAULT NOW(),
    access_count INTEGER DEFAULT 1,
    ttl_hours INTEGER DEFAULT 336 -- 14 days default
);

-- Create GIN index for JSONB embedding lookup
CREATE INDEX idx_answer_cache_embedding_gin ON answer_cache USING gin(query_embedding);

-- Index for TTL cleanup
CREATE INDEX idx_answer_cache_created_at ON answer_cache(created_at);

-- Index for style filtering
CREATE INDEX idx_answer_cache_style ON answer_cache(style);

-- Composite index for common queries
CREATE INDEX idx_answer_cache_style_created ON answer_cache(style, created_at DESC);

-- Function to clean up expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_answer_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM answer_cache
    WHERE created_at + (ttl_hours || ' hours')::INTERVAL < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON TABLE answer_cache IS 'Semantic cache for AI-generated answers with TTL, flexible embedding storage';
COMMENT ON COLUMN answer_cache.query_embedding IS 'JSONB object with model_key and vector array, e.g., {"bge-small-en-v1.5": [0.1, 0.2, ...]}';
COMMENT ON COLUMN answer_cache.style IS 'Answer style: concise or detailed';
COMMENT ON COLUMN answer_cache.ttl_hours IS 'Time-to-live in hours before cache entry expires';
COMMENT ON COLUMN answer_cache.access_count IS 'Number of times this cached answer was returned';
