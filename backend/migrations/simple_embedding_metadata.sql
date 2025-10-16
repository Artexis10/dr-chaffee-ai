-- Simple approach: Track which model generated each embedding
-- No schema changes needed for different models with same dimensions

-- Add metadata column to track embedding model
ALTER TABLE segments 
ADD COLUMN IF NOT EXISTS embedding_model text DEFAULT 'gte-qwen2-1.5b',
ADD COLUMN IF NOT EXISTS embedding_created_at timestamptz DEFAULT now();

-- Create index for filtering by model
CREATE INDEX IF NOT EXISTS idx_segments_embedding_model 
ON segments(embedding_model) 
WHERE embedding IS NOT NULL;

-- Add comment
COMMENT ON COLUMN segments.embedding_model IS 'Model used to generate the embedding (e.g., gte-qwen2-1.5b, openai-3-large)';

-- Function to check if re-embedding is needed
CREATE OR REPLACE FUNCTION check_embedding_compatibility(
    current_model text,
    target_model text
) RETURNS boolean AS $$
DECLARE
    current_dims integer;
    target_dims integer;
BEGIN
    -- In practice, load from config file
    -- For now, assume 1536 for both
    RETURN current_model = target_model;
END;
$$ LANGUAGE plpgsql;
