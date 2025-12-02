"""Create segment_embeddings_384 table for BGE-small embeddings

Revision ID: 021
Revises: 020
Create Date: 2025-12-02

TABLE-PER-DIMENSION ARCHITECTURE:
This migration creates the segment_embeddings_384 table for BGE-small-en-v1.5
embeddings (384 dimensions). Each embedding dimension gets its own table:
- segment_embeddings_384 (this migration)
- segment_embeddings_768 (created on-demand for Nomic)
- segment_embeddings_1024 (created on-demand for BGE-large)
- segment_embeddings_1536 (created on-demand for GTE-Qwen2, OpenAI-small)
- segment_embeddings_3072 (created on-demand for OpenAI-large)

WHY TABLE-PER-DIMENSION:
- IVFFlat indexes require fixed-dimension VECTOR(N) columns
- Each table has its own optimized index
- No dimension mismatch errors at query time
- Clean separation between models

This migration also creates a compatibility view 'segment_embeddings' that
points to segment_embeddings_384 for backward compatibility with existing code.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import os
import json
import logging
import math

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = '021'
down_revision = '020_rag_profiles_auto_select'
branch_labels = None
depends_on = None

# Fixed configuration for this migration
TABLE_NAME = 'segment_embeddings_384'
DIMENSIONS = 384
MODEL_KEY = 'bge-small-en-v1.5'


def upgrade() -> None:
    conn = op.get_bind()
    
    print("=" * 60)
    print("🔧 Migration 021: Creating segment_embeddings_384 table")
    print("=" * 60)
    print(f"📋 Table: {TABLE_NAME} (VECTOR({DIMENSIONS}))")
    print(f"📋 Model: {MODEL_KEY}")
    
    # 1. Check if table already exists (for idempotency)
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = :table_name
        )
    """).bindparams(table_name=TABLE_NAME))
    table_exists = result.scalar()
    
    if table_exists:
        print(f"\n📦 {TABLE_NAME} already exists, verifying structure...")
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = :table_name
        """).bindparams(table_name=TABLE_NAME))
        existing_columns = {row[0] for row in result}
        required_columns = {'id', 'segment_id', 'model_key', 'embedding', 'created_at'}
        
        if required_columns.issubset(existing_columns):
            print("   ✅ Table structure is valid")
        else:
            missing = required_columns - existing_columns
            print(f"   ⚠️  Missing columns: {missing}")
            print("   Dropping and recreating table...")
            conn.execute(text(f"DROP TABLE IF EXISTS {TABLE_NAME} CASCADE"))
            table_exists = False
    
    if not table_exists:
        print(f"\n📦 Creating {TABLE_NAME}...")
        conn.execute(text(f"""
            CREATE TABLE {TABLE_NAME} (
                id BIGSERIAL PRIMARY KEY,
                segment_id BIGINT NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
                model_key TEXT NOT NULL,
                embedding VECTOR({DIMENSIONS}) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(segment_id, model_key)
            )
        """))
        print("   ✅ Table created")
    
    # 2. Create indexes
    print("\n📊 Creating indexes...")
    
    conn.execute(text(f"""
        CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_model_key
        ON {TABLE_NAME}(model_key)
    """))
    print(f"   ✅ idx_{TABLE_NAME}_model_key created")
    
    conn.execute(text(f"""
        CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_segment_id
        ON {TABLE_NAME}(segment_id)
    """))
    print(f"   ✅ idx_{TABLE_NAME}_segment_id created")
    
    # 3. Backfill existing embeddings from segments.embedding
    print("\n📥 Backfilling embeddings from segments.embedding...")
    
    result = conn.execute(text("""
        SELECT COUNT(*) FROM segments WHERE embedding IS NOT NULL
    """))
    row = result.fetchone()
    total_embeddings = row[0] if row else 0
    
    result = conn.execute(text(f"""
        SELECT COUNT(*) FROM {TABLE_NAME} WHERE model_key = :model_key
    """).bindparams(model_key=MODEL_KEY))
    row = result.fetchone()
    already_migrated = row[0] if row else 0
    
    if already_migrated >= total_embeddings and total_embeddings > 0:
        print(f"   ℹ️  Already migrated: {already_migrated:,} embeddings")
    elif total_embeddings > 0:
        print(f"   Found {total_embeddings:,} embeddings to migrate")
        
        # Verify dimensions match
        result = conn.execute(text("""
            SELECT vector_dims(embedding) FROM segments WHERE embedding IS NOT NULL LIMIT 1
        """))
        row = result.fetchone()
        db_dims = row[0] if row else DIMENSIONS
        
        if db_dims != DIMENSIONS:
            print(f"   ⚠️  WARNING: Database has {db_dims}-dim vectors, table expects {DIMENSIONS}")
            print(f"   Skipping backfill - dimension mismatch")
        else:
            batch_size = 10000
            offset = 0
            
            while offset < total_embeddings:
                conn.execute(text(f"""
                    INSERT INTO {TABLE_NAME} (segment_id, model_key, embedding)
                    SELECT id, :model_key, embedding
                    FROM segments
                    WHERE embedding IS NOT NULL
                    ORDER BY id
                    LIMIT :batch_size OFFSET :offset
                    ON CONFLICT (segment_id, model_key) DO NOTHING
                """).bindparams(model_key=MODEL_KEY, batch_size=batch_size, offset=offset))
                
                offset += batch_size
                print(f"   Migrated {min(offset, total_embeddings):,}/{total_embeddings:,}...")
            
            print(f"   ✅ Backfill complete")
    else:
        print("   ℹ️  No existing embeddings to migrate")
    
    # 4. Create IVFFlat index
    print(f"\n🔍 Creating IVFFlat vector index...")
    
    result = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}"))
    row = result.fetchone()
    embedding_count = row[0] if row else 0
    
    lists = max(10, min(1000, int(math.sqrt(embedding_count)))) if embedding_count > 0 else 100
    print(f"   Embedding count: {embedding_count:,}, lists={lists}")
    
    conn.execute(text(f"""
        CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_ivfflat
        ON {TABLE_NAME} USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = {lists})
    """))
    print(f"   ✅ IVFFlat index created")
    
    # 5. Create compatibility view for existing code
    print("\n📋 Creating compatibility view...")
    conn.execute(text("DROP VIEW IF EXISTS segment_embeddings CASCADE"))
    conn.execute(text(f"""
        CREATE VIEW segment_embeddings AS
        SELECT 
            id,
            segment_id,
            model_key,
            {DIMENSIONS} as dimensions,
            embedding,
            created_at,
            TRUE as is_active
        FROM {TABLE_NAME}
    """))
    print("   ✅ segment_embeddings view created (points to segment_embeddings_384)")
    
    # 6. Add comment
    conn.execute(text(f"""
        COMMENT ON TABLE {TABLE_NAME} IS 
        'Segment embeddings for 384-dimension models (BGE-small-en-v1.5). Part of table-per-dimension architecture.'
    """))
    
    print("\n" + "=" * 60)
    print("✅ Migration 021 complete!")
    print("=" * 60)
    print(f"   • {TABLE_NAME} with VECTOR({DIMENSIONS})")
    print(f"   • {total_embeddings:,} embeddings backfilled")
    print(f"   • IVFFlat index (lists={lists})")
    print(f"   • segment_embeddings compatibility view")
    print("=" * 60)


def downgrade() -> None:
    conn = op.get_bind()
    
    print("🔄 Rolling back migration 021...")
    
    # Drop compatibility view
    conn.execute(text("DROP VIEW IF EXISTS segment_embeddings CASCADE"))
    
    # Drop indexes
    conn.execute(text(f"DROP INDEX IF EXISTS idx_{TABLE_NAME}_model_key"))
    conn.execute(text(f"DROP INDEX IF EXISTS idx_{TABLE_NAME}_segment_id"))
    conn.execute(text(f"DROP INDEX IF EXISTS idx_{TABLE_NAME}_ivfflat"))
    
    # Drop table
    conn.execute(text(f"DROP TABLE IF EXISTS {TABLE_NAME} CASCADE"))
    
    print(f"   ✅ {TABLE_NAME} dropped")
