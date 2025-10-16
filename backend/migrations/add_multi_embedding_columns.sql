-- Add multiple embedding columns for different models
-- This allows switching between embedding providers without re-embedding everything

-- OpenAI text-embedding-3-large (1536 dims)
ALTER TABLE segments 
ADD COLUMN IF NOT EXISTS embedding_openai vector(1536);

-- GTE-Qwen2-1.5B-instruct (1536 dims) - rename existing column
ALTER TABLE segments 
RENAME COLUMN embedding TO embedding_gte_qwen;

-- BGE-large-en-v1.5 (1024 dims) - for future use
ALTER TABLE segments 
ADD COLUMN IF NOT EXISTS embedding_bge vector(1024);

-- Create indexes for each embedding column
CREATE INDEX IF NOT EXISTS idx_segments_embedding_openai 
ON segments USING ivfflat (embedding_openai vector_cosine_ops) 
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_segments_embedding_gte_qwen 
ON segments USING ivfflat (embedding_gte_qwen vector_cosine_ops) 
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_segments_embedding_bge 
ON segments USING ivfflat (embedding_bge vector_cosine_ops) 
WITH (lists = 100);

-- Add metadata to track which embeddings are populated
ALTER TABLE segments 
ADD COLUMN IF NOT EXISTS embedding_providers text[];

COMMENT ON COLUMN segments.embedding_openai IS 'OpenAI text-embedding-3-large (1536 dims)';
COMMENT ON COLUMN segments.embedding_gte_qwen IS 'GTE-Qwen2-1.5B-instruct (1536 dims)';
COMMENT ON COLUMN segments.embedding_bge IS 'BGE-large-en-v1.5 (1024 dims)';
