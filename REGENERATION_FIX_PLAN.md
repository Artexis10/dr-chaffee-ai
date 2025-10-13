# Speaker Label Regeneration Fix Plan

## Problem Identified

**All segments labeled as GUEST with 0.000 similarity** - This is a catastrophic failure caused by:

1. **Embedding Dimension Mismatch**:
   - Chaffee profile centroid: **195 dimensions**
   - Database embeddings: **192 dimensions** (from dummy model)
   - Real SpeechBrain ECAPA model: **192 dimensions**

2. **Root Cause**:
   - `voice_enrollment_optimized.py` uses a **dummy/fallback SimpleEmbeddingModel** (lines 44-93)
   - This dummy model creates **random 192-dim embeddings** instead of real voice embeddings
   - The Chaffee profile was built from these dummy embeddings (somehow got 195 dims)
   - Database segments also have dummy embeddings
   - **Result**: Comparing random noise to random noise = 0.000 similarity

## Why This Happened

The `voice_enrollment_optimized.py` was created as a workaround for Windows symlink issues with SpeechBrain, but it uses a completely broken dummy model that doesn't actually extract voice features.

## Solution Options

### Option 1: Use Real SpeechBrain Model (RECOMMENDED)
- Fix `voice_enrollment_optimized.py` to use real SpeechBrain ECAPA model
- Rebuild Chaffee profile with real embeddings
- Re-extract all database embeddings with real model
- **Pros**: Accurate speaker identification
- **Cons**: Requires fixing SpeechBrain on Windows, full re-ingestion

### Option 2: Use Alternative Embedding Model
- Switch to a different speaker embedding model (e.g., pyannote.audio's embedding)
- Rebuild everything with new model
- **Pros**: May avoid Windows issues
- **Cons**: Still requires full re-ingestion

### Option 3: Fix Existing Data (QUICK FIX)
- Check if database has any real embeddings from before the dummy model
- If yes, rebuild profile from those
- If no, must re-ingest with real model
- **Pros**: Faster if real embeddings exist
- **Cons**: May not be possible

## Immediate Actions Required

1. **Verify**: Check if database embeddings are real or dummy
   ```python
   # Check embedding variance - dummy embeddings will have high variance
   # Real voice embeddings cluster together
   ```

2. **Fix voice_enrollment_optimized.py**: Replace dummy model with real SpeechBrain
   - Use `local_dir_use_symlinks=False` to avoid Windows issues
   - Ensure proper model loading

3. **Rebuild Chaffee Profile**: With real embeddings from known Chaffee videos

4. **Re-run Regeneration**: After fixing the model

## DO NOT PROCEED with current regeneration - it will corrupt all speaker labels!
