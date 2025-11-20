"""Fix embedding dimensions to match .env configuration

Revision ID: 015_fix_embedding_dimensions
Revises: 012_custom_instructions
Create Date: 2025-11-20 14:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import os
from pathlib import Path
from dotenv import load_dotenv

# revision identifiers, used by Alembic.
revision = '015_fix_embedding_dimensions'
down_revision = '012_custom_instructions'
branch_labels = None
depends_on = None


def upgrade():
    """
    Dynamically adjust embedding vector dimensions based on .env configuration.
    This allows switching between embedding models without manual SQL.
    """
    # Load .env from project root
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    # Get embedding dimensions from environment
    embedding_dims = int(os.getenv('EMBEDDING_DIMENSIONS', '384'))
    
    print(f"🔧 Adjusting embedding dimensions to {embedding_dims} (from .env)")
    
    conn = op.get_bind()
    
    # Check current dimensions
    result = conn.execute(text("""
        SELECT atttypmod 
        FROM pg_attribute 
        WHERE attrelid = 'segments'::regclass 
        AND attname = 'embedding'
    """)).fetchone()
    
    if result and result[0] > 0:
        current_dims = result[0] - 4
        if current_dims == embedding_dims:
            print(f"✅ Embedding dimensions already correct ({embedding_dims})")
            return
        print(f"📊 Current dimensions: {current_dims}, Target: {embedding_dims}")
    
    # Drop existing index (will be recreated with correct dimensions)
    print("🗑️  Dropping old embedding index...")
    conn.execute(text("DROP INDEX IF EXISTS segments_embedding_idx"))
    
    # Alter column to new dimensions
    print(f"🔄 Changing embedding column to vector({embedding_dims})...")
    conn.execute(text(f"ALTER TABLE segments ALTER COLUMN embedding TYPE vector({embedding_dims})"))
    
    # Recreate index with new dimensions
    print("🔨 Creating new embedding index...")
    conn.execute(text("""
        CREATE INDEX segments_embedding_idx 
        ON segments 
        USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100)
    """))
    
    # Update comment
    conn.execute(text(f"""
        COMMENT ON COLUMN segments.embedding IS 
        'Text embedding vector for semantic search ({embedding_dims}-dim, from .env EMBEDDING_MODEL)'
    """))
    
    print(f"✅ Successfully updated embedding dimensions to {embedding_dims}")


def downgrade():
    """
    Downgrade is not supported for dimension changes as it would lose data.
    To change dimensions, update .env and run upgrade again.
    """
    print("⚠️  Downgrade not supported for embedding dimension changes")
    print("💡 To change dimensions: update EMBEDDING_DIMENSIONS in .env and run 'alembic upgrade head'")
