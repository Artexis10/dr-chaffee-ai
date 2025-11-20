#!/usr/bin/env python3
"""
Parallel backfill embeddings for existing segments.
Maximizes GPU utilization by batching embeddings and database writes.
"""

import os
import sys
import logging
import psycopg2
from psycopg2.extras import execute_batch
import time
from pathlib import Path
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

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


class ParallelEmbeddingBackfill:
    def __init__(self, batch_size=1024, mega_batch_size=10240, num_workers=4):
        """
        Args:
            batch_size: Segments per embedding batch (GPU batch)
            mega_batch_size: Total segments to process before DB commit
            num_workers: Number of parallel embedding workers
        """
        self.batch_size = batch_size
        self.mega_batch_size = mega_batch_size
        self.num_workers = num_workers
        self.db_url = os.getenv('DATABASE_URL')
        self.embedder = EmbeddingGenerator()
        self.stats_lock = Lock()
        self.total_processed = 0
        self.total_failed = 0
        
    def backfill(self, limit=None):
        """Backfill embeddings with parallel processing"""
        
        conn = psycopg2.connect(self.db_url)
        
        try:
            # Count segments without embeddings
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM segments WHERE embedding IS NULL")
                total_missing = cur.fetchone()[0]
                logger.info(f"Found {total_missing:,} segments without embeddings")
                
                if total_missing == 0:
                    logger.info("✅ All segments already have embeddings!")
                    return
                
                process_count = min(total_missing, limit) if limit else total_missing
                logger.info(f"Will process {process_count:,} segments")
                logger.info(f"  Batch size: {self.batch_size} (GPU)")
                logger.info(f"  Mega batch: {self.mega_batch_size} (DB commit)")
                logger.info(f"  Workers: {self.num_workers} (parallel)")
            
            # Process in mega-batches
            processed = 0
            mega_batch_num = 0
            
            while processed < process_count:
                mega_batch_num += 1
                current_mega_size = min(self.mega_batch_size, process_count - processed)
                
                logger.info(f"\n🚀 Mega-batch {mega_batch_num}: {current_mega_size:,} segments")
                start_time = time.time()
                
                # Fetch all segments for this mega-batch
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, text 
                        FROM segments 
                        WHERE embedding IS NULL 
                        LIMIT %s
                    """, (current_mega_size,))
                    
                    rows = cur.fetchall()
                    if not rows:
                        logger.info("No more segments to process")
                        break
                
                segment_ids = [row[0] for row in rows]
                texts = [row[1] for row in rows]
                
                logger.info(f"   📥 Fetched {len(texts)} segments")
                
                # Process in parallel batches
                embeddings_map = {}  # seg_id -> embedding
                
                with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                    futures = {}
                    
                    # Submit all embedding jobs
                    for i in range(0, len(texts), self.batch_size):
                        batch_texts = texts[i:i+self.batch_size]
                        batch_ids = segment_ids[i:i+self.batch_size]
                        batch_num = i // self.batch_size + 1
                        
                        future = executor.submit(
                            self._process_embedding_batch,
                            batch_ids, batch_texts, batch_num
                        )
                        futures[future] = (batch_ids, batch_texts)
                    
                    # Collect results
                    for future in as_completed(futures):
                        try:
                            batch_embeddings = future.result()
                            embeddings_map.update(batch_embeddings)
                        except Exception as e:
                            logger.error(f"❌ Batch processing failed: {e}")
                
                # Write all embeddings to DB in one transaction
                logger.info(f"   💾 Writing {len(embeddings_map)} embeddings to database...")
                self._write_embeddings_batch(conn, embeddings_map)
                
                processed += len(embeddings_map)
                mega_elapsed = time.time() - start_time
                
                logger.info(f"   ✅ Mega-batch complete: {len(embeddings_map)} embeddings")
                logger.info(f"   ⏱️  Time: {mega_elapsed:.1f}s ({len(embeddings_map)/mega_elapsed:.0f} seg/s)")
                logger.info(f"   📊 Progress: {processed:,} / {process_count:,} ({processed/process_count*100:.1f}%)")
            
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
    
    def _process_embedding_batch(self, segment_ids, texts, batch_num):
        """Process a batch of texts and return {seg_id: embedding} map"""
        try:
            logger.info(f"   🔄 Batch {batch_num}: Generating {len(texts)} embeddings...")
            embeddings = self.embedder.generate_embeddings(texts)
            
            if not embeddings or len(embeddings) != len(texts):
                logger.error(f"   ❌ Batch {batch_num}: Embedding count mismatch")
                return {}
            
            result = dict(zip(segment_ids, embeddings))
            logger.info(f"   ✅ Batch {batch_num}: Generated {len(result)} embeddings")
            return result
            
        except Exception as e:
            logger.error(f"   ❌ Batch {batch_num} failed: {e}")
            return {}
    
    def _write_embeddings_batch(self, conn, embeddings_map):
        """Write all embeddings using temp table + JOIN (10-100x faster than individual UPDATEs)"""
        try:
            with conn.cursor() as cur:
                # Create temp table with embeddings
                cur.execute("""
                    CREATE TEMP TABLE temp_embeddings (
                        id INTEGER,
                        embedding vector(384)
                    ) ON COMMIT DROP
                """)
                
                # Bulk insert into temp table
                data = [(seg_id, embedding) for seg_id, embedding in embeddings_map.items()]
                
                execute_batch(cur, """
                    INSERT INTO temp_embeddings (id, embedding) 
                    VALUES (%s, %s)
                """, data, page_size=5000)
                
                # Single UPDATE using JOIN
                cur.execute("""
                    UPDATE segments s
                    SET embedding = t.embedding
                    FROM temp_embeddings t
                    WHERE s.id = t.id
                """)
            
            conn.commit()
            with self.stats_lock:
                self.total_processed += len(embeddings_map)
                
        except Exception as e:
            logger.error(f"❌ Database write failed: {e}")
            conn.rollback()
            with self.stats_lock:
                self.total_failed += len(embeddings_map)
            raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Parallel backfill embeddings")
    parser.add_argument('--batch-size', type=int, default=1024,
                       help='GPU batch size (default: 1024)')
    parser.add_argument('--mega-batch', type=int, default=10240,
                       help='DB commit batch size (default: 10240)')
    parser.add_argument('--workers', type=int, default=4,
                       help='Parallel workers (default: 4)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Max segments to process (default: all)')
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting parallel embedding backfill...")
    logger.info(f"   GPU batch: {args.batch_size}")
    logger.info(f"   DB batch: {args.mega_batch}")
    logger.info(f"   Workers: {args.workers}")
    logger.info(f"   Limit: {args.limit if args.limit else 'None (all)'}")
    
    backfill = ParallelEmbeddingBackfill(
        batch_size=args.batch_size,
        mega_batch_size=args.mega_batch,
        num_workers=args.workers
    )
    backfill.backfill(limit=args.limit)
