#!/usr/bin/env python3
"""
Re-embed all segments with Nomic v1.5 using local GPU (RTX 5080)
Fast batch processing optimized for your hardware
"""
import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
import time
import torch
from sentence_transformers import SentenceTransformer

# Load environment
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / '.env'
load_dotenv(env_path)

PROD_DB = os.getenv('PRODUCTION_DATABASE_URL')

if not PROD_DB:
    print("ERROR: PRODUCTION_DATABASE_URL not set")
    exit(1)

print("=" * 80)
print("RE-EMBEDDING WITH NOMIC V1.5 (LOCAL GPU)")
print("=" * 80)
print(f"Database: {PROD_DB.split('@')[1].split('/')[0]}...")
print(f"Model: nomic-embed-text-v1.5 (768 dims)")
print(f"Device: RTX 5080")
print()

# Connect to database
conn = psycopg2.connect(PROD_DB)
cur = conn.cursor()

# Count segments
cur.execute("SELECT COUNT(*) FROM segments WHERE text IS NOT NULL AND text != ''")
total = cur.fetchone()[0]

print(f"Total segments: {total:,}")
print(f"Estimated time: ~{total / 125 / 60:.1f} minutes (125 seg/sec)")
print()

# Check if we're doing a test run
TEST_MODE = '--test' in sys.argv
if TEST_MODE:
    print("🧪 TEST MODE: Processing first 100 segments only")
    limit_clause = "LIMIT 100"
else:
    response = input("Continue with FULL re-embedding? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted")
        exit(0)
    limit_clause = ""

# Load Nomic model
print("\n📦 Loading Nomic v1.5 model on GPU...")
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True, device=device)
print(f"✅ Model loaded on {device}")

# Fetch segments
print("\n📥 Fetching segments...")
cur.execute(f"""
    SELECT id, text 
    FROM segments 
    WHERE text IS NOT NULL AND text != ''
    ORDER BY id
    {limit_clause}
""")

segments = cur.fetchall()
print(f"Loaded {len(segments):,} segments")

# Process in batches
batch_size = 256  # Optimized for RTX 5080
processed = 0
start_time = time.time()

print("\n🚀 Generating embeddings...")

for i in range(0, len(segments), batch_size):
    batch = segments[i:i + batch_size]
    batch_ids = [s[0] for s in batch]
    batch_texts = [s[1] for s in batch]
    
    try:
        # Generate embeddings on GPU
        embeddings = model.encode(
            batch_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True  # Nomic recommends normalization
        )
        
        # Insert into segment_embeddings table
        for seg_id, embedding in zip(batch_ids, embeddings):
            cur.execute("""
                INSERT INTO segment_embeddings (
                    segment_id, model_key, model_name, provider, dimensions, embedding
                ) VALUES (%s, %s, %s, %s, %s, %s::vector)
                ON CONFLICT (segment_id, model_key) 
                DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    created_at = NOW()
            """, (
                seg_id,
                'nomic-v1.5',
                'nomic-embed-text-v1.5',
                'local',
                768,
                str(embedding.tolist())
            ))
        
        conn.commit()
        processed += len(batch)
        
        # Progress update
        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = (len(segments) - processed) / rate if rate > 0 else 0
        
        print(f"Progress: {processed:,}/{len(segments):,} ({processed/len(segments)*100:.1f}%) "
              f"| Rate: {rate:.1f} seg/s | ETA: {remaining/60:.1f} min", end='\r')
        
    except Exception as e:
        print(f"\n❌ Error processing batch {i}: {e}")
        conn.rollback()
        continue

elapsed = time.time() - start_time
print(f"\n\n✅ Complete! Processed {processed:,} segments in {elapsed/60:.1f} minutes")
print(f"Average rate: {processed/elapsed:.1f} segments/second")

# Verify coverage
cur.execute("""
    SELECT COUNT(*) FROM segment_embeddings 
    WHERE model_key = 'nomic-v1.5' AND embedding IS NOT NULL
""")
nomic_count = cur.fetchone()[0]
print(f"\n📊 Nomic embeddings in DB: {nomic_count:,}")

cur.close()
conn.close()

if TEST_MODE:
    print("\n✅ Test complete! Run without --test to process all segments.")
else:
    print("\n🎉 Ready for production! Update config to use nomic-v1.5")
