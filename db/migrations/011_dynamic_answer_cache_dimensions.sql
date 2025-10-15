-- Dynamic answer cache to support both embedding profiles
-- Migration 011: Support both BGE-small (384) and GTE-Qwen2 (1536) dimensions

-- Drop existing answer_cache table and recreate with flexible schema
DROP TABLE IF EXISTS answer_cache CASCADE;

CREATE TABLE answer_cache (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_embedding_384 vector(384),  -- BGE-small (speed profile)
    query_embedding_1536 vector(1536), -- GTE-Qwen2 (quality profile)
    embedding_profile VARCHAR(20) NOT NULL, -- 'speed' or 'quality'
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

-- Indexes for both embedding types
CREATE INDEX idx_answer_cache_embedding_384 ON answer_cache 
USING ivfflat (query_embedding_384 vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_answer_cache_embedding_1536 ON answer_cache 
USING ivfflat (query_embedding_1536 vector_cosine_ops)
WITH (lists = 100);

-- Index for TTL cleanup
CREATE INDEX idx_answer_cache_created_at ON answer_cache(created_at);

-- Index for style filtering
CREATE INDEX idx_answer_cache_style ON answer_cache(style);

-- Index for profile filtering
CREATE INDEX idx_answer_cache_profile ON answer_cache(embedding_profile);

-- Composite index for common queries
CREATE INDEX idx_answer_cache_profile_style_created ON answer_cache(embedding_profile, style, created_at DESC);

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
COMMENT ON TABLE answer_cache IS 'Semantic cache for AI-generated answers with TTL, supports both embedding profiles';
COMMENT ON COLUMN answer_cache.query_embedding_384 IS 'BGE-small embedding (384-dim) for speed profile';
COMMENT ON COLUMN answer_cache.query_embedding_1536 IS 'GTE-Qwen2-1.5B embedding (1536-dim) for quality profile';
COMMENT ON COLUMN answer_cache.embedding_profile IS 'Embedding profile used: speed (384) or quality (1536)';
COMMENT ON COLUMN answer_cache.style IS 'Answer style: concise or detailed';
COMMENT ON COLUMN answer_cache.ttl_hours IS 'Time-to-live in hours before cache entry expires';
COMMENT ON COLUMN answer_cache.access_count IS 'Number of times this cached answer was returned';
