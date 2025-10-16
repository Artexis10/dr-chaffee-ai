-- Flexible embedding storage - supports any model/dimension combination
-- Store embeddings as JSONB with metadata, use materialized columns for vector search

-- Add JSONB column to store all embeddings with metadata
ALTER TABLE segments 
ADD COLUMN IF NOT EXISTS embeddings_store jsonb DEFAULT '{}'::jsonb;

-- Create a function to extract vector from JSONB for a specific model
CREATE OR REPLACE FUNCTION get_embedding_vector(
    embeddings jsonb, 
    model_key text
) RETURNS vector AS $$
DECLARE
    embedding_data jsonb;
    vector_array float[];
BEGIN
    embedding_data := embeddings->model_key;
    IF embedding_data IS NULL THEN
        RETURN NULL;
    END IF;
    
    -- Extract vector array from JSONB
    SELECT ARRAY(SELECT jsonb_array_elements_text(embedding_data->'vector')::float)
    INTO vector_array;
    
    RETURN vector_array::vector;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create generated columns for common models (for performance)
-- These are automatically updated when embeddings_store changes

-- GTE-Qwen (1536 dims)
ALTER TABLE segments 
ADD COLUMN IF NOT EXISTS embedding_gte_qwen vector(1536)
GENERATED ALWAYS AS (get_embedding_vector(embeddings_store, 'gte-qwen2-1.5b')::vector(1536)) STORED;

-- OpenAI (1536 dims)
ALTER TABLE segments 
ADD COLUMN IF NOT EXISTS embedding_openai vector(1536)
GENERATED ALWAYS AS (get_embedding_vector(embeddings_store, 'openai-3-large')::vector(1536)) STORED;

-- BGE (1024 dims)
ALTER TABLE segments 
ADD COLUMN IF NOT EXISTS embedding_bge vector(1024)
GENERATED ALWAYS AS (get_embedding_vector(embeddings_store, 'bge-large-en')::vector(1024)) STORED;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_segments_embedding_gte_qwen 
ON segments USING ivfflat (embedding_gte_qwen vector_cosine_ops) 
WITH (lists = 100)
WHERE embedding_gte_qwen IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_segments_embedding_openai 
ON segments USING ivfflat (embedding_openai vector_cosine_ops) 
WITH (lists = 100)
WHERE embedding_openai IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_segments_embedding_bge 
ON segments USING ivfflat (embedding_bge vector_cosine_ops) 
WITH (lists = 100)
WHERE embedding_bge IS NOT NULL;

-- Create GIN index on JSONB for metadata queries
CREATE INDEX IF NOT EXISTS idx_segments_embeddings_store 
ON segments USING gin (embeddings_store);

-- Helper function to add/update an embedding
CREATE OR REPLACE FUNCTION upsert_embedding(
    segment_id integer,
    model_key text,
    model_name text,
    dimensions integer,
    vector_data float[],
    provider text DEFAULT NULL
) RETURNS void AS $$
BEGIN
    UPDATE segments
    SET embeddings_store = jsonb_set(
        COALESCE(embeddings_store, '{}'::jsonb),
        ARRAY[model_key],
        jsonb_build_object(
            'model', model_name,
            'dimensions', dimensions,
            'vector', to_jsonb(vector_data),
            'provider', provider,
            'created_at', now()
        )
    )
    WHERE id = segment_id;
END;
$$ LANGUAGE plpgsql;

-- Migrate existing embedding column to new structure
DO $$
DECLARE
    r RECORD;
BEGIN
    -- Only migrate if old embedding column exists and has data
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'segments' AND column_name = 'embedding'
    ) THEN
        FOR r IN 
            SELECT id, embedding 
            FROM segments 
            WHERE embedding IS NOT NULL
        LOOP
            PERFORM upsert_embedding(
                r.id,
                'gte-qwen2-1.5b',
                'Alibaba-NLP/gte-Qwen2-1.5B-instruct',
                1536,
                r.embedding::float[],
                'local'
            );
        END LOOP;
        
        -- Drop old column after migration
        ALTER TABLE segments DROP COLUMN IF EXISTS embedding;
    END IF;
END $$;

COMMENT ON COLUMN segments.embeddings_store IS 'Flexible storage for embeddings from multiple models. Format: {model_key: {model, dimensions, vector, provider, created_at}}';
COMMENT ON FUNCTION upsert_embedding IS 'Add or update an embedding for a segment. Automatically updates generated vector columns.';
