-- Fix answer_cache embedding dimensions to match segments table (1536)
-- Migration 010: Update answer_cache to use GTE-Qwen2 dimensions

-- Drop the old column and recreate with correct dimensions
ALTER TABLE answer_cache DROP COLUMN IF EXISTS query_embedding;
ALTER TABLE answer_cache ADD COLUMN query_embedding vector(1536);

-- Recreate the index
DROP INDEX IF EXISTS idx_answer_cache_embedding;
CREATE INDEX idx_answer_cache_embedding ON answer_cache 
USING ivfflat (query_embedding vector_cosine_ops)
WITH (lists = 100);

-- Update comment
COMMENT ON COLUMN answer_cache.query_embedding IS 'GTE-Qwen2-1.5B embedding (1536-dim) for semantic similarity matching';
