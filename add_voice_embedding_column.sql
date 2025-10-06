-- Add voice_embedding column for speaker identification
-- This stores 192-dim SpeechBrain ECAPA embeddings
-- Separate from text embeddings (1536-dim) used for semantic search

ALTER TABLE segments ADD COLUMN IF NOT EXISTS voice_embedding jsonb;

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_segments_voice_embedding ON segments USING gin (voice_embedding);

-- Add comment
COMMENT ON COLUMN segments.voice_embedding IS '192-dim SpeechBrain ECAPA voice embedding for speaker identification';
