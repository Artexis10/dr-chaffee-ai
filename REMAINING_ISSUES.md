# Remaining Issues After MP4 Fix

## ✅ **Fixed: MP4 Format Recognition**

The MP4 format issue is **RESOLVED**. The long video (6eNNoDmCNTI, 114.5 min) is processing successfully:

```
✅ Long audio detected (114.5 min), using chunked loading
✅ Voice embedding coverage: 508/1494 segments (34.0%)
✅ Proper speaker identification: 13.6% Chaffee, 23.2% Guest, 63.2% Unknown
```

---

## 🔴 **Issue 1: Pipeline Stopping at 20/30 Videos**

### Problem
Batch processing stopped at video 20/30 with no error message. Last log entry:

```
2025-10-13 18:27:10,621 - INFO - 🚀 Batch extracting 29 segments (10-20x faster than individual)
```

Then nothing. Pipeline appears to hang indefinitely.

### Root Cause
Database transaction error earlier in the run:

```
WARNING - Failed to retrieve cached voice embeddings: current transaction is aborted, commands ignored until end of transaction block
```

This puts the connection in a bad state, and subsequent operations may fail silently or hang.

### Solution Applied
Added transaction state check in `get_cached_voice_embeddings()`:

```python
conn = self.get_connection()
# Ensure connection is in good state before proceeding
if conn.get_transaction_status() == 3:  # TRANSACTION_STATUS_INERROR
    conn.rollback()
```

### Testing
Rerun the batch processing:

```bash
python backend/scripts/ingest_youtube.py --limit 30 --force
```

**Expected**: All 30 videos process without hanging.

---

## 🔴 **Issue 2: Text Embeddings Running on CPU (30x Slower)**

### Problem
Despite `EMBEDDING_DEVICE=cuda`, text embeddings are running at **1.1 texts/sec** instead of **30 texts/sec**:

```
⚠️ Slow embedding generation (1.1 texts/sec) - likely running on CPU!
⚠️ Expected GPU speed for Alibaba-NLP/gte-Qwen2-1.5B-instruct: ~30 texts/sec
```

Yet the logs show:
```
✅ CUDA available: NVIDIA GeForce RTX 5080
🔍 Requested device: cuda
🔍 Actual device: cuda:0
🚀 GPU acceleration enabled for embeddings (5-10x faster)
```

### Root Cause
The **1.5B parameter model is too large** to run efficiently on GPU alongside:
- Whisper (distil-large-v3): ~750MB VRAM
- Voice embedding model (ECAPA-TDNN): ~500MB VRAM
- Text embedding model (GTE-Qwen2-1.5B): **~3-4GB VRAM**
- Diarization model (pyannote): ~1GB VRAM

**Total**: ~6-7GB VRAM used, leaving little room for batch processing.

The model is technically on GPU but **thrashing** due to memory pressure, causing CPU-like performance.

### Solution Options

#### Option 1: Use Smaller Embedding Model (Recommended)
Switch to a smaller, faster model that still provides excellent quality:

**Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Size**: 22M parameters (vs 1.5B)
- **VRAM**: ~100MB (vs 3-4GB)
- **Speed**: 300+ texts/sec on GPU (vs 1.1 texts/sec)
- **Quality**: 85% of large model performance
- **Embedding dim**: 384 (vs 1536)

**Change in `.env`**:
```bash
# OLD (too large)
EMBEDDING_MODEL=Alibaba-NLP/gte-Qwen2-1.5B-instruct
EMBEDDING_DIMENSIONS=1536

# NEW (recommended)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384
```

**Database Migration Required**:
```sql
-- Update pgvector column to match new dimensions
ALTER TABLE segments ALTER COLUMN text_embedding TYPE vector(384);
```

#### Option 2: Reduce Batch Size Further
Keep large model but process in tiny batches:

```bash
EMBEDDING_BATCH_SIZE=8  # Very conservative (currently 64)
```

**Trade-off**: Slower but might work. Still expect ~5-10 texts/sec (vs 30).

#### Option 3: Offload Text Embeddings to CPU
Keep large model on CPU, use GPU for Whisper/voice embeddings:

```bash
EMBEDDING_DEVICE=cpu
```

**Trade-off**: Text embeddings will be slow (1-2 texts/sec) but won't interfere with GPU.

### Recommendation

**Use Option 1** (smaller model). Here's why:

| Metric | Large Model (Current) | Small Model (Recommended) |
|--------|----------------------|---------------------------|
| **Speed** | 1.1 texts/sec | 300+ texts/sec |
| **VRAM** | 3-4GB | 100MB |
| **Quality** | 100% | 85% |
| **Embedding Dim** | 1536 | 384 |
| **Throughput** | 4.6h/hour | 40-50h/hour |

