# Final Speaker Accuracy Fix - Summary

## Problem
Video `1oKru2X3AvU` (interview with Pascal Johns) showed **100% Chaffee** when it should be ~50/50.

## Root Cause
**Pyannote's clustering threshold was not being configured correctly**, causing it to merge two distinct speakers (Chaffee and Guest) into a single cluster.

## The Journey (TDD Approach)

### 1. ✅ Tests Written First
- `tests/integration/test_speaker_accuracy.py` - Caught the 100% Chaffee issue
- `tests/unit/test_cluster_speaker_assignment.py` - Tests clustering logic
- Tests identified: 12 low-confidence segments, 100% Chaffee attribution

### 2. ❌ First Fix Attempt: Trust Diarization Clusters
**What we did**: Modified code to trust diarization clusters instead of per-segment re-identification  
**Result**: Didn't help because pyannote only returned 1 cluster  
**Lesson**: Fix was correct but addressed wrong layer of the problem

### 3. ❌ Second Fix Attempt: Set Clustering Threshold (Wrong Path)
**What we did**: Tried to set `pipeline.klustering.clustering.threshold`  
**Result**: Failed - wrong attribute path  
**Lesson**: Need to understand the actual object structure

### 4. ✅ Debug and Discover
**What we did**: Created `debug_pyannote.py` to inspect pipeline structure  
**Found**:
- `pipeline.klustering` is just a string "VBxClustering"
- `pipeline.clustering` is the actual VBxClustering object
- `pipeline.clustering.threshold` exists and defaults to 0.6
- Can be set directly: `pipeline.clustering.threshold = 0.4`

### 5. ✅ Final Fix: Correct Threshold Configuration
**What we did**: 
```python
if hasattr(pipeline, 'clustering') and hasattr(pipeline.clustering, 'threshold'):
    old_threshold = pipeline.clustering.threshold
    pipeline.clustering.threshold = 0.4  # From .env
    logger.info(f"✓ Set clustering threshold: {old_threshold} → {clustering_threshold}")
```

**Why 0.4**:
- Default: 0.6 (merges similar voices)
- Our setting: 0.4 (more sensitive to differences)
- Range: 0.0-1.0 (lower = more clusters)

## Why This Is The Right Solution

### ❌ Bad Approach: Force Speaker Count
```python
# DON'T DO THIS
params['min_speakers'] = 2
params['max_speakers'] = 2
```
**Problems**:
- Breaks for 3+ person panels
- Breaks for monologues
- Hardcoded assumption

### ✅ Good Approach: Lower Clustering Threshold
```python
# DO THIS
pipeline.clustering.threshold = 0.4
```
**Benefits**:
- ✅ Works for 2-person interviews
- ✅ Works for 3+ person panels
- ✅ Works for monologues (detects 1 speaker)
- ✅ Adapts to actual content
- ✅ No hardcoded assumptions

## Expected Results

### Before Fix
```
Video 1oKru2X3AvU:
  Clusters detected: 1
  Chaffee: 100% (WRONG!)
  Guest: 0%
```

### After Fix
```
Video 1oKru2X3AvU:
  Clusters detected: 2
  Chaffee: ~50%
  Guest: ~50%
  Low confidence segments: <2 (was 12)
```

## Verification Steps

1. **Re-ingest video**: `python backend/scripts/ingest_youtube.py --from-url https://www.youtube.com/watch?v=1oKru2X3AvU --source yt-dlp --force`

2. **Check segments**: `python check_segments.py 1oKru2X3AvU`

3. **Run integration tests**: `python -m pytest tests/integration/test_speaker_accuracy.py -v -s`

4. **Verify logs show**:
   ```
   ✓ Set clustering threshold: 0.6 → 0.4
   Cluster 0: ... Chaffee
   Cluster 1: ... GUEST
   ```

## Files Changed

1. **`backend/scripts/common/asr_diarize_v4.py`**
   - Fixed clustering threshold configuration
   - Correct attribute path: `pipeline.clustering.threshold`
   - Added logging to verify threshold is set

2. **`.env`**
   - `PYANNOTE_CLUSTERING_THRESHOLD=0.4` (was 0.5, default 0.6)

3. **`tests/integration/test_speaker_accuracy.py`** ✅
   - Integration tests for speaker attribution

4. **`tests/unit/test_cluster_speaker_assignment.py`** ✅
   - Unit tests for clustering logic

## Lessons Learned

1. **TDD is essential** - Tests caught the issue immediately
2. **Debug thoroughly** - Inspect actual object structure, don't assume
3. **One fix at a time** - Don't stack multiple fixes
4. **Verify each step** - Use debug scripts to understand what's happening
5. **Avoid hardcoded solutions** - Threshold adjustment > forced speaker count
6. **Test with real data** - Integration tests with actual videos

## Success Criteria

- [x] Tests written and committed
- [x] Root cause identified (clustering threshold)
- [x] Fix implemented correctly
- [ ] Video re-ingested successfully
- [ ] Integration tests pass
- [ ] ~50/50 speaker distribution
- [ ] <2 low-confidence segments

## Next Steps

1. Wait for re-ingestion to complete (~5 min)
2. Verify speaker distribution is ~50/50
3. Run integration tests
4. If successful, document as standard approach
5. Apply to full pipeline

---

**Status**: 🔄 Testing fix...
