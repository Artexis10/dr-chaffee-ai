-- Create answer_cache table with support for 768-dimensional Nomic embeddings
-- This table caches AI-generated answers to avoid redundant OpenAI API calls

CREATE TABLE IF NOT EXISTS answer_cache (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_embedding_384 vector(384),  -- BGE-Small (speed profile)
    query_embedding_768 vector(768),  -- Nomic (current production)
    query_embedding_1536 vector(1536), -- GTE-Qwen (quality profile)
    embedding_profile TEXT NOT NULL,  -- 'speed', 'nomic', or 'quality'
    style TEXT NOT NULL,              -- 'concise', 'detailed', 'technical'
    answer_md TEXT NOT NULL,          -- Markdown-formatted answer
    citations JSONB NOT NULL,         -- Array of source citations
    confidence FLOAT,                 -- 0-1 confidence score
    notes TEXT,                       -- Optional notes about the answer
    used_chunk_ids INTEGER[],         -- IDs of chunks used
    source_clips JSONB,               -- Video clips with timestamps
    ttl_hours INTEGER DEFAULT 336,    -- Time-to-live (14 days default)
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed_at TIMESTAMP DEFAULT NOW(),
    access_count INTEGER DEFAULT 0
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_answer_cache_style_profile 
ON answer_cache(style, embedding_profile);

CREATE INDEX IF NOT EXISTS idx_answer_cache_created 
ON answer_cache(created_at);

-- Vector similarity indexes for each dimension
CREATE INDEX IF NOT EXISTS idx_answer_cache_384 
ON answer_cache USING ivfflat (query_embedding_384 vector_cosine_ops)
WHERE query_embedding_384 IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_answer_cache_768 
ON answer_cache USING ivfflat (query_embedding_768 vector_cosine_ops)
WHERE query_embedding_768 IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_answer_cache_1536 
ON answer_cache USING ivfflat (query_embedding_1536 vector_cosine_ops)
WHERE query_embedding_1536 IS NOT NULL;

-- Cleanup function to remove expired entries
CREATE OR REPLACE FUNCTION cleanup_expired_answer_cache() RETURNS void AS $$
BEGIN
    DELETE FROM answer_cache 
    WHERE created_at + (ttl_hours || ' hours')::INTERVAL < NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE answer_cache IS 'Cache for AI-generated answers to avoid redundant OpenAI API calls';
COMMENT ON COLUMN answer_cache.query_embedding_384 IS 'BGE-Small embeddings (384 dims, speed profile)';
COMMENT ON COLUMN answer_cache.query_embedding_768 IS 'Nomic embeddings (768 dims, current production)';
COMMENT ON COLUMN answer_cache.query_embedding_1536 IS 'GTE-Qwen embeddings (1536 dims, quality profile)';
