#!/usr/bin/env python3
"""
Re-embed all segments with OpenAI embeddings
Replaces GTE-Qwen embeddings with OpenAI text-embedding-3-large
"""
import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
import time

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from scripts.common.embeddings import EmbeddingGenerator

# Load environment
env_path = backend_dir / '.env'
load_dotenv(env_path)

PROD_DB = os.getenv('PRODUCTION_DATABASE_URL')
OPENAI_KEY = os.getenv('OPENAI_API_KEY')

if not PROD_DB:
    print("ERROR: PRODUCTION_DATABASE_URL not set")
    exit(1)

if not OPENAI_KEY:
    print("ERROR: OPENAI_API_KEY not set")
    exit(1)

print("=" * 80)
print("RE-EMBEDDING WITH OPENAI")
print("=" * 80)
print(f"Database: {PROD_DB.split('@')[1].split('/')[0]}...")
print(f"Model: text-embedding-3-large (1536 dims)")
print()

# Connect to database
conn = psycopg2.connect(PROD_DB)
cur = conn.cursor()

# Count segments to re-embed
cur.execute("SELECT COUNT(*) FROM segments WHERE text IS NOT NULL AND text != ''")
total = cur.fetchone()[0]

print(f"Total segments to re-embed: {total:,}")
print(f"Estimated cost: ${total * 0.13 / 1000:.2f}")
print(f"Estimated time: ~{total / 40:.0f} minutes")
print()

response = input("Continue? (yes/no): ")
if response.lower() != 'yes':
    print("Aborted")
    exit(0)

# Initialize OpenAI embeddings
print("\nInitializing OpenAI embedding generator...")
generator = EmbeddingGenerator(
    embedding_provider='openai',
    model_name='text-embedding-3-large'
)

# Fetch all segments
print("Fetching segments...")
cur.execute("""
    SELECT id, text 
    FROM segments 
    WHERE text IS NOT NULL AND text != ''
    ORDER BY id
""")

segments = cur.fetchall()
print(f"Loaded {len(segments):,} segments")

# Process in batches
batch_size = 100  # OpenAI limit
processed = 0
start_time = time.time()

print("\nGenerating embeddings...")

for i in range(0, len(segments), batch_size):
    batch = segments[i:i + batch_size]
    batch_ids = [s[0] for s in batch]
    batch_texts = [s[1] for s in batch]
    
    try:
        # Generate embeddings
        embeddings = generator.generate_embeddings(batch_texts)
        
        # Update database
        for seg_id, embedding in zip(batch_ids, embeddings):
            cur.execute("""
                UPDATE segments 
                SET embedding = %s::vector,
                    embedding_model = 'openai-3-large',
                    embedding_created_at = NOW()
                WHERE id = %s
            """, (str(embedding), seg_id))
        
        conn.commit()
        processed += len(batch)
        
        # Progress update
        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = (total - processed) / rate if rate > 0 else 0
        
        print(f"Progress: {processed:,}/{total:,} ({processed/total*100:.1f}%) "
              f"| Rate: {rate:.1f} seg/s | ETA: {remaining/60:.1f} min", end='\r')
        
    except Exception as e:
        print(f"\nError processing batch {i}: {e}")
        conn.rollback()
        continue

elapsed = time.time() - start_time
print(f"\n\n✅ Complete! Processed {processed:,} segments in {elapsed/60:.1f} minutes")
print(f"Average rate: {processed/elapsed:.1f} segments/second")

cur.close()
conn.close()
