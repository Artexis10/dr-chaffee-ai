"""Create answer_cache table with 768-dim Nomic support

Revision ID: 009
Revises: 008
Create Date: 2025-10-17 10:55:00

This migration creates the answer_cache table for caching AI-generated answers
to avoid redundant OpenAI API calls. Supports multiple embedding dimensions:
- 384 dims: BGE-Small (speed profile)
- 768 dims: Nomic (current production)
- 1536 dims: GTE-Qwen (quality profile)

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    print("Creating answer_cache table with multi-dimensional embedding support...")
    
    # Create answer_cache table
    op.execute("""
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
        )
    """)
    
    # Create indexes for fast lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_answer_cache_style_profile 
        ON answer_cache(style, embedding_profile)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_answer_cache_created 
        ON answer_cache(created_at)
    """)
    
    # Vector similarity indexes for each dimension
    # Note: ivfflat indexes are created with lists parameter based on expected data size
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_answer_cache_384 
        ON answer_cache USING ivfflat (query_embedding_384 vector_cosine_ops)
        WITH (lists = 50)
        WHERE query_embedding_384 IS NOT NULL
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_answer_cache_768 
        ON answer_cache USING ivfflat (query_embedding_768 vector_cosine_ops)
        WITH (lists = 50)
        WHERE query_embedding_768 IS NOT NULL
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_answer_cache_1536 
        ON answer_cache USING ivfflat (query_embedding_1536 vector_cosine_ops)
        WITH (lists = 50)
        WHERE query_embedding_1536 IS NOT NULL
    """)
    
    # Create cleanup function for expired entries
    op.execute("""
        CREATE OR REPLACE FUNCTION cleanup_expired_answer_cache() RETURNS void AS $$
        BEGIN
            DELETE FROM answer_cache 
            WHERE created_at + (ttl_hours || ' hours')::INTERVAL < NOW();
        END;
        $$ LANGUAGE plpgsql
    """)
    
    # Add table and column comments
    op.execute("""
        COMMENT ON TABLE answer_cache IS 
        'Cache for AI-generated answers to avoid redundant OpenAI API calls'
    """)
    
    op.execute("""
        COMMENT ON COLUMN answer_cache.query_embedding_384 IS 
        'BGE-Small embeddings (384 dims, speed profile)'
    """)
    
    op.execute("""
        COMMENT ON COLUMN answer_cache.query_embedding_768 IS 
        'Nomic embeddings (768 dims, current production)'
    """)
    
    op.execute("""
        COMMENT ON COLUMN answer_cache.query_embedding_1536 IS 
        'GTE-Qwen embeddings (1536 dims, quality profile)'
    """)
    
    print("[OK] answer_cache table created successfully")
    print("[OK] Vector indexes created for 384, 768, and 1536 dimensions")
    print("[OK] Cleanup function created")


def downgrade() -> None:
    print("Dropping answer_cache table and related objects...")
    
    # Drop function
    op.execute("DROP FUNCTION IF EXISTS cleanup_expired_answer_cache()")
    
    # Drop table (indexes will be dropped automatically)
    op.execute("DROP TABLE IF EXISTS answer_cache CASCADE")
    
    print("[OK] answer_cache table dropped")
