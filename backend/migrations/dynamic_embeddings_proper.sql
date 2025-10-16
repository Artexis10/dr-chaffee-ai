-- Proper multi-model embedding storage
-- Uses JSONB for metadata + separate table for vectors (normalized design)

-- Create embeddings table (normalized)
CREATE TABLE IF NOT EXISTS segment_embeddings (
    id SERIAL PRIMARY KEY,
    segment_id INTEGER NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
    model_key TEXT NOT NULL,
    model_name TEXT NOT NULL,
    provider TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    embedding VECTOR,  -- Dynamic size based on dimensions
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(segment_id, model_key)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_segment_embeddings_segment_model 
ON segment_embeddings(segment_id, model_key);

CREATE INDEX IF NOT EXISTS idx_segment_embeddings_model 
ON segment_embeddings(model_key) 
WHERE embedding IS NOT NULL;

-- Dynamic vector similarity search function
CREATE OR REPLACE FUNCTION search_by_model(
    query_embedding VECTOR,
    model_key_param TEXT,
    min_similarity FLOAT DEFAULT 0.5,
    limit_count INTEGER DEFAULT 50
) RETURNS TABLE (
    segment_id INTEGER,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        se.segment_id,
        (1 - (se.embedding <=> query_embedding))::FLOAT as similarity
    FROM segment_embeddings se
    WHERE se.model_key = model_key_param
      AND se.embedding IS NOT NULL
      AND (1 - (se.embedding <=> query_embedding)) >= min_similarity
    ORDER BY se.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql STABLE;

-- View for embedding coverage by model
CREATE OR REPLACE VIEW embedding_coverage_by_model AS
SELECT 
    model_key,
    model_name,
    provider,
    dimensions,
    COUNT(*) as segment_count,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM segment_embeddings
WHERE embedding IS NOT NULL
GROUP BY model_key, model_name, provider, dimensions
ORDER BY segment_count DESC;

-- Function to upsert embedding
CREATE OR REPLACE FUNCTION upsert_segment_embedding(
    p_segment_id INTEGER,
    p_model_key TEXT,
    p_model_name TEXT,
    p_provider TEXT,
    p_dimensions INTEGER,
    p_embedding FLOAT[]
) RETURNS VOID AS $$
BEGIN
    INSERT INTO segment_embeddings (
        segment_id, model_key, model_name, provider, dimensions, embedding
    ) VALUES (
        p_segment_id, p_model_key, p_model_name, p_provider, p_dimensions, p_embedding::VECTOR
    )
    ON CONFLICT (segment_id, model_key) 
    DO UPDATE SET
        embedding = EXCLUDED.embedding,
        created_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Migrate existing embeddings from segments table
DO $$
DECLARE
    r RECORD;
    embedding_array FLOAT[];
BEGIN
    -- Check if old embedding column exists
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'segments' AND column_name = 'embedding'
    ) THEN
        -- Migrate to new structure
        FOR r IN 
            SELECT id, embedding::text as embedding_text
            FROM segments 
            WHERE embedding IS NOT NULL
            LIMIT 1000  -- Test with small batch first
        LOOP
            -- Convert vector text representation to float array
            -- Remove brackets and split by comma
            embedding_array := string_to_array(
                trim(both '[]' from r.embedding_text), 
                ','
            )::FLOAT[];
            
            PERFORM upsert_segment_embedding(
                r.id,
                'gte-qwen2-1.5b',
                'Alibaba-NLP/gte-Qwen2-1.5B-instruct',
                'local',
                1536,
                embedding_array
            );
        END LOOP;
        
        RAISE NOTICE 'Migrated % embeddings. Run full migration separately.', (
            SELECT COUNT(*) FROM segments WHERE embedding IS NOT NULL LIMIT 1000
        );
    END IF;
END $$;

COMMENT ON TABLE segment_embeddings IS 'Normalized storage for embeddings from multiple models with different dimensions';
COMMENT ON FUNCTION search_by_model IS 'Perform vector similarity search for a specific model';
