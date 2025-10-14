"""Backfill embedding_384 column with BGE-Small embeddings (Phase 2: Data Migration)

Revision ID: 006
Revises: 005
Create Date: 2025-10-13 22:05:00

This is Phase 2 of the BGE-Small migration:
- Backfills embedding_384 for all segments with NULL values
- Uses EmbeddingsService.encode_texts() with CUDA/FP16
- Processes in batches of 1,000 rows for resumability
- Retries failed batches up to 3 times with exponential backoff
- Safe to run multiple times (only processes NULL rows)

Performance expectations:
- ~1,000-2,000 texts/sec on RTX 5080 (bge-small + FP16)
- 100k segments: ~1-2 minutes
- 1M segments: ~10-20 minutes

After this migration:
- Run Phase 3 (007) to swap columns and rebuild index
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import os
import sys
import time
import logging

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade() -> None:
    """Backfill embedding_384 column in batches"""
    print("=" * 80)
    print("PHASE 2: Backfilling embedding_384 with BGE-Small embeddings")
    print("=" * 80)
    
    # Add backend/services to path for EmbeddingsService import
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    try:
        from services.embeddings_service import EmbeddingsService
        
        # Initialize service (loads models)
        logger.info("Initializing EmbeddingsService...")
        EmbeddingsService.init_from_env()
        logger.info(f"✅ EmbeddingsService initialized on {EmbeddingsService.get_device()}")
        
    except ImportError as e:
        logger.error(f"Failed to import EmbeddingsService: {e}")
        logger.error("Ensure sentence-transformers>=2.7.0 is installed")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize EmbeddingsService: {e}")
        raise
    
    # Get database connection from Alembic context
    connection = op.get_bind()
    
    # Configuration
    BATCH_SIZE = 1000  # Process 1k rows at a time
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    
    # Count total rows to process
    result = connection.execute(text("""
        SELECT COUNT(*) 
        FROM segments 
        WHERE embedding_384 IS NULL 
        AND text IS NOT NULL 
        AND text != ''
    """))
    total_rows = result.scalar()
    
    if total_rows == 0:
        print("✅ No rows to backfill (all embeddings already populated)")
        print("=" * 80)
        return
    
    print(f"📊 Found {total_rows:,} segments to backfill")
    print(f"📦 Batch size: {BATCH_SIZE:,} rows")
    print(f"⏱️  Estimated time: ~{total_rows / 1500 / 60:.1f} minutes (assuming 1,500 texts/sec)")
    print("=" * 80)
    
    processed = 0
    failed_batches = 0
    start_time = time.time()
    
    while True:
        # Fetch next batch of rows with NULL embedding_384
        result = connection.execute(text("""
            SELECT id, text 
            FROM segments 
            WHERE embedding_384 IS NULL 
            AND text IS NOT NULL 
            AND text != ''
            ORDER BY id 
            LIMIT :batch_size
        """), {"batch_size": BATCH_SIZE})
        
        rows = result.fetchall()
        
        if not rows:
            break  # No more rows to process
        
        # Extract IDs and texts
        ids = [row[0] for row in rows]
        texts = [row[1] for row in rows]
        
        # Generate embeddings with retry logic
        embeddings = None
        for attempt in range(MAX_RETRIES):
            try:
                embeddings = EmbeddingsService.encode_texts(texts, batch_size=256)
                break  # Success
            except Exception as e:
                logger.error(f"Batch failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                    
                    # Try to clear CUDA cache if available
                    try:
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    except:
                        pass
                else:
                    logger.error(f"Batch failed after {MAX_RETRIES} attempts, skipping")
                    failed_batches += 1
                    embeddings = None
        
        if embeddings is None or len(embeddings) != len(ids):
            logger.error(f"Skipping batch of {len(ids)} rows due to embedding failure")
            continue
        
        # Update database in transaction
        try:
            # Convert embeddings to list format for PostgreSQL
            for row_id, embedding in zip(ids, embeddings):
                embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
                connection.execute(text("""
                    UPDATE segments 
                    SET embedding_384 = :embedding::vector 
                    WHERE id = :id
                """), {"id": row_id, "embedding": str(embedding_list)})
            
            # Commit batch
            connection.execute(text("COMMIT"))
            
            processed += len(ids)
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            eta_seconds = (total_rows - processed) / rate if rate > 0 else 0
            
            print(f"✅ Processed {processed:,}/{total_rows:,} ({processed/total_rows*100:.1f}%) "
                  f"| Rate: {rate:.0f} texts/sec | ETA: {eta_seconds/60:.1f} min")
            
        except Exception as e:
            logger.error(f"Database update failed: {e}")
            connection.execute(text("ROLLBACK"))
            failed_batches += 1
    
    # Final summary
    elapsed = time.time() - start_time
    print("=" * 80)
    print("PHASE 2 COMPLETE")
    print(f"✅ Processed: {processed:,} segments")
    print(f"⏱️  Time: {elapsed/60:.1f} minutes")
    print(f"🚀 Throughput: {processed/elapsed:.0f} texts/sec")
    if failed_batches > 0:
        print(f"⚠️  Failed batches: {failed_batches}")
    print("Next: Run Phase 3 (007_swap_embedding_columns.py) to finalize migration")
    print("=" * 80)


def downgrade() -> None:
    """Clear embedding_384 column (set to NULL)"""
    print("Downgrading: Clearing embedding_384 column")
    
    connection = op.get_bind()
    
    # Count rows to clear
    result = connection.execute(text("""
        SELECT COUNT(*) 
        FROM segments 
        WHERE embedding_384 IS NOT NULL
    """))
    count = result.scalar()
    
    if count == 0:
        print("✅ No rows to clear (embedding_384 already NULL)")
        return
    
    print(f"Clearing {count:,} embedding_384 values...")
    
    # Clear in batches to avoid long locks
    BATCH_SIZE = 10000
    cleared = 0
    
    while True:
        result = connection.execute(text("""
            UPDATE segments 
            SET embedding_384 = NULL 
            WHERE id IN (
                SELECT id FROM segments 
                WHERE embedding_384 IS NOT NULL 
                LIMIT :batch_size
            )
        """), {"batch_size": BATCH_SIZE})
        
        rows_affected = result.rowcount
        if rows_affected == 0:
            break
        
        cleared += rows_affected
        connection.execute(text("COMMIT"))
        print(f"Cleared {cleared:,}/{count:,} rows...")
    
    print(f"✅ Downgrade complete ({cleared:,} rows cleared)")
