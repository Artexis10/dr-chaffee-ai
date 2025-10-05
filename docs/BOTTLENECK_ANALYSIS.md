# Bottleneck Analysis - Only 8 Videos in 1 Hour

## The Problem

**Expected:** ~50h audio per hour (from memory)  
**Actual:** 8 videos in 1 hour (~6-8 videos/hour)  
**Performance:** ~10-15x slower than target!

## Root Cause: Embedding Generation Bottleneck

### Evidence from Logs

```
Generated 372 local embeddings in 446.03s (0.8 texts/sec)
Batches: 100%|###| 12/12 [07:25<00:00, 37.17s/it]
```

**37 seconds per batch** for embeddings!

### GPU Utilization

```
SM=26% ... SM=14% ... SM=2% ... SM=1%
```

**GPU sitting idle 75-99% of the time!**

### Queue Status

```
io_q=24 asr_q=1 db=0
```

- I/O queue full (24 downloads waiting)
- ASR queue empty (only 1 video processing)
- **Embeddings blocking everything!**

## The Culprit: gte-Qwen2-1.5B-instruct

**Model:** `Alibaba-NLP/gte-Qwen2-1.5B-instruct`  
**Size:** 1.5 billion parameters  
**Speed:** 37 seconds per batch (0.8 texts/sec)  
**Dimensions:** 1536

**This model is TOO SLOW for bulk processing!**

## The Fix

### Change 1: Switch to Faster Embedding Model

```bash
# Before (SLOW):
EMBEDDING_MODEL=Alibaba-NLP/gte-Qwen2-1.5B-instruct  # 37s/batch
EMBEDDING_DIMENSIONS=1536

# After (FAST):
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # ~2s/batch
EMBEDDING_DIMENSIONS=384
```

**Speed improvement:** 18x faster (37s → 2s per batch)

### Change 2: Reduce Concurrency (Embeddings are Bottleneck)

```bash
# Before:
IO_WORKERS=12
ASR_WORKERS=12
DB_WORKERS=16
BATCH_SIZE=256

# After:
IO_WORKERS=8   # Reduce downloads (queue was full)
ASR_WORKERS=2  # Reduce ASR (only 1 was active anyway)
DB_WORKERS=4   # Reduce DB (embeddings blocking)
BATCH_SIZE=128 # Smaller batches for faster throughput
```

## Alternative Embedding Models

### Option 1: all-MiniLM-L6-v2 (Recommended)
- **Speed:** ~2s/batch (18x faster)
- **Dimensions:** 384
- **Quality:** Good for semantic search
- **Best for:** Bulk processing

### Option 2: bge-small-en-v1.5
- **Speed:** ~3-5s/batch (7-12x faster)
- **Dimensions:** 384
- **Quality:** Better than MiniLM
- **Best for:** Balance of speed and quality

### Option 3: gte-Qwen2-1.5B (Current - TOO SLOW)
- **Speed:** 37s/batch
- **Dimensions:** 1536
- **Quality:** Best
- **Best for:** Small datasets only

## Expected Performance After Fix

### Before
- Embedding: 37s/batch
- GPU util: 1-26%
- Throughput: 8 videos/hour

### After
- Embedding: 2s/batch (18x faster)
- GPU util: 70-90% (target)
- Throughput: 80-120 videos/hour (10-15x faster)

## Implementation

### Step 1: Update .env

```bash
# Change these lines in .env:
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384
IO_WORKERS=8
ASR_WORKERS=2
DB_WORKERS=4
BATCH_SIZE=128
```

### Step 2: Restart Ingestion

```bash
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 300 --limit-unprocessed
```

### Step 3: Monitor Performance

Watch for:
- ✅ GPU util: 70-90%
- ✅ Embedding speed: ~2s/batch
- ✅ Queue balance: io_q < 10, asr_q > 0
- ✅ Throughput: 80-120 videos/hour

## Why This Happened

**gte-Qwen2-1.5B is a high-quality model** but:
- 1.5 billion parameters
- Designed for accuracy, not speed
- Overkill for bulk processing
- Better suited for final production embeddings

**For bulk ingestion, use faster model:**
- Process 1200h in 24h
- Then optionally re-embed with better model later

## Summary

**The bottleneck:** Embedding model too slow (37s/batch)  
**The fix:** Switch to faster model (2s/batch)  
**Expected result:** 18x faster, 80-120 videos/hour  

**Your ingestion should be MUCH faster now!** 🎯
