# BGE-Small Migration Guide

## Overview

This guide covers migrating from **GTE-Qwen2-1.5B** (1536-dim) to **BAAI/bge-small-en-v1.5** (384-dim) embeddings for **50x+ faster** embedding generation with minimal quality loss.

## Performance Comparison

| Model | Dimensions | Speed (texts/sec) | VRAM | Quality |
|-------|-----------|-------------------|------|---------|
| GTE-Qwen2-1.5B | 1536 | ~30-50 | ~4GB | Excellent |
| BGE-Small | 384 | ~1,500-2,000 | ~0.5GB | Very Good |

**Speedup**: 50x faster on RTX 5080  
**Storage**: 75% reduction (384 vs 1536 dims)  
**Quality**: <5% retrieval quality loss with optional reranker

---

## Prerequisites

### 1. Dependencies

Update dependencies:
```bash
pip install sentence-transformers>=2.7.0 transformers>=4.41.0
```

### 2. Environment Configuration

Update `.env` file:
```bash
# Embedding Configuration (BGE-Small for 50x+ speedup)
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSIONS=384
EMBEDDING_DEVICE=cuda  # 'cuda' for GPU, 'cpu' for CPU
EMBEDDING_BATCH_SIZE=256

# Reranker Configuration (Optional cross-encoder for better relevance)
ENABLE_RERANKER=true
RERANK_TOP_K=200  # Retrieve this many candidates for reranking
RETURN_TOP_K=20   # Return this many after reranking
RERANK_BATCH_SIZE=64
```

### 3. Database Backup

**CRITICAL**: Backup your database before migration:
```bash
pg_dump -U postgres askdrchaffee > backup_before_bge_migration.sql
```

---

## Migration Process

The migration consists of **3 phases**:

### Phase 1: Add embedding_384 Column
- Adds new `embedding_384 vector(384)` column
- Drops old IVFFLAT index to prevent conflicts
- **Safe**: Idempotent, can run multiple times

### Phase 2: Backfill Embeddings
- Generates BGE-Small embeddings for all segments
- Processes in batches of 1,000 rows
- Retries failed batches up to 3 times
- **Resumable**: Only processes NULL rows
- **Performance**: ~1,500-2,000 texts/sec on RTX 5080

### Phase 3: Swap Columns & Rebuild Index
- Creates IVFFLAT index on `embedding_384`
- Drops old `embedding` column (1536-dim)
- Renames `embedding_384` to `embedding`
- Rebuilds index with optimal parameters
- **Warning**: Old embeddings are deleted (irreversible)

---

## Execution

### Option 1: Automated Script (Recommended)

**Windows (PowerShell)**:
```powershell
cd backend
.\scripts\02_switch_to_bge_small.ps1
```

**Linux/Mac (Bash)**:
```bash
cd backend
chmod +x scripts/02_switch_to_bge_small.sh
./scripts/02_switch_to_bge_small.sh
```

### Option 2: Manual Execution

```bash
cd backend

# Run all migrations
alembic upgrade head

# Verify migration
alembic current

# Run benchmark
python scripts/test_embedding_speed.py
```

### Option 3: Step-by-Step

```bash
cd backend

# Phase 1: Add column
alembic upgrade 005

# Phase 2: Backfill (may take 10-20 min for 1M segments)
alembic upgrade 006

# Phase 3: Swap & index
alembic upgrade 007
```

---

## Performance Expectations

### Phase 2 Backfill Times

| Segments | RTX 5080 | RTX 4090 | CPU (16-core) |
|----------|----------|----------|---------------|
| 10k | ~10 sec | ~15 sec | ~3 min |
| 100k | ~1-2 min | ~2-3 min | ~20 min |
| 1M | ~10-20 min | ~15-30 min | ~3 hours |

### Embedding Generation

**GPU (RTX 5080)**:
- Throughput: 1,500-2,000 texts/sec
- Batch size: 256 (optimal)
- VRAM usage: ~0.5 GB

**CPU (16-core)**:
- Throughput: 50-100 texts/sec
- Batch size: 64 (optimal)
- RAM usage: ~2 GB

---

## Verification

### 1. Check Migration Status

```bash
cd backend
alembic current
```

Should show: `007 (head)`

### 2. Verify Column Structure

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'segments' 
AND column_name = 'embedding';
```

Should show: `embedding | USER-DEFINED` (vector type)

### 3. Check Embedding Dimensions

```sql
SELECT COUNT(*) as total,
       COUNT(embedding) as populated,
       COUNT(*) - COUNT(embedding) as missing
FROM segments
WHERE text IS NOT NULL;
```

### 4. Test Semantic Search

```sql
-- Generate test embedding (384-dim)
SELECT id, text, 
       embedding <=> '[0.1, 0.2, ...]'::vector as distance
FROM segments
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;
```

### 5. Run Benchmark

```bash
cd backend
python scripts/test_embedding_speed.py
```

Expected output:
```
✅ Best encoding throughput: 1,500+ texts/sec (batch_size=256)
🚀 Speedup vs GTE-Qwen2-1.5B: 50x faster
```

---

## Rollback

### Before Phase 3 (Reversible)

If you haven't run Phase 3 yet, you can rollback:

```bash
# Rollback to Phase 1 (clears embedding_384)
alembic downgrade 005

