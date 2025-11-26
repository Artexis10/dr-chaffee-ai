-- Migration: 015_search_config.sql
-- Purpose: Store search configuration parameters that can be tuned via the dashboard
-- Created: 2025-11-26

-- Create search_config table with a single row (id=1)
CREATE TABLE IF NOT EXISTS search_config (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),  -- Ensures only one row
    top_k INTEGER NOT NULL DEFAULT 100,                -- Initial results to consider
    min_similarity REAL NOT NULL DEFAULT 0.3,          -- Minimum relevance threshold (0-1)
    enable_reranker BOOLEAN NOT NULL DEFAULT FALSE,    -- Use reranking step
    rerank_top_k INTEGER NOT NULL DEFAULT 200,         -- Candidates for reranking
    return_top_k INTEGER NOT NULL DEFAULT 20,          -- Final results to return
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default row
INSERT INTO search_config (id, top_k, min_similarity, enable_reranker, rerank_top_k, return_top_k)
VALUES (1, 100, 0.3, FALSE, 200, 20)
ON CONFLICT (id) DO NOTHING;

-- Create function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_search_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for auto-updating timestamp
DROP TRIGGER IF EXISTS search_config_updated_at ON search_config;
CREATE TRIGGER search_config_updated_at
    BEFORE UPDATE ON search_config
    FOR EACH ROW
    EXECUTE FUNCTION update_search_config_timestamp();

-- Add comment
COMMENT ON TABLE search_config IS 'Search configuration parameters tunable via the dashboard';
