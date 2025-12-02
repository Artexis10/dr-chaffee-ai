"""Create answer_cache_embeddings_384 table for BGE-small answer cache embeddings

Revision ID: 022
Revises: 021
Create Date: 2025-12-02

TABLE-PER-DIMENSION ARCHITECTURE:
This migration creates the answer_cache_embeddings_384 table for BGE-small-en-v1.5
embeddings (384 dimensions). Mirrors the segment_embeddings_384 pattern.

This migration also creates a compatibility view 'answer_cache_embeddings' that
points to answer_cache_embeddings_384 for backward compatibility with existing code.
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
revision = '022'
down_revision = '021'
branch_labels = None
depends_on = None

# Fixed configuration for this migration
TABLE_NAME = 'answer_cache_embeddings_384'
DIMENSIONS = 384
MODEL_KEY = 'bge-small-en-v1.5'


def upgrade() -> None:
    conn = op.get_bind()
    
    print("=" * 60)
    print("🔧 Migration 022: Creating answer_cache_embeddings_384 table")
    print("=" * 60)
    print(f"📋 Table: {TABLE_NAME} (VECTOR({DIMENSIONS}))")
    print(f"📋 Model: {MODEL_KEY}")
    
    # 1. Check if table already exists
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
        required_columns = {'id', 'answer_cache_id', 'model_key', 'embedding', 'created_at'}
        
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
                answer_cache_id BIGINT NOT NULL REFERENCES answer_cache(id) ON DELETE CASCADE,
                model_key TEXT NOT NULL,
                embedding VECTOR({DIMENSIONS}) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(answer_cache_id, model_key)
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
        CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_answer_cache_id
        ON {TABLE_NAME}(answer_cache_id)
    """))
    print(f"   ✅ idx_{TABLE_NAME}_answer_cache_id created")
    
    # 3. Migrate existing embeddings from answer_cache legacy columns
    print("\n📥 Checking for legacy embeddings in answer_cache...")
    
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'answer_cache' AND column_name LIKE 'query_embedding_%'
    """))
    legacy_columns = [row[0] for row in result]
    
    if 'query_embedding_384' in legacy_columns:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM answer_cache WHERE query_embedding_384 IS NOT NULL
        """))
        count = result.scalar() or 0
        
        if count > 0:
            print(f"   Migrating {count} embeddings from query_embedding_384...")
            conn.execute(text(f"""
                INSERT INTO {TABLE_NAME} (answer_cache_id, model_key, embedding)
                SELECT id, :model_key, query_embedding_384
                FROM answer_cache
                WHERE query_embedding_384 IS NOT NULL
                ON CONFLICT (answer_cache_id, model_key) DO NOTHING
            """).bindparams(model_key=MODEL_KEY))
            print(f"   ✅ Migrated {count} embeddings")
        else:
            print("   ℹ️  No legacy embeddings to migrate")
    else:
        print("   ℹ️  No query_embedding_384 column found")
    
    # 4. Create IVFFlat index
    print(f"\n🔍 Creating IVFFlat vector index...")
    
    result = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}"))
    row = result.fetchone()
    embedding_count = row[0] if row else 0
    
    lists = max(10, min(100, int(math.sqrt(embedding_count)))) if embedding_count > 0 else 50
    print(f"   Embedding count: {embedding_count:,}, lists={lists}")
    
    conn.execute(text(f"""
        CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_ivfflat
        ON {TABLE_NAME} USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = {lists})
    """))
    print(f"   ✅ IVFFlat index created")
    
    # 5. Create compatibility view
    print("\n📋 Creating compatibility view...")
    conn.execute(text("DROP VIEW IF EXISTS answer_cache_embeddings CASCADE"))
    conn.execute(text(f"""
        CREATE VIEW answer_cache_embeddings AS
        SELECT 
            id,
            answer_cache_id,
            model_key,
            {DIMENSIONS} as dimensions,
            embedding,
            created_at,
            TRUE as is_active
        FROM {TABLE_NAME}
    """))
    print("   ✅ answer_cache_embeddings view created")
    
    # 6. Add comment
    conn.execute(text(f"""
        COMMENT ON TABLE {TABLE_NAME} IS 
        'Answer cache embeddings for 384-dimension models (BGE-small-en-v1.5). Part of table-per-dimension architecture.'
    """))
    
    print("\n" + "=" * 60)
    print("✅ Migration 022 complete!")
    print("=" * 60)
    print(f"   • {TABLE_NAME} with VECTOR({DIMENSIONS})")
    print(f"   • IVFFlat index (lists={lists})")
    print(f"   • answer_cache_embeddings compatibility view")
    print("=" * 60)


def downgrade() -> None:
    conn = op.get_bind()
    
    print("🔄 Rolling back migration 022...")
    
    # Drop compatibility view
    conn.execute(text("DROP VIEW IF EXISTS answer_cache_embeddings CASCADE"))
    
    # Drop indexes
    conn.execute(text(f"DROP INDEX IF EXISTS idx_{TABLE_NAME}_model_key"))
    conn.execute(text(f"DROP INDEX IF EXISTS idx_{TABLE_NAME}_answer_cache_id"))
    conn.execute(text(f"DROP INDEX IF EXISTS idx_{TABLE_NAME}_ivfflat"))
    
    # Drop table
    conn.execute(text(f"DROP TABLE IF EXISTS {TABLE_NAME} CASCADE"))
    
    print(f"   ✅ {TABLE_NAME} dropped")
