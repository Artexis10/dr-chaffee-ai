-- Refactor answer_cache to use normalized design like segment_embeddings
-- Migration 012: Separate tables for answer_cache and answer_cache_embeddings

-- Drop old table
DROP TABLE IF EXISTS answer_cache CASCADE;

-- Main answer cache table (no embeddings)
CREATE TABLE answer_cache (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
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

-- Separate embeddings table (normalized, like segment_embeddings)
CREATE TABLE answer_cache_embeddings (
    id SERIAL PRIMARY KEY,
    answer_cache_id INTEGER NOT NULL REFERENCES answer_cache(id) ON DELETE CASCADE,
    model_key TEXT NOT NULL,
    embedding VECTOR,  -- Dynamic size based on model
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(answer_cache_id, model_key)
);

-- Indexes for answer_cache
CREATE INDEX idx_answer_cache_style ON answer_cache(style);
CREATE INDEX idx_answer_cache_created_at ON answer_cache(created_at);
CREATE INDEX idx_answer_cache_style_created ON answer_cache(style, created_at DESC);

-- Indexes for answer_cache_embeddings
CREATE INDEX idx_answer_cache_embeddings_cache_model 
ON answer_cache_embeddings(answer_cache_id, model_key);

CREATE INDEX idx_answer_cache_embeddings_model 
ON answer_cache_embeddings(model_key) 
WHERE embedding IS NOT NULL;

-- Function to search cached answers by similarity
CREATE OR REPLACE FUNCTION search_answer_cache_by_model(
    query_embedding VECTOR,
    model_key_param TEXT,
    style_param VARCHAR(20),
    min_similarity FLOAT DEFAULT 0.92,
    limit_count INTEGER DEFAULT 5
) RETURNS TABLE (
    cache_id INTEGER,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ace.answer_cache_id,
        (1 - (ace.embedding <=> query_embedding))::FLOAT as similarity
    FROM answer_cache_embeddings ace
    JOIN answer_cache ac ON ac.id = ace.answer_cache_id
    WHERE ace.model_key = model_key_param
      AND ac.style = style_param
      AND ace.embedding IS NOT NULL
      AND ac.created_at + (ac.ttl_hours || ' hours')::INTERVAL > NOW()
      AND (1 - (ace.embedding <=> query_embedding)) >= min_similarity
    ORDER BY ace.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql STABLE;

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
COMMENT ON TABLE answer_cache_embeddings IS 'Normalized storage for answer query embeddings from multiple models';
COMMENT ON COLUMN answer_cache.style IS 'Answer style: concise or detailed';
COMMENT ON COLUMN answer_cache.ttl_hours IS 'Time-to-live in hours before cache entry expires';
COMMENT ON COLUMN answer_cache.access_count IS 'Number of times this cached answer was returned';
COMMENT ON FUNCTION search_answer_cache_by_model IS 'Find cached answers by vector similarity for a specific model';
