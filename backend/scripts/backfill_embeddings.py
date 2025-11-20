#!/usr/bin/env python3
"""
Backfill embeddings for existing segments that don't have embeddings.
This script processes segments in batches and generates embeddings for them.
"""

import os
import sys
import logging
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Add paths for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(__file__), 'common'))

from scripts.common.embeddings import EmbeddingGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backfill_embeddings(batch_size=1024, limit=None):
    """
    Backfill embeddings for segments without embeddings.
    
    Args:
        batch_size: Number of segments to process per batch
        limit: Maximum number of segments to process (None = all)
    """
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable required")
    
    # Initialize embedding generator
    logger.info("Initializing embedding generator...")
    embedder = EmbeddingGenerator()
    logger.info(f"Embedding model: {embedder.model_name}, dimensions: {embedder.embedding_dimensions}")
    
    # Connect to database
    conn = psycopg2.connect(db_url)
    
    try:
        # Count segments without embeddings
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM segments WHERE embedding IS NULL")
            total_missing = cur.fetchone()[0]
            logger.info(f"Found {total_missing:,} segments without embeddings")
            
            if total_missing == 0:
                logger.info("✅ All segments already have embeddings!")
                return
            
            # Apply limit if specified
            process_count = min(total_missing, limit) if limit else total_missing
            logger.info(f"Will process {process_count:,} segments in batches of {batch_size}")
        
        # Process in batches
        processed = 0
        batch_num = 0
        
        while processed < process_count:
            batch_num += 1
            current_batch_size = min(batch_size, process_count - processed)
            
            logger.info(f"\n📦 Batch {batch_num}: Processing {current_batch_size} segments...")
            
            with conn.cursor() as cur:
                # Fetch batch of segments without embeddings
                cur.execute("""
                    SELECT id, text 
                    FROM segments 
                    WHERE embedding IS NULL 
                    LIMIT %s
                """, (current_batch_size,))
                
                rows = cur.fetchall()
                if not rows:
                    logger.info("No more segments to process")
                    break
                
                segment_ids = [row[0] for row in rows]
                texts = [row[1] for row in rows]
                
                logger.info(f"   Generating embeddings for {len(texts)} texts...")
                
                # Generate embeddings
                embeddings = embedder.generate_embeddings(texts)
                
                if not embeddings or len(embeddings) != len(texts):
                    logger.error(f"❌ Embedding generation failed or returned wrong count")
                    logger.error(f"   Expected: {len(texts)}, Got: {len(embeddings) if embeddings else 0}")
                    continue
                
                # Update database
                logger.info(f"   Updating database...")
                update_count = 0
                for segment_id, embedding in zip(segment_ids, embeddings):
                    try:
                        cur.execute("""
                            UPDATE segments 
                            SET embedding = %s 
                            WHERE id = %s
                        """, (embedding, segment_id))
                        update_count += 1
                    except Exception as e:
                        logger.error(f"   Failed to update segment {segment_id}: {e}")
                
                conn.commit()
                processed += update_count
                
                logger.info(f"   ✅ Updated {update_count} segments")
                logger.info(f"   Progress: {processed:,} / {process_count:,} ({processed/process_count*100:.1f}%)")
        
        logger.info(f"\n🎉 Backfill complete! Processed {processed:,} segments")
        
        # Final verification
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM segments WHERE embedding IS NULL")
            remaining = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM segments WHERE embedding IS NOT NULL")
            with_embeddings = cur.fetchone()[0]
            
            logger.info(f"\n📊 Final stats:")
            logger.info(f"   Segments with embeddings: {with_embeddings:,}")
            logger.info(f"   Segments without embeddings: {remaining:,}")
            
    except Exception as e:
        logger.error(f"❌ Backfill failed: {e}", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill embeddings for existing segments")
    parser.add_argument('--batch-size', type=int, default=1024,
                       help='Number of segments to process per batch (default: 1024)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Maximum number of segments to process (default: all)')
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting embedding backfill...")
    logger.info(f"   Batch size: {args.batch_size}")
    logger.info(f"   Limit: {args.limit if args.limit else 'None (process all)'}")
    
    backfill_embeddings(batch_size=args.batch_size, limit=args.limit)