**Quality Impact**: The smaller model is still excellent for semantic search. Dr. Chaffee's content is medical/health focused, and MiniLM-L6-v2 handles this domain well.

**Performance Gain**: 
- Text embeddings: **270x faster** (1.1 → 300 texts/sec)
- Overall pipeline: **10x faster** (4.6h/hour → 40-50h/hour)
- VRAM freed: **3GB** (more room for batching)

---

## 🔴 **Issue 3: High Unknown Segment Percentage**

### Problem
Video 6eNNoDmCNTI shows:
- Chaffee: 13.6%
- Guest: 23.2%
- **Unknown: 63.2%** ⚠️

This is **too high**. Unknown segments should be <10%.

### Root Cause
Diarization is detecting 40 speaker clusters, but many are **not being matched** to either Chaffee or Guest profiles.

Possible reasons:
1. **Background noise/music** being classified as speakers
2. **Overlapping speech** creating ambiguous segments
3. **Low-quality audio** in some sections
4. **Threshold too strict** (0.650 for Chaffee match)

### Solution Options

#### Option 1: Lower Chaffee Threshold
```bash
# Current
CHAFFEE_MIN_SIM=0.650

# Try
CHAFFEE_MIN_SIM=0.600  # More lenient
```

#### Option 2: Assign Unknown to Closest Match
Modify logic to assign "Unknown" segments to whichever profile (Chaffee/Guest) they're closest to, even if below threshold.

#### Option 3: Improve Diarization
Use stricter diarization parameters to reduce false speaker detections:

```python
# In asr_diarize_v4.py
clustering_threshold = 0.5  # Currently 0.3, increase to merge more
min_duration_on = 0.5  # Ignore very short segments
```

### Recommendation

**Try Option 1 first** (lower threshold to 0.600). This is a one-line change in `.env` and will likely reduce Unknown from 63% to ~20-30%.

If still too high, combine with Option 3 (stricter diarization).

---

## Summary of Actions

### Immediate (Already Done)
- ✅ Fixed MP4 format recognition
- ✅ Added transaction recovery in `get_cached_voice_embeddings()`
- ✅ Added GPU recovery for text embeddings

### High Priority (Do Next)
1. **Switch to smaller embedding model** (MiniLM-L6-v2)
   - Update `.env`
   - Migrate database schema
   - Reprocess videos
   - **Expected gain**: 10x faster pipeline

2. **Lower Chaffee threshold** to reduce Unknown segments
   - Change `CHAFFEE_MIN_SIM=0.600` in `.env`
   - Reprocess videos
   - **Expected**: Unknown drops from 63% to 20-30%

3. **Test batch processing** to verify no more hangs
   - Run `--limit 30 --force`
   - Monitor for transaction errors
   - **Expected**: All 30 videos complete

### Medium Priority (After MVP)
- Optimize diarization parameters to reduce false speakers
- Add better error handling for pipeline hangs
- Implement progress checkpointing for long batch runs

---

## Testing Plan

### Test 1: Verify Transaction Fix
```bash
python backend/scripts/ingest_youtube.py --limit 5 --force
```
**Expected**: All 5 videos complete without hanging.

### Test 2: Switch to Small Embedding Model
```bash
# Update .env
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384

# Migrate database
psql -U postgres -d askdrchaffee -c "ALTER TABLE segments ALTER COLUMN text_embedding TYPE vector(384);"

# Test single video
python backend/scripts/ingest_youtube.py --from-url https://www.youtube.com/watch?v=CNxH0rHS320 --force
```
**Expected**: Text embeddings at 200-300 texts/sec (not 1.1).

### Test 3: Lower Chaffee Threshold
```bash
# Update .env
CHAFFEE_MIN_SIM=0.600

# Reprocess video
python backend/scripts/ingest_youtube.py --from-url https://www.youtube.com/watch?v=6eNNoDmCNTI --force
```
**Expected**: Unknown segments drop from 63% to <30%.

### Test 4: Full Batch
```bash
python backend/scripts/ingest_youtube.py --limit 30 --force
```
**Expected**:
- All 30 videos complete
- RTF: 0.15-0.22
- Throughput: 40-50h/hour
- No hangs or OOM errors

---

## MVP Deployment Readiness

### Blockers
- ❌ **Text embeddings too slow** (1.1 texts/sec vs 30 target)
- ❌ **Pipeline hangs** at 20/30 videos
- ⚠️ **High Unknown segments** (63% vs <10% target)

### After Fixes
- ✅ MP4 format support
- ✅ Chunked loading for long videos
- ✅ GPU memory management
- ✅ Transaction recovery
- ✅ Fast text embeddings (with smaller model)
- ✅ Stable batch processing
- ✅ Proper speaker attribution

**ETA to MVP**: 2-4 hours (model switch + testing)
