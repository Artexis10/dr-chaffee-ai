"""
Embedding Storage Initialization Module
=======================================

This module handles the creation and validation of embedding storage tables
for the table-per-dimension architecture.

BEHAVIOR BY ENVIRONMENT:

Production (ENV=production or ENV=prod):
- If table missing → raise EmbeddingStorageError (hard failure)
- No auto-creation
- No auto-backfill
- Tables must be created via migrations

Development (ENV=dev or ENV=development or unset):
- If table missing AND AUTO_CREATE_EMBEDDING_TABLES=true → auto-create table + index
- If table missing AND AUTO_CREATE_EMBEDDING_TABLES=false → raise EmbeddingStorageError
- No auto-backfill (backfills must be triggered manually)

TABLE SCHEMA:
    segment_embeddings_{dim}:
        id              BIGSERIAL PRIMARY KEY
        segment_id      BIGINT NOT NULL REFERENCES segments(id) ON DELETE CASCADE
        model_key       TEXT NOT NULL
        embedding       VECTOR({dim}) NOT NULL
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        UNIQUE(segment_id, model_key)
    
    answer_cache_embeddings_{dim}:
        id              BIGSERIAL PRIMARY KEY
        answer_cache_id BIGINT NOT NULL REFERENCES answer_cache(id) ON DELETE CASCADE
        model_key       TEXT NOT NULL
        embedding       VECTOR({dim}) NOT NULL
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        UNIQUE(answer_cache_id, model_key)

INDEXES:
    - IVFFlat index on embedding column for ANN search
    - B-tree index on model_key for filtering

Usage:
    from backend.scripts.embedding_storage import ensure_storage_initialized
    
    # Will raise in production if table doesn't exist
    # Will auto-create in dev if AUTO_CREATE_EMBEDDING_TABLES=true
    ensure_storage_initialized("bge-small-en-v1.5")
"""

import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class EmbeddingStorageError(Exception):
    """Raised when embedding storage is not properly initialized."""
    pass


def is_production() -> bool:
    """Check if running in production environment."""
    env = os.getenv('ENV', os.getenv('ENVIRONMENT', 'development')).lower()
    return env in ('production', 'prod')


def auto_create_enabled() -> bool:
    """Check if auto-creation of embedding tables is enabled."""
    return os.getenv('AUTO_CREATE_EMBEDDING_TABLES', '').lower() in ('1', 'true', 'yes')


def table_exists(conn, table_name: str) -> bool:
    """
    Check if a table exists in the database.
    
    Args:
        conn: Database connection (psycopg2 or SQLAlchemy)
        table_name: Name of the table to check
        
    Returns:
        True if table exists, False otherwise
    """
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            )
        """, [table_name])
        result = cur.fetchone()
        return result[0] if result else False
    except Exception as e:
        logger.warning(f"Error checking if table {table_name} exists: {e}")
        return False


def create_segment_embedding_table(conn, table_name: str, dimensions: int) -> None:
    """
    Create a segment embeddings table with the specified dimensions.
    
    Args:
        conn: Database connection
        table_name: Name of the table to create (e.g., "segment_embeddings_384")
        dimensions: Vector dimensions (e.g., 384, 768, 1536)
    """
    logger.info(f"Creating segment embedding table: {table_name} (VECTOR({dimensions}))")
    
    cur = conn.cursor()
    
    # Create table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id BIGSERIAL PRIMARY KEY,
            segment_id BIGINT NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
            model_key TEXT NOT NULL,
            embedding VECTOR({dimensions}) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(segment_id, model_key)
        )
    """)
    
    # Create index on model_key
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_name}_model_key
        ON {table_name}(model_key)
    """)
    
    # Create index on segment_id
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_name}_segment_id
        ON {table_name}(segment_id)
    """)
    
    conn.commit()
    logger.info(f"✅ Created table {table_name}")


def create_answer_cache_embedding_table(conn, table_name: str, dimensions: int) -> None:
    """
    Create an answer cache embeddings table with the specified dimensions.
    
    Args:
        conn: Database connection
        table_name: Name of the table to create (e.g., "answer_cache_embeddings_384")
        dimensions: Vector dimensions (e.g., 384, 768, 1536)
    """
    logger.info(f"Creating answer cache embedding table: {table_name} (VECTOR({dimensions}))")
    
    cur = conn.cursor()
    
    # Create table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id BIGSERIAL PRIMARY KEY,
            answer_cache_id BIGINT NOT NULL REFERENCES answer_cache(id) ON DELETE CASCADE,
            model_key TEXT NOT NULL,
            embedding VECTOR({dimensions}) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(answer_cache_id, model_key)
        )
    """)
    
    # Create index on model_key
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_name}_model_key
        ON {table_name}(model_key)
    """)
    
    # Create index on answer_cache_id
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_name}_answer_cache_id
        ON {table_name}(answer_cache_id)
    """)
    
    conn.commit()
    logger.info(f"✅ Created table {table_name}")


def create_ivfflat_index(conn, table_name: str, dimensions: int, lists: int = 100) -> None:
    """
    Create an IVFFlat index on an embedding table.
    
    Args:
        conn: Database connection
        table_name: Name of the table
        dimensions: Vector dimensions (for documentation)
        lists: Number of IVFFlat lists (default: 100)
    """
    index_name = f"idx_{table_name}_ivfflat"
    logger.info(f"Creating IVFFlat index: {index_name} (lists={lists})")
    
    cur = conn.cursor()
    
    # Check if index already exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM pg_indexes 
            WHERE indexname = %s
        )
    """, [index_name])
    
    if cur.fetchone()[0]:
        logger.info(f"Index {index_name} already exists, skipping")
        return
    
    # Create IVFFlat index
    # Using vector_cosine_ops for cosine similarity (most common for embeddings)
    cur.execute(f"""
        CREATE INDEX {index_name}
        ON {table_name}
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = {lists})
    """)
    
    conn.commit()
    logger.info(f"✅ Created IVFFlat index {index_name}")


