"""Add embedding_384 column for BGE-Small migration (Phase 1: Schema Prep)

Revision ID: 005
Revises: 004
Create Date: 2025-10-13 22:00:00

This is Phase 1 of the BGE-Small migration:
- Adds new embedding_384 column (vector(384))
- Drops old IVFFLAT index to prevent conflicts
- Safe and resumable (uses IF NOT EXISTS / IF EXISTS)

After this migration:
- Run Phase 2 (006) to backfill embeddings
- Run Phase 3 (007) to swap columns and rebuild index
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add embedding_384 column and prepare for migration"""
    print("=" * 80)
    print("PHASE 1: Adding embedding_384 column for BGE-Small migration")
    print("=" * 80)
    
    # Ensure pgvector extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    print("✅ pgvector extension verified")
    
    # Drop old index if it exists (prevents conflicts during migration)
    # Note: We use different index names to avoid confusion
    op.execute("DROP INDEX IF EXISTS idx_segments_text_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS segments_embedding_idx")
    print("✅ Old embedding index dropped (will be recreated in Phase 3)")
    
    # Add new 384-dim column (safe if already exists)
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='segments' AND column_name='embedding_384'
            ) THEN
                ALTER TABLE segments ADD COLUMN embedding_384 vector(384);
                RAISE NOTICE 'Added embedding_384 column';
            ELSE
                RAISE NOTICE 'embedding_384 column already exists, skipping';
            END IF;
        END $$;
    """)
    print("✅ embedding_384 column added (384 dimensions)")
    
    # Add comment for documentation
    op.execute("""
        COMMENT ON COLUMN segments.embedding_384 IS 
        'BGE-Small text embeddings (384-dim, BAAI/bge-small-en-v1.5) - migration in progress'
    """)
    
    print("=" * 80)
    print("PHASE 1 COMPLETE")
    print("Next: Run Phase 2 (006_backfill_embedding_384.py) to populate embeddings")
    print("=" * 80)


def downgrade() -> None:
    """Remove embedding_384 column"""
    print("Downgrading: Removing embedding_384 column")
    
    # Drop column if exists
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='segments' AND column_name='embedding_384'
            ) THEN
                ALTER TABLE segments DROP COLUMN embedding_384;
                RAISE NOTICE 'Dropped embedding_384 column';
            ELSE
                RAISE NOTICE 'embedding_384 column does not exist, skipping';
            END IF;
        END $$;
    """)
    
    print("✅ Downgrade complete (embedding_384 removed)")
    print("⚠️  Note: Original index not recreated - run migration 004 to restore")
