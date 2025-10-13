# TDD Fix Plan: Restore 50 Videos/Hour Performance

## Root Cause Analysis (Data-Driven)

### What We Know Works (from SESSION_SUMMARY.md)
- **Achieved**: 63h/hour throughput (RTF: 0.107)
- **Voice embedding batching**: 885x speedup (2.3s vs 34min)
- **Text embedding caching**: Model loaded once
- **Target**: 50h/hour → 1200h in 24h

### What's Broken Now
1. **Voice embeddings NOT cached** - re-extracted every video
   - Current: 19 segments × 5s = 95s overhead per video
   - For 5 videos: 475s wasted (79% of 605s total time!)
   - **This is THE bottleneck**

2. **Speaker counting bug** - 215 > 115 (1.87x overcounting)
   - Fixed in code but needs verification

3. **No performance regression tests**
   - Can't detect when performance degrades

## TDD Approach

### Step 1: Write Failing Tests ✅
Created: `tests/unit/test_voice_embedding_caching.py`
- test_voice_embeddings_stored_in_database
- test_voice_embeddings_retrieved_from_database  
- test_voice_embedding_cache_hit
- test_voice_embedding_cache_miss
- test_voice_embedding_partial_cache
- test_voice_embedding_performance_improvement

### Step 2: Implement Voice Embedding Cache
**File**: `backend/scripts/common/voice_enrollment_optimized.py`

```python
def get_cached_voice_embeddings(self, video_id: str, segments_db) -> Dict[tuple, np.ndarray]:
    """Retrieve cached voice embeddings from database
    
    Returns:
        Dict mapping (start_sec, end_sec) -> voice_embedding
    """
    # Query database for existing voice embeddings for this video
    # Return as dict for fast lookup
    pass

def extract_missing_embeddings(self, audio_path: str, segments: List, 
                               cached_embeddings: Dict) -> Dict:
    """Extract only embeddings not in cache
    
    Args:
        audio_path: Path to audio file
        segments: All segments needing embeddings
        cached_embeddings: Already cached embeddings
        
    Returns:
        Dict of newly extracted embeddings
    """
    # Filter segments to only those without cached embeddings
    # Extract embeddings for missing segments only
    # Return combined cached + new embeddings
    pass
```

### Step 3: Update Enhanced ASR to Use Cache
**File**: `backend/scripts/common/enhanced_asr.py`

```python
# Before speaker ID, check cache
cached_embeddings = self.voice_enrollment.get_cached_voice_embeddings(
    video_id, segments_db
)

# Only extract missing embeddings
if len(cached_embeddings) < len(segments):
    new_embeddings = self.voice_enrollment.extract_missing_embeddings(
        audio_path, segments, cached_embeddings
    )
    all_embeddings = {**cached_embeddings, **new_embeddings}
else:
    all_embeddings = cached_embeddings
    logger.info(f"✅ 100% cache hit - no extraction needed!")
```

### Step 4: Run Tests
```powershell
pytest tests/unit/test_voice_embedding_caching.py -v
```

Expected: All tests pass ✅

### Step 5: Performance Regression Test
**File**: `tests/performance/test_ingestion_throughput.py`

```python
def test_ingestion_throughput_target():
    """Test that ingestion meets 50h/hour target"""
    # Process 5 test videos
    # Measure throughput
    # Assert throughput >= 50h/hour
    pass

def test_voice_embedding_cache_usage():
    """Test that voice embeddings are cached and reused"""
    # Process video 1: Extract embeddings
    # Process video 2 (same speaker): Should use cache
    # Assert: No extraction calls for video 2
    pass
```

### Step 6: Verify Speaker Counting Fix
```powershell
python backend/scripts/ingest_youtube.py --limit 5 --newest-first
```

Watch for:
```
📊 Speaker counts for VIDEO_ID: 77 segments → Chaffee=60, Guest=15, Unknown=2
```

Sum should equal total segments created.

## Expected Performance After Fix

### Before (Current - Broken)
- 5 videos in 605 seconds = 121s/video
- Voice embedding overhead: 475s (79% of time!)
- Throughput: 14.8h/hour
- Estimate for 1200h: 81 hours

### After (With Caching)
- 5 videos in ~130 seconds = 26s/video (4.7x faster!)
- Voice embedding overhead: ~10s (first video only)
- Throughput: 50-60h/hour ✅
- Estimate for 1200h: 20-24 hours ✅

## Implementation Priority

1. **HIGH**: Voice embedding caching (79% time savings!)
2. **MEDIUM**: Verify speaker counting fix
3. **MEDIUM**: Add performance regression tests
4. **LOW**: Other optimizations

## Success Criteria

- ✅ All unit tests pass
- ✅ Performance tests pass (50h/hour target)
- ✅ Speaker counts match total segments
- ✅ Voice embeddings cached and reused
- ✅ 5 videos process in <150 seconds (vs 605s current)

## Notes

- Voice embedding batching (885x speedup) is ALREADY implemented
- The issue is we're calling it TOO MANY TIMES
- Caching will reduce calls from N videos to 1 (first video only)
- This is the LAST major bottleneck to fix
