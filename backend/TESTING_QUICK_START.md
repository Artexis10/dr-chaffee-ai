# Testing Quick Start Guide

## Run Tests

### Unit Tests (Fast - 5 seconds)
```powershell
cd backend
py -3.11 -m pytest tests/test_ingestion_pipeline.py -v
```

### Integration Tests (Requires Network - 30+ seconds)
```powershell
cd backend
py -3.11 -m pytest tests/test_live_ingestion.py -v --run-integration
```

### All Tests
```powershell
cd backend
py -3.11 -m pytest tests/ -v
```

### Specific Test
```powershell
py -3.11 -m pytest tests/test_ingestion_pipeline.py::TestYouTubeVideoListing::test_shorts_filtering -v
```

## What's Being Tested

### Filtering
✅ **Shorts Detection** - Videos <120 seconds
- Access via: `video.is_short` property
- Filtering: `skip_shorts` flag in config

✅ **Members-Only Detection** - Subscriber-only videos
- Detected via yt-dlp error messages
- Filtered in Phase 1 pre-filter

### Data Integrity
✅ Video ID extraction from URLs
✅ Metadata completeness
✅ Duration parsing
✅ JSON parsing

### Error Handling
✅ API rate limits
✅ Network timeouts
✅ Malformed data
✅ Bot detection

### Performance
✅ Fetch speed (<2 minutes for 1300+ videos)
✅ Cache effectiveness (>10x speedup)

## Using the `is_short` Property

```python
from scripts.common.list_videos_yt_dlp import YtDlpVideoLister

lister = YtDlpVideoLister()
videos = lister.list_channel_videos("https://www.youtube.com/@anthonychaffeemd")

# Check if video is short
for video in videos:
    if video.is_short:
        print(f"Short: {video.title} ({video.duration_s}s)")
    else:
        print(f"Regular: {video.title} ({video.duration_s}s)")

# Filter shorts
regular_videos = [v for v in videos if not v.is_short]
shorts = [v for v in videos if v.is_short]

print(f"Regular: {len(regular_videos)}, Shorts: {len(shorts)}")
```

## Test Results Summary

```
✅ 11/12 tests PASSED
⏭️  1/12 tests SKIPPED (requires API key)
⏱️  Total time: 5.30 seconds

Coverage:
- Filtering logic ✅
- Error handling ✅
- Data integrity ✅
- YouTube resilience ✅
```

## Continuous Monitoring

### Weekly Integration Test
```powershell
# Add to Windows Task Scheduler or cron
py -3.11 -m pytest tests/test_live_ingestion.py -v --run-integration
```

### After YouTube Changes
1. Run integration tests
2. Check for new error patterns
3. Update detection logic if needed
4. Update test assertions

## Troubleshooting

### pytest not found
```powershell
# ❌ Wrong
pytest tests/test_ingestion_pipeline.py -v

# ✅ Correct
py -3.11 -m pytest tests/test_ingestion_pipeline.py -v
```

### Integration tests timeout
```powershell
# Increase timeout
py -3.11 -m pytest tests/test_live_ingestion.py -v --run-integration --timeout=600
```

### Tests fail after yt-dlp update
```powershell
# Update yt-dlp
pip install --upgrade yt-dlp

# Re-run tests
py -3.11 -m pytest tests/ -v
```

## Key Files

- `tests/test_ingestion_pipeline.py` - Unit tests (no network)
- `tests/test_live_ingestion.py` - Integration tests (requires network)
- `tests/conftest.py` - Pytest configuration
- `tests/README.md` - Detailed documentation
- `scripts/common/list_videos_yt_dlp.py` - VideoInfo class with `is_short` property
- `scripts/ingest_youtube.py` - Filtering logic using `is_short`
