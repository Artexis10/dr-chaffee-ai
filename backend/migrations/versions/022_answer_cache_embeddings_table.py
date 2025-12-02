"""Create answer_cache_embeddings table for normalized answer cache embedding storage

Revision ID: 022
Revises: 021
Create Date: 2025-12-02

This migration creates the answer_cache_embeddings table that was referenced
in main.py but never created via migration. This table stores embeddings
for cached answers, enabling semantic similarity lookup across different
embedding models.

The table design mirrors segment_embeddings for consistency:
- One embedding per (answer_cache_id, model_key) pair
- Supports multiple embedding models
- Uses is_active flag for model switching
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
revision = '022'
down_revision = '021'
branch_labels = None
depends_on = None


def get_active_model_config():
    """Get active embedding model configuration from embedding_models.json"""
    config_paths = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'models', 'embedding_models.json'),
        '/app/config/models/embedding_models.json',
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
    
    dimensions = int(os.getenv('EMBEDDING_DIMENSIONS', '384'))
    model_key = os.getenv('EMBEDDING_MODEL_KEY', 'bge-small-en-v1.5')
    
    return {'model_key': model_key, 'dimensions': dimensions}


def upgrade() -> None:
    conn = op.get_bind()
    
    print("=" * 60)
    print("🔧 Migration 022: Creating answer_cache_embeddings table")
    print("=" * 60)
    
    model_config = get_active_model_config()
    model_key = model_config['model_key']
    dimensions = model_config['dimensions']
    
    print(f"📋 Active model: {model_key} ({dimensions} dimensions)")
    
    # Check if table already exists (may have been created manually)
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'answer_cache_embeddings'
        )
    """))
    table_exists = result.scalar()
    
    if table_exists:
        print("   ℹ️  Table already exists, checking structure...")
        
        # Verify required columns exist
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'answer_cache_embeddings'
        """))
        existing_columns = {row[0] for row in result}
        required_columns = {'id', 'answer_cache_id', 'model_key', 'embedding'}
        
        if required_columns.issubset(existing_columns):
            print("   ✅ Table structure is valid")
            
            # Add missing columns if needed
            if 'dimensions' not in existing_columns:
                conn.execute(text("""
                    ALTER TABLE answer_cache_embeddings 
                    ADD COLUMN IF NOT EXISTS dimensions INTEGER
                """))
                print("   ✅ Added dimensions column")
            
            if 'is_active' not in existing_columns:
                conn.execute(text("""
                    ALTER TABLE answer_cache_embeddings 
                    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE
                """))
                print("   ✅ Added is_active column")
            
            if 'created_at' not in existing_columns:
                conn.execute(text("""
                    ALTER TABLE answer_cache_embeddings 
                    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now()
                """))
                print("   ✅ Added created_at column")
        else:
            print(f"   ⚠️  Missing columns: {required_columns - existing_columns}")
            print("   Recreating table...")
            conn.execute(text("DROP TABLE IF EXISTS answer_cache_embeddings CASCADE"))
            table_exists = False
    
    if not table_exists:
        # Create answer_cache_embeddings table
        # Schema design mirrors segment_embeddings for consistency:
        # - UUID primary key for distributed systems compatibility
        # - answer_cache_id FK with CASCADE delete for data integrity
        # - model_key to identify which embedding model was used
        # - dimensions stored for validation and index selection
        # - is_active flag for model switching without data deletion
        # - UNIQUE constraint prevents duplicate embeddings per cache entry/model
        print("\n📦 Creating answer_cache_embeddings table...")
        conn.execute(text("""
            CREATE TABLE answer_cache_embeddings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                answer_cache_id INTEGER NOT NULL REFERENCES answer_cache(id) ON DELETE CASCADE,
                model_key TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                embedding VECTOR NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                UNIQUE (answer_cache_id, model_key)
            )
        """))
        print("   ✅ Table created")
    
    # Create indexes
    print("\n📊 Creating indexes...")
    
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_ace_model_active 
        ON answer_cache_embeddings(model_key, is_active) 
        WHERE is_active = TRUE
    """))
    print("   ✅ idx_ace_model_active created")
    
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_ace_answer_cache_id 
        ON answer_cache_embeddings(answer_cache_id)
    """))
    print("   ✅ idx_ace_answer_cache_id created")
    
    # Create vector index for the active model
    print(f"\n🔍 Creating vector index for {model_key}...")
    
    safe_model_key = model_key.replace('-', '_').replace('.', '_')
    index_name = f"idx_ace_vector_{safe_model_key}"
    
    conn.execute(text(f"""
        CREATE INDEX IF NOT EXISTS {index_name}
        ON answer_cache_embeddings USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50)
        WHERE model_key = :model_key AND is_active = TRUE
    """).bindparams(model_key=model_key))
    print(f"   ✅ Vector index {index_name} created")
    
    # Migrate existing embeddings from answer_cache if they exist
    print("\n📥 Checking for legacy embeddings in answer_cache...")
    
    # Check if answer_cache has embedding columns
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'answer_cache' AND column_name LIKE 'query_embedding_%'
    """))
    legacy_columns = [row[0] for row in result]
    
    if legacy_columns:
        print(f"   Found legacy columns: {legacy_columns}")
        
        # Migrate from the appropriate column based on dimensions
        dim_to_column = {
            384: 'query_embedding_384',
            768: 'query_embedding_768',
            1536: 'query_embedding_1536'
        }
        
        source_column = dim_to_column.get(dimensions)
        if source_column and source_column in legacy_columns:
            result = conn.execute(text(f"""
                SELECT COUNT(*) FROM answer_cache WHERE {source_column} IS NOT NULL
            """))
            count = result.scalar()
            
            if count > 0:
                print(f"   Migrating {count} embeddings from {source_column}...")
                conn.execute(text(f"""
                    INSERT INTO answer_cache_embeddings (answer_cache_id, model_key, dimensions, embedding, is_active)
                    SELECT 
                        id,
                        :model_key,
                        :dimensions,
                        {source_column},
                        TRUE
                    FROM answer_cache
                    WHERE {source_column} IS NOT NULL
                    ON CONFLICT (answer_cache_id, model_key) DO NOTHING
                """).bindparams(model_key=model_key, dimensions=dimensions))
                print(f"   ✅ Migrated {count} embeddings")
        else:
            print(f"   ℹ️  No matching legacy column for {dimensions} dimensions")
    else:
        print("   ℹ️  No legacy embedding columns found")
    
    # Add comment
    conn.execute(text("""
        COMMENT ON TABLE answer_cache_embeddings IS 
        'Normalized storage for answer cache embeddings. Supports multiple embedding models for semantic cache lookup.'
    """))
    
    print("\n" + "=" * 60)
    print("✅ Migration 022 complete!")
    print("=" * 60)


def downgrade() -> None:
    conn = op.get_bind()
    
    print("🔄 Rolling back migration 022...")
    
    # Drop indexes
    conn.execute(text("DROP INDEX IF EXISTS idx_ace_model_active"))
    conn.execute(text("DROP INDEX IF EXISTS idx_ace_answer_cache_id"))
    
    # Drop model-specific vector indexes
    result = conn.execute(text("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename = 'answer_cache_embeddings' 
        AND indexname LIKE 'idx_ace_vector_%'
    """))
    for row in result:
        conn.execute(text(f"DROP INDEX IF EXISTS {row[0]}"))
    
    # Drop the table
    conn.execute(text("DROP TABLE IF EXISTS answer_cache_embeddings CASCADE"))
    
    print("   ✅ answer_cache_embeddings table dropped")
