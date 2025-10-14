# Quick Start: BGE-Small Migration

## TL;DR

Replace GTE-Qwen2-1.5B with BGE-Small for **50x faster** embeddings in 3 commands:

```bash
cd backend
pip install sentence-transformers>=2.7.0 transformers>=4.41.0
.\scripts\02_switch_to_bge_small.ps1  # Windows
# OR
./scripts/02_switch_to_bge_small.sh   # Linux/Mac
```

---

## What This Does

1. **Adds** new 384-dim embedding column
2. **Backfills** all segments with BGE-Small embeddings (~10-20 min for 1M segments)
3. **Swaps** columns and rebuilds index
4. **Result**: 50x faster embedding generation, 75% less storage

---

## Before You Start

### 1. Backup Database
```bash
pg_dump -U postgres askdrchaffee > backup_before_bge.sql
```

### 2. Update .env
```bash
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSIONS=384
EMBEDDING_DEVICE=cuda
ENABLE_RERANKER=true
```

### 3. Verify CUDA
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

---

## Run Migration

### Windows
```powershell
cd backend
.\scripts\02_switch_to_bge_small.ps1
```

### Linux/Mac
```bash
cd backend
chmod +x scripts/02_switch_to_bge_small.sh
./scripts/02_switch_to_bge_small.sh
```

---

## Verify

```bash
# Check migration status
cd backend
alembic current  # Should show: 007 (head)

# Run benchmark
python scripts/test_embedding_speed.py
# Expected: 1,500+ texts/sec

# Run tests
pytest tests/embeddings/ tests/db/ tests/migrations/ -v
```

---

## What Changed

### Performance
- **Before**: 30-50 texts/sec (GTE-Qwen2-1.5B)
- **After**: 1,500-2,000 texts/sec (BGE-Small)
- **Speedup**: 50x

### Storage
- **Before**: 1536 dims × 4 bytes = 6.1 GB per 1M segments
- **After**: 384 dims × 4 bytes = 1.5 GB per 1M segments
- **Savings**: 75%

### Code
- Existing code works unchanged (backward compatible)
- Optional: Use new `EmbeddingsService` for better performance

---

## Rollback (Before Phase 3)

```bash
cd backend
alembic downgrade 004
```

**After Phase 3**: Restore from backup (old embeddings deleted)

---

## Need Help?

- **Full Guide**: [BGE_MIGRATION_GUIDE.md](./BGE_MIGRATION_GUIDE.md)
- **Implementation Details**: [BGE_IMPLEMENTATION_SUMMARY.md](./BGE_IMPLEMENTATION_SUMMARY.md)
- **Troubleshooting**: See migration guide

---

## Next Steps

1. ✅ Migration complete
2. Test semantic search queries
3. Monitor embedding generation performance
4. (Optional) Update code to use `EmbeddingsService` directly

---

**Time Required**: 20-30 minutes for 1M segments  
**Risk Level**: Low (resumable, idempotent, backward compatible)  
**Reversibility**: Yes (before Phase 3), backup restore (after Phase 3)
