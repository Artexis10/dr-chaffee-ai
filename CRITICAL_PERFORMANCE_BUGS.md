# Critical Performance Bugs Found

## Summary
30-40 minutes for 5 videos = **6.4h/hour throughput** (target: 50h/hour)
**Root causes**: Cache not working + RTF not tracked for fast-path

## Bug 1: Voice Embedding Cache Not Working ❌

### Evidence
```
📊 Voice embedding cache stats: 0 hits, 236 misses (0.0% hit rate)
📊 Voice embedding cache stats: 0 hits, 240 misses (0.0% hit rate)
```

### Root Cause
`segments_db` and `video_id` are NOT passed to `enhanced_asr.transcribe_with_speaker_id()`

### Location
`backend/scripts/common/enhanced_transcript_fetch.py:329`
```python
# BROKEN: No segments_db or video_id passed
result = enhanced_asr.transcribe_with_speaker_id(audio_path)
```

### Fix Required
```python
# Pass segments_db and video_id for caching
enhanced_asr.segments_db = segments_db
enhanced_asr.video_id = video_id
result = enhanced_asr.transcribe_with_speaker_id(audio_path)
```

### Impact
- **Current**: Re-extracts 19 embeddings per video (~17 seconds each)
- **With cache**: 0 seconds for cached embeddings
- **Time saved**: ~85 seconds per video = 425 seconds for 5 videos!

## Bug 2: RTF Calculation Broken ❌

### Evidence
```
Real-time factor (RTF): 0.000 (target: 0.15-0.22)
Throughput: 6.4 hours audio per hour (target: ~50h/h)
```

### Root Cause
`asr_processing_time_s` is NOT tracked for fast-path videos

### Location
`backend/scripts/ingest_youtube.py:1315-1329`
```python
# BROKEN: Fast-path doesn't track ASR time
fast_path_result = self._process_monologue_fast_path(...)
if fast_path_result:
    # Missing: self.stats.asr_processing_time_s += asr_time
    self.stats.add_audio_duration(audio_duration)
```

### Fix Required
```python
# Track ASR time for fast-path
asr_start_time = time.time()
fast_path_result = self._process_monologue_fast_path(...)
asr_end_time = time.time()

if fast_path_result:
    asr_processing_time = asr_end_time - asr_start_time
    with stats_lock:
        self.stats.asr_processing_time_s += asr_processing_time
        self.stats.add_audio_duration(audio_duration)
```

### Impact
- **Current**: RTF = 0.000 (meaningless)
- **With fix**: RTF = 0.15-0.22 (accurate measurement)

## Bug 3: Speaker Count Mismatch (Still Present!) ❌

### Evidence
```
⚠️  Speaker count mismatch: 447 speaker segments > 147 total segments
Chaffee segments: 208
Guest segments: 234
Unknown segments: 5
Total: 447 (should be 147!)
```

### Root Cause
Speaker segments are counted BEFORE optimization (1424 + 1494 + ... segments)
But `segments_created` is counted AFTER optimization (182 + 240 + ... segments)

### Location
`backend/scripts/ingest_youtube.py:1748-1775`

### Fix Required
Count speaker segments AFTER optimization, not before

### Impact
- **Current**: Confusing logs, incorrect percentages
- **With fix**: Accurate speaker attribution metrics

## Performance Analysis

### Current Performance (BROKEN)
- 5 videos: 38 minutes (2295 seconds)
- Total audio: 4.1 hours
- Throughput: 6.4h/hour
- **7.8x slower than target!**

### Expected Performance (WITH FIXES)
- Voice embedding cache: Save ~425 seconds (18.5%)
- Remaining time: ~1870 seconds (31 minutes)
- Throughput: ~7.9h/hour
- **Still 6.3x slower than target!**

### Why Still Slow?

Looking at logs, voice embeddings are extracted **MANY times per video**:
```
Processing 19 segments in 1 batches of 32  ← Repeated 10+ times per video!
```

This suggests:
1. **Per-segment identification** is being used (slow path)
2. **Cluster-level identification** should be used instead (fast path)
3. **Cache would help** but won't fix the root issue

### Real Bottleneck

The pipeline is using **per-segment speaker identification** instead of **cluster-level**:
- Per-segment: Extract embeddings for EVERY segment (slow)
- Cluster-level: Extract embeddings for EACH cluster (fast)

For a video with 226 segments in 1 cluster:
- Per-segment: 226 × 19 embeddings = 4294 extractions!
- Cluster-level: 1 × 19 embeddings = 19 extractions
- **Speedup: 226x!**

## Action Plan

### Priority 1: Enable Cache (Quick Win)
1. Pass `segments_db` and `video_id` to enhanced_asr
2. Expected: 18% speedup (425s saved)

### Priority 2: Fix RTF Calculation (Metrics)
1. Track ASR time for fast-path
2. Expected: Accurate performance metrics

### Priority 3: Fix Speaker Counting (Accuracy)
1. Count speakers after optimization
2. Expected: Correct attribution percentages

### Priority 4: Investigate Per-Segment Identification (Root Cause)
1. Check why per-segment ID is being used
2. Should use cluster-level ID for monologue content
3. Expected: 10-20x speedup if fixed

## Estimated Impact

| Fix | Time Saved | Throughput Improvement |
|-----|------------|----------------------|
| Enable cache | 425s (18%) | 6.4 → 7.9h/hour |
| Fix per-segment ID | 1500s (65%) | 7.9 → 22.6h/hour |
| **Combined** | **1925s (84%)** | **6.4 → 40h/hour** |

**Still short of 50h/hour target, but much closer!**

## Next Steps

1. ✅ Implement cache fixes (Priority 1)
2. ✅ Fix RTF calculation (Priority 2)
3. ✅ Fix speaker counting (Priority 3)
4. ⏳ Investigate per-segment ID issue (Priority 4)
5. ⏳ Profile remaining bottlenecks
