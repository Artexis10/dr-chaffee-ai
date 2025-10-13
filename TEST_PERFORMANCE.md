# Performance Testing Guide

## Quick Test (5 videos)

```powershell
# Clear GPU
nvidia-smi --gpu-reset

# Run test
python backend/scripts/ingest_youtube.py --limit 5 --newest-first

# Watch for these logs:
# 📊 Speaker counts for {video_id}: X segments → Chaffee=Y, Guest=Z, Unknown=W
```

## Expected Results (5 videos, ~20min each)

```
Total audio processed: ~1.7 hours
Real-time factor (RTF): 0.05-0.10 (fast-path is FAST!)
Throughput: 10-20 hours audio per hour
Speaker counts: Should MATCH total segments created
```

## Known Issues Fixed

1. ✅ Audio duration tracking in fast-path
2. ✅ CUDA OOM errors (GPU cache clearing)
3. ⚠️ Speaker counting (still debugging - 215 > 115)

## Debug Speaker Counting

The new logging will show:
```
📊 Speaker counts for VIDEO_ID: 77 segments → Chaffee=60, Guest=15, Unknown=2
```

If you see this 5 times (once per video), and the sum matches the total, then it's fixed!

## Performance Comparison

### Before (Broken)
- 10 videos in 51 minutes = 5.1 min/video
- Total audio: 0.0 hours (broken tracking)
- Speaker counts: 645 > 245 (2.6x overcounting)

### Target (Working)
- 10 videos in 10-15 minutes = 1-1.5 min/video
- Total audio: ~3.5 hours (accurate)
- Speaker counts: Match total segments

### Why Slower Now?

1. **Voice enrollment overhead**: Every segment extracts 19 embeddings for speaker ID
2. **Full diarization**: Some videos not using fast-path
3. **I/O bottleneck**: Queue full at `io_q=10`
4. **First run**: Model loading, cache warming

## To Restore 50 videos/hour Performance

Need to investigate:
1. Why voice enrollment is so slow (19 embeddings × 5 seconds = 95s overhead per video!)
2. Why fast-path isn't being used more aggressively
3. Whether we can cache voice embeddings
4. If diarization can be skipped entirely for known monologue content

## Unit Tests

Currently NO performance unit tests exist. Should create:
- `tests/performance/test_ingestion_throughput.py`
- `tests/performance/test_speaker_counting.py`
- `tests/performance/test_fast_path_usage.py`