def ensure_storage_initialized(model_key: str, conn=None) -> Tuple[str, str]:
    """
    Ensure embedding storage tables exist for a model.
    
    This is the main entry point for storage initialization. It checks if
    the required tables exist and creates them if allowed by the environment.
    
    Args:
        model_key: The embedding model key (e.g., "bge-small-en-v1.5")
        conn: Optional database connection. If not provided, will attempt to get one.
        
    Returns:
        Tuple of (segment_table, answer_cache_table) names
        
    Raises:
        EmbeddingStorageError: If tables don't exist and can't be created
        ValueError: If model_key is unknown
    """
    # Import here to avoid circular imports
    try:
        from backend.api.embedding_config import resolve_embedding_model_config
    except ImportError:
        from api.embedding_config import resolve_embedding_model_config
    
    cfg = resolve_embedding_model_config(model_key)
    segment_table = cfg.segment_table
    answer_cache_table = cfg.answer_cache_table
    dimensions = cfg.dimensions
    
    # Get connection if not provided
    close_conn = False
    if conn is None:
        try:
            from backend.api.main import get_db_connection
        except ImportError:
            from api.main import get_db_connection
        conn = get_db_connection()
        close_conn = True
    
    try:
        # Check segment table
        segment_exists = table_exists(conn, segment_table)
        answer_cache_exists = table_exists(conn, answer_cache_table)
        
        if segment_exists and answer_cache_exists:
            logger.debug(f"Storage tables exist for {model_key}: {segment_table}, {answer_cache_table}")
            return (segment_table, answer_cache_table)
        
        # Tables missing - behavior depends on environment
        if is_production():
            missing = []
            if not segment_exists:
                missing.append(segment_table)
            if not answer_cache_exists:
                missing.append(answer_cache_table)
            
            raise EmbeddingStorageError(
                f"PRODUCTION ERROR: Embedding tables missing for model '{model_key}': {missing}. "
                f"Tables must be created via migration. "
                f"Run: alembic upgrade head"
            )
        
        # Development mode
        if not auto_create_enabled():
            missing = []
            if not segment_exists:
                missing.append(segment_table)
            if not answer_cache_exists:
                missing.append(answer_cache_table)
            
            raise EmbeddingStorageError(
                f"Embedding tables missing for model '{model_key}': {missing}. "
                f"Set AUTO_CREATE_EMBEDDING_TABLES=true to auto-create in development, "
                f"or run migrations: alembic upgrade head"
            )
        
        # Auto-create in development
        logger.info(f"Auto-creating embedding tables for {model_key} (dev mode)")
        
        if not segment_exists:
            create_segment_embedding_table(conn, segment_table, dimensions)
            create_ivfflat_index(conn, segment_table, dimensions)
        
        if not answer_cache_exists:
            create_answer_cache_embedding_table(conn, answer_cache_table, dimensions)
            create_ivfflat_index(conn, answer_cache_table, dimensions)
        
        return (segment_table, answer_cache_table)
        
    finally:
        if close_conn:
            conn.close()


def get_table_row_count(conn, table_name: str) -> int:
    """
    Get the number of rows in a table.
    
    Args:
        conn: Database connection
        table_name: Name of the table
        
    Returns:
        Number of rows in the table
    """
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        result = cur.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logger.warning(f"Error getting row count for {table_name}: {e}")
        return 0


def get_storage_status(conn, model_key: str) -> dict:
    """
    Get storage status for a model.
    
    Args:
        conn: Database connection
        model_key: The embedding model key
        
    Returns:
        Dict with storage status information
    """
    try:
        from backend.api.embedding_config import resolve_embedding_model_config
    except ImportError:
        from api.embedding_config import resolve_embedding_model_config
    
    cfg = resolve_embedding_model_config(model_key)
    
    segment_exists = table_exists(conn, cfg.segment_table)
    answer_cache_exists = table_exists(conn, cfg.answer_cache_table)
    
    return {
        'model_key': model_key,
        'dimensions': cfg.dimensions,
        'segment_table': cfg.segment_table,
        'segment_table_exists': segment_exists,
        'segment_row_count': get_table_row_count(conn, cfg.segment_table) if segment_exists else 0,
        'answer_cache_table': cfg.answer_cache_table,
        'answer_cache_table_exists': answer_cache_exists,
        'answer_cache_row_count': get_table_row_count(conn, cfg.answer_cache_table) if answer_cache_exists else 0,
        'paid': cfg.paid,
        'auto_backfill': cfg.auto_backfill,
    }
