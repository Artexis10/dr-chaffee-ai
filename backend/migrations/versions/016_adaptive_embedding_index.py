"""Adaptive embedding index for different database environments

Revision ID: 016_adaptive_embedding_index
Revises: 015_fix_embedding_dimensions
Create Date: 2025-11-20 20:09:00.000000

This migration creates an ivfflat index with adaptive parameters based on:
- Available maintenance_work_mem (Render: 16MB, Local: 256MB+)
- Number of segments (scales lists parameter)
- Environment (local vs managed PostgreSQL)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import os

# revision identifiers, used by Alembic.
revision = '016_adaptive_embedding_index'
down_revision = '015_fix_embedding_dimensions'
branch_labels = None
depends_on = None


def upgrade():
    """Create adaptive ivfflat index based on environment"""
    
    conn = op.get_bind()
    
    # Drop existing index if it exists
    print("🗑️  Dropping old embedding index if exists...")
    conn.execute(text("DROP INDEX IF EXISTS segments_embedding_idx"))
    
    # Check available maintenance_work_mem
    result = conn.execute(text(
        "SHOW maintenance_work_mem"
    )).fetchone()
    
    mem_str = result[0] if result else "256MB"
    print(f"📊 Available maintenance_work_mem: {mem_str}")
    
    # Parse memory value
    if 'MB' in mem_str:
        mem_mb = int(mem_str.replace('MB', '').strip())
    elif 'GB' in mem_str:
        mem_mb = int(mem_str.replace('GB', '').strip()) * 1024
    else:
        mem_mb = 256  # default
    
    # Count segments to determine index size
    count_result = conn.execute(text(
        "SELECT COUNT(*) FROM segments"
    )).fetchone()
    
    segment_count = count_result[0] if count_result else 0
    print(f"📈 Total segments: {segment_count:,}")
    
    # Adaptive parameters based on environment
    if mem_mb <= 16:
        # Render managed PostgreSQL (16MB limit)
        lists = 20
        env = "Render (16MB)"
    elif mem_mb <= 64:
        # Small local setup
        lists = 50
        env = "Small (64MB)"
    elif mem_mb <= 256:
        # Standard local setup
        lists = 100
        env = "Standard (256MB)"
    else:
        # Large local setup
        lists = 200
        env = "Large (512MB+)"
    
    print(f"🎯 Environment: {env}")
    print(f"📍 Using lists={lists} for ivfflat index")
    
    # Create index with adaptive parameters
    print(f"🔨 Creating embedding index with lists={lists}...")
    conn.execute(text(f"""
        CREATE INDEX segments_embedding_idx 
        ON segments 
        USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists={lists})
    """))
    
    # Add helpful comment
    conn.execute(text(f"""
        COMMENT ON INDEX segments_embedding_idx IS 
        'Adaptive ivfflat index for semantic search. Lists={lists} for {env} environment. Segment count: {segment_count:,}'
    """))
    
    print(f"✅ Index created successfully with adaptive parameters")
    print(f"   Environment: {env}")
    print(f"   Lists: {lists}")
    print(f"   Segments: {segment_count:,}")


def downgrade():
    """Drop the adaptive embedding index"""
    print("⚠️  Dropping embedding index...")
    op.execute(text("DROP INDEX IF EXISTS segments_embedding_idx"))