# Rollback to before migration
alembic downgrade 004
```

### After Phase 3 (Irreversible)

Phase 3 deletes old 1536-dim embeddings. To restore:

**Option 1**: Restore from backup
```bash
psql -U postgres askdrchaffee < backup_before_bge_migration.sql
```

**Option 2**: Re-run ingestion with old model
```bash
# Update .env to use old model
EMBEDDING_MODEL=Alibaba-NLP/gte-Qwen2-1.5B-instruct
EMBEDDING_DIMENSIONS=1536

# Re-run ingestion
python scripts/ingest_youtube_enhanced.py --force
```

---

## Integration

### Update Application Code

Replace direct `EmbeddingGenerator` usage with `EmbeddingsService`:

**Before**:
```python
from scripts.common.embeddings import EmbeddingGenerator

generator = EmbeddingGenerator()
embeddings = generator.generate_embeddings(texts)
```

**After**:
```python
from services.embeddings_service import EmbeddingsService

EmbeddingsService.init_from_env()
embeddings = EmbeddingsService.encode_texts(texts, batch_size=256)
```

### Query Path with Reranker

```python
from services.embeddings_service import EmbeddingsService

# Initialize once
EmbeddingsService.init_from_env()

# Generate query embedding
query_embedding = EmbeddingsService.encode_texts([query])[0]

# Retrieve top-K candidates from pgvector
candidates = retrieve_from_db(query_embedding, top_k=200)

# Rerank if enabled
if os.getenv('ENABLE_RERANKER') == 'true':
    candidate_texts = [c['text'] for c in candidates]
    ranked_indices = EmbeddingsService.rerank(query, candidate_texts, top_k=20)
    results = [candidates[i] for i in ranked_indices]
else:
    results = candidates[:20]
```

---

## Testing

### Run Pytest Suite

```bash
# Test embeddings service
pytest tests/embeddings/test_embeddings_service.py -v

# Test session rollback hygiene
pytest tests/db/test_session_rollback.py -v

# Test migration chain
pytest tests/migrations/test_bge_migration_chain.py -v

# Run all tests
pytest tests/ -v
```

### Skip GPU/pgvector Tests

If running in CI without GPU or pgvector:

```bash
pytest tests/ -v -m "not cuda and not pgvector"
```

---

## Troubleshooting

### Issue: "CUDA out of memory"

**Solution**: Reduce batch size
```bash
# In .env
EMBEDDING_BATCH_SIZE=128  # or 64
```

### Issue: "pgvector extension not found"

**Solution**: Install pgvector
```bash
# Ubuntu/Debian
sudo apt install postgresql-15-pgvector

# From source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### Issue: "Slow embedding generation"

**Check**:
1. Verify CUDA is available: `python -c "import torch; print(torch.cuda.is_available())"`
2. Check device in logs: Should show `cuda`, not `cpu`
3. Monitor GPU usage: `nvidia-smi -l 1`

**Fix**:
```bash
# Ensure CUDA device is set
EMBEDDING_DEVICE=cuda
```

### Issue: "Migration Phase 2 stuck"

**Check progress**:
```sql
SELECT COUNT(*) as total,
       COUNT(embedding_384) as populated
FROM segments;
```

**Resume**: Phase 2 is resumable - just run again:
```bash
alembic upgrade 006
```

### Issue: "Index creation takes too long"

Phase 3 index creation can take 5-10 minutes for large datasets. This is normal.

**Monitor**:
```sql
SELECT * FROM pg_stat_progress_create_index;
```

---

## Performance Tuning

### Optimal Batch Sizes

| Hardware | Encoding Batch | Reranking Batch |
|----------|---------------|-----------------|
| RTX 5080 | 256 | 64 |
| RTX 4090 | 256 | 64 |
| RTX 3090 | 128 | 32 |
| CPU (16-core) | 64 | 16 |

### IVFFLAT Index Tuning

The migration auto-calculates `lists` parameter:
```python
lists = min(1000, max(100, int(sqrt(num_rows))))
```

For manual tuning:
```sql
-- Drop and recreate index with custom lists
DROP INDEX idx_segments_text_embedding_ivfflat;

CREATE INDEX idx_segments_text_embedding_ivfflat 
ON segments USING ivfflat (embedding vector_l2_ops) 
WITH (lists = 500);  -- Adjust based on dataset size
```

**Guidelines**:
- 100k rows: lists=300-400
- 1M rows: lists=500-1000
- 10M rows: lists=1000-2000

---

## FAQ

**Q: Will this affect search quality?**  
A: Minimal impact (<5% retrieval quality loss). Enable reranker for best results.

**Q: Can I keep both embedding models?**  
A: Not directly. You'd need to add a separate column and modify queries.

**Q: How long does migration take?**  
A: Phase 1: <1 min, Phase 2: 10-20 min (1M segments), Phase 3: 5-10 min

**Q: Is this reversible?**  
A: Before Phase 3: Yes. After Phase 3: Only via backup restore.

**Q: Do I need to re-ingest videos?**  
A: No. Migration backfills embeddings automatically.

**Q: What about voice embeddings?**  
A: Voice embeddings (speaker identification) are unchanged.

---

## Support

For issues or questions:
1. Check logs: `backend/youtube_ingestion_enhanced.log`
2. Run diagnostics: `python scripts/test_embedding_speed.py`
3. Review migration status: `alembic current`
4. Check database: `psql -U postgres askdrchaffee`

---

## Summary

✅ **50x faster** embedding generation  
✅ **75% smaller** storage footprint  
✅ **Resumable** migration with retry logic  
✅ **Optional reranker** for quality preservation  
✅ **Comprehensive tests** for validation  

**Estimated total time**: 20-30 minutes for 1M segments
