-- Answer cache table with semantic similarity search
CREATE TABLE IF NOT EXISTS answer_cache (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_embedding vector(384), -- BGE-small embedding dimension
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

-- Index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_answer_cache_embedding ON answer_cache 
USING ivfflat (query_embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for TTL cleanup
CREATE INDEX IF NOT EXISTS idx_answer_cache_created_at ON answer_cache(created_at);

-- Index for style filtering
CREATE INDEX IF NOT EXISTS idx_answer_cache_style ON answer_cache(style);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_answer_cache_style_created ON answer_cache(style, created_at DESC);

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
COMMENT ON TABLE answer_cache IS 'Semantic cache for AI-generated answers with TTL';
COMMENT ON COLUMN answer_cache.query_embedding IS 'BGE-small embedding for semantic similarity matching';
COMMENT ON COLUMN answer_cache.style IS 'Answer style: concise or detailed';
COMMENT ON COLUMN answer_cache.ttl_hours IS 'Time-to-live in hours before cache entry expires';
COMMENT ON COLUMN answer_cache.access_count IS 'Number of times this cached answer was returned';
