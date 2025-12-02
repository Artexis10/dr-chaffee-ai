"""Create segment_embeddings table for multi-model embedding storage

Revision ID: 021
Revises: 020
Create Date: 2025-12-02

This migration introduces a normalized embedding storage system that:
1. Supports multiple embedding models per segment
2. Enables rapid model switching without re-ingestion
3. Provides zero-downtime migration via dual-write strategy
4. Maintains backward compatibility with segments.embedding column

The segment_embeddings table stores embeddings separately from segments,
allowing concurrent storage of embeddings from different models (e.g.,
BGE-small-384, Nomic-768, GTE-Qwen2-1536) for the same segment.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text
import os
import json
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = '021'
down_revision = '020_rag_profiles_auto_select'
branch_labels = None
depends_on = None


def get_active_model_config():
    """Get active embedding model configuration from embedding_models.json"""
    # Try to load from config file
    config_paths = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'models', 'embedding_models.json'),
        '/app/config/models/embedding_models.json',  # Docker path
    ]
    
    for config_path in config_paths:
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                active_model_key = config.get('active_query_model', 'bge-small-en-v1.5')
                models = config.get('models', {})
                if active_model_key in models:
                    model = models[active_model_key]
                    return {
                        'model_key': active_model_key,
                        'dimensions': model.get('dimensions', 384)
                    }
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    
    # Fallback to environment variables
    dimensions = int(os.getenv('EMBEDDING_DIMENSIONS', '384'))
    model_key = os.getenv('EMBEDDING_MODEL_KEY', 'bge-small-en-v1.5')
    
    return {'model_key': model_key, 'dimensions': dimensions}


def upgrade() -> None:
    conn = op.get_bind()
    
    print("=" * 60)
    print("🔧 Migration 021: Creating segment_embeddings table")
    print("=" * 60)
    
    # Get active model configuration
    model_config = get_active_model_config()
    model_key = model_config['model_key']
    dimensions = model_config['dimensions']
    
    print(f"📋 Active model: {model_key} ({dimensions} dimensions)")
    
    # 1. Check if table already exists (for idempotency)
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'segment_embeddings'
        )
    """))
    table_exists = result.scalar()
    
    if table_exists:
        print("\n📦 segment_embeddings table already exists, checking structure...")
        # Verify required columns exist
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'segment_embeddings'
        """))
        existing_columns = {row[0] for row in result}
        required_columns = {'id', 'segment_id', 'model_key', 'dimensions', 'embedding', 'is_active'}
        
        if required_columns.issubset(existing_columns):
            print("   ✅ Table structure is valid")
        else:
            missing = required_columns - existing_columns
            print(f"   ⚠️  Missing columns: {missing}")
            print("   Dropping and recreating table...")
            conn.execute(text("DROP TABLE IF EXISTS segment_embeddings CASCADE"))
            table_exists = False
    
    if not table_exists:
        # Create segment_embeddings table
        # Schema design:
        # - UUID primary key for distributed systems compatibility
        # - segment_id FK with CASCADE delete for data integrity
        # - model_key to identify which embedding model was used
        # - dimensions stored for validation and index selection
        # - is_active flag for model switching without data deletion
        # - UNIQUE constraint prevents duplicate embeddings per segment/model
        print("\n📦 Creating segment_embeddings table...")
        conn.execute(text("""
            CREATE TABLE segment_embeddings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                segment_id INTEGER NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
                model_key TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                embedding VECTOR NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                UNIQUE (segment_id, model_key)
            )
        """))
        print("   ✅ Table created")
    
    # 2. Create indexes
    print("\n📊 Creating indexes...")
    
    # Index for model_key + is_active filtering
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_segment_embeddings_model_active 
        ON segment_embeddings(model_key, is_active) 
        WHERE is_active = TRUE
    """))
    print("   ✅ idx_segment_embeddings_model_active created")
    
    # Index for segment lookups
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_segment_embeddings_segment_id 
        ON segment_embeddings(segment_id)
    """))
    print("   ✅ idx_segment_embeddings_segment_id created")
    
    # 3. Backfill existing embeddings from segments.embedding
    # This is idempotent due to ON CONFLICT DO NOTHING
    print("\n📥 Backfilling embeddings from segments.embedding...")
    
    # Check if there are embeddings to migrate
    result = conn.execute(text("""
        SELECT COUNT(*) as count FROM segments WHERE embedding IS NOT NULL
    """))
    row = result.fetchone()
    total_embeddings = row[0] if row else 0
    
    # Check how many are already migrated
    result = conn.execute(text("""
        SELECT COUNT(*) as count FROM segment_embeddings WHERE model_key = :model_key
    """).bindparams(model_key=model_key))
    row = result.fetchone()
    already_migrated = row[0] if row else 0
    
    if already_migrated >= total_embeddings and total_embeddings > 0:
        print(f"   ℹ️  Already migrated: {already_migrated:,} embeddings (skipping backfill)")
    elif total_embeddings > 0:
        print(f"   Found {total_embeddings:,} embeddings to migrate ({already_migrated:,} already done)")
        
        # Get current embedding dimensions from database
        result = conn.execute(text("""
            SELECT vector_dims(embedding) as dims
            FROM segments
            WHERE embedding IS NOT NULL
            LIMIT 1
        """))
        row = result.fetchone()
        db_dimensions = row[0] if row else dimensions
        
        print(f"   Database embedding dimensions: {db_dimensions}")
        
        # Batch insert to avoid memory issues
        # ON CONFLICT DO NOTHING makes this idempotent for partial runs
        batch_size = 10000
        offset = 0
        migrated = 0
        
        while offset < total_embeddings:
            conn.execute(text("""
                INSERT INTO segment_embeddings (segment_id, model_key, dimensions, embedding, is_active)
                SELECT 
                    id,
                    :model_key,
                    :dimensions,
                    embedding,
                    TRUE
                FROM segments
                WHERE embedding IS NOT NULL
                ORDER BY id
                LIMIT :batch_size OFFSET :offset
                ON CONFLICT (segment_id, model_key) DO NOTHING
            """).bindparams(
                model_key=model_key,
                dimensions=db_dimensions,
                batch_size=batch_size,
                offset=offset
            ))
            
            migrated += batch_size
            offset += batch_size
            print(f"   Migrated {min(migrated, total_embeddings):,}/{total_embeddings:,} embeddings...")
        
        print(f"   ✅ Backfill complete: {total_embeddings:,} embeddings migrated")
    else:
        print("   ℹ️  No existing embeddings to migrate")
    
    # 4. Create per-model vector index for the active model
    # Note: ivfflat indexes require fixed-dimension columns, but we use VECTOR (no dims)
    # to support multiple models. Skip index creation here - search still works without it.
    # For production performance, create a typed index manually after migration.
    print(f"\n🔍 Attempting vector index for {model_key}...")
    
    try:
        # Calculate optimal lists parameter based on row count
        result = conn.execute(text("""
            SELECT COUNT(*) FROM segment_embeddings WHERE model_key = :model_key
        """).bindparams(model_key=model_key))
        row = result.fetchone()
        embedding_count = row[0] if row else 0
        
        # ivfflat lists should be sqrt(n) for optimal performance
        # Minimum 10, maximum 1000
        if embedding_count > 0:
            import math
            lists = max(10, min(1000, int(math.sqrt(embedding_count))))
        else:
            lists = 100  # Default for empty table
        
        print(f"   Using lists={lists} for {embedding_count:,} embeddings")
        
        # Create the index with a sanitized name
        safe_model_key = model_key.replace('-', '_').replace('.', '_')
        index_name = f"idx_se_vector_{safe_model_key}"
        
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON segment_embeddings USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = {lists})
            WHERE model_key = :model_key AND is_active = TRUE
        """).bindparams(model_key=model_key))
        print(f"   ✅ Vector index {index_name} created")
    except Exception as e:
        # IVFFlat requires fixed dimensions, which we don't have with VECTOR type
        # This is expected - search will use sequential scan (slower but works)
        print(f"   ⚠️  Vector index skipped: {type(e).__name__}")
        print(f"      Reason: IVFFlat requires fixed-dimension column")
        print(f"      Search will work but may be slower without index")
    
    # 5. Add comment for documentation
    conn.execute(text("""
        COMMENT ON TABLE segment_embeddings IS 
        'Normalized storage for embeddings from multiple models. Supports rapid model switching and concurrent multi-model storage.'
    """))
    
    print("\n" + "=" * 60)
    print("✅ Migration 021 complete!")
    print("=" * 60)
    print(f"   • segment_embeddings table created")
    print(f"   • {total_embeddings:,} embeddings backfilled")
    print(f"   • Legacy segments.embedding preserved for fallback")
    print("=" * 60)


def downgrade() -> None:
    conn = op.get_bind()
    
    print("🔄 Rolling back migration 021...")
    
    # Drop all indexes first
    conn.execute(text("DROP INDEX IF EXISTS idx_segment_embeddings_model_active"))
    conn.execute(text("DROP INDEX IF EXISTS idx_segment_embeddings_segment_id"))
    
    # Drop any model-specific vector indexes
    result = conn.execute(text("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename = 'segment_embeddings' 
        AND indexname LIKE 'idx_se_vector_%'
    """))
    for row in result:
        conn.execute(text(f"DROP INDEX IF EXISTS {row[0]}"))
    
    # Drop the table
    conn.execute(text("DROP TABLE IF EXISTS segment_embeddings CASCADE"))
    
    print("   ✅ segment_embeddings table dropped")
