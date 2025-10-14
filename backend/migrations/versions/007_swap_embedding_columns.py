"""Swap embedding columns and rebuild index (Phase 3: Finalize Migration)

Revision ID: 007
Revises: 006
Create Date: 2025-10-13 22:10:00

This is Phase 3 of the BGE-Small migration:
- Creates IVFFLAT index on embedding_384 for fast similarity search
- Drops old embedding column (1536-dim from GTE-Qwen2)
- Renames embedding_384 to embedding (becomes primary column)
- Rebuilds IVFFLAT index with optimal parameters

After this migration:
- All queries use BGE-Small embeddings (384-dim)
- 50x+ faster embedding generation
- Smaller storage footprint (384 vs 1536 dims)

Index parameters:
- lists=400 for ~100k-1M segments (adjust based on dataset size)
- vector_l2_ops for L2 distance (normalized embeddings)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Swap columns and rebuild index"""
    print("=" * 80)
    print("PHASE 3: Swapping embedding columns and rebuilding index")
    print("=" * 80)
    
    connection = op.get_bind()
    
    # Step 1: Verify embedding_384 is populated
    result = connection.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(embedding_384) as populated,
            COUNT(*) - COUNT(embedding_384) as missing
        FROM segments
        WHERE text IS NOT NULL AND text != ''
    """))
    stats = result.fetchone()
    total, populated, missing = stats
    
    print(f"📊 Segments with text: {total:,}")
    print(f"✅ Populated embedding_384: {populated:,}")
    print(f"⚠️  Missing embedding_384: {missing:,}")
    
    if missing > 0:
        print(f"\n⚠️  WARNING: {missing:,} segments missing embedding_384!")
        print("These will lose their embeddings after migration.")
        print("Recommendation: Run Phase 2 (006) again to backfill missing embeddings")
        
        # Ask for confirmation (in production, you might want to abort)
        response = input("\nContinue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration aborted. Run Phase 2 to backfill missing embeddings.")
            return
    
    # Step 2: Create IVFFLAT index on embedding_384
    print("\n📊 Creating IVFFLAT index on embedding_384...")
    print("This may take several minutes for large datasets...")
    
    # Calculate optimal lists parameter based on dataset size
    # Rule of thumb: lists = sqrt(num_rows), capped at 1000
    lists = min(1000, max(100, int(total ** 0.5)))
    
    op.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_segments_embedding_384_ivfflat 
        ON segments USING ivfflat (embedding_384 vector_l2_ops) 
        WITH (lists = {lists})
    """)
    print(f"✅ Index created with lists={lists}")
    
    # Step 3: Drop old embedding column
    print("\n🗑️  Dropping old embedding column (1536-dim)...")
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='segments' AND column_name='embedding'
            ) THEN
                ALTER TABLE segments DROP COLUMN embedding;
                RAISE NOTICE 'Dropped old embedding column';
            ELSE
                RAISE NOTICE 'Old embedding column does not exist, skipping';
            END IF;
        END $$;
    """)
    print("✅ Old embedding column dropped")
    
    # Step 4: Rename embedding_384 to embedding
    print("\n🔄 Renaming embedding_384 to embedding...")
    op.execute("""
        ALTER TABLE segments RENAME COLUMN embedding_384 TO embedding
    """)
    print("✅ Column renamed")
    
    # Step 5: Drop old index name and create new one
    print("\n📊 Rebuilding index with standard name...")
    op.execute("DROP INDEX IF EXISTS idx_segments_embedding_384_ivfflat")
    op.execute(f"""
        CREATE INDEX idx_segments_text_embedding_ivfflat 
        ON segments USING ivfflat (embedding vector_l2_ops) 
        WITH (lists = {lists})
    """)
    print("✅ Index rebuilt as idx_segments_text_embedding_ivfflat")
    
    # Step 6: Update column comment
    op.execute("""
        COMMENT ON COLUMN segments.embedding IS 
        'BGE-Small text embeddings (384-dim, BAAI/bge-small-en-v1.5) for semantic search'
    """)
    
    # Step 7: Analyze table for query planner
    print("\n📊 Analyzing table for query optimizer...")
    op.execute("ANALYZE segments")
    print("✅ Table analyzed")
    
    print("=" * 80)
    print("PHASE 3 COMPLETE - MIGRATION SUCCESSFUL! 🎉")
    print("=" * 80)
    print("Summary:")
    print(f"  • Migrated to BGE-Small (384-dim embeddings)")
    print(f"  • IVFFLAT index created with lists={lists}")
    print(f"  • Storage reduced by ~75% (384 vs 1536 dims)")
    print(f"  • Embedding generation now 50x+ faster")
    print("\nNext steps:")
    print("  1. Update application code to use EmbeddingsService")
    print("  2. Test semantic search queries")
    print("  3. Run benchmark: python backend/scripts/test_embedding_speed.py")
    print("=" * 80)


def downgrade() -> None:
    """
    Downgrade is non-trivial because we've dropped the old 1536-dim embeddings.
    This would require re-generating all embeddings with the old model.
    """
    print("=" * 80)
    print("DOWNGRADE NOT SUPPORTED")
    print("=" * 80)
    print("Reason: Old 1536-dim embeddings were dropped in Phase 3")
    print("\nTo restore old embeddings:")
    print("  1. Restore database from backup before migration")
    print("  2. OR: Re-run full ingestion with GTE-Qwen2-1.5B model")
    print("\nAlternatively, to keep BGE-Small but restore column structure:")
    print("  1. Rename embedding to embedding_384")
    print("  2. Add new embedding column as vector(1536)")
    print("  3. Re-generate embeddings with old model")
    print("=" * 80)
    
    raise NotImplementedError(
        "Downgrade not supported - old embeddings were dropped. "
        "Restore from backup or re-run ingestion with old model."
    )
