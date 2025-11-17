# Ingestion Pipeline Testing

## Overview
Comprehensive test suite for YouTube ingestion pipeline to detect breaking changes from YouTube updates or code modifications.

## Test Files

### `test_ingestion_pipeline.py`
**Unit tests** - Fast, no network required
- ✅ Shorts filtering (<120s)
- ✅ Members-only detection
- ✅ Duration edge cases
- ✅ Error handling (rate limits, timeouts, malformed data)
- ✅ Video ID extraction
- ✅ Metadata completeness

### `test_live_ingestion.py`
**Integration tests** - Requires network, tests against real YouTube
- ✅ yt-dlp fetches all 1300+ videos
- ✅ Shorts detection accuracy
- ✅ Members-only filtering
- ✅ YouTube API fallback
- ✅ Performance benchmarks
- ✅ Resilience to YouTube changes

## Running Tests

### Unit Tests (Fast)
```bash
cd backend
pytest tests/test_ingestion_pipeline.py -v
```

### Integration Tests (Requires Network)
```bash
cd backend
pytest tests/test_live_ingestion.py -v --run-integration
```

### All Tests
```bash
cd backend
pytest tests/ -v --run-integration
```

### Run Specific Test
```bash
pytest tests/test_ingestion_pipeline.py::TestYouTubeVideoListing::test_shorts_filtering -v
```

## Current Status

### Filtering Verification
✅ **Shorts filtering:** Videos <120s are filtered (line 700 in `ingest_youtube.py`)
✅ **Members-only filtering:** Detected via yt-dlp error messages (lines 1909-1913)

### Detection Patterns
Members-only videos are identified by these error messages:
- `"members-only"` in error
- `"join this channel"` in error  
- `"available to this channel's members"` in error

### Test Results
- **Unit tests:** 11/12 passed (1 skipped - no API key)
- **Integration tests:** Not run yet (require `--run-integration` flag)

## CI/CD Integration

### GitHub Actions (Recommended)
```yaml
name: Test Ingestion Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/test_ingestion_pipeline.py -v
      
  integration:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/test_live_ingestion.py -v --run-integration
        env:
          YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
```

### Manual Monitoring
Run integration tests weekly to detect YouTube changes:
```bash
# Add to cron or Windows Task Scheduler
pytest tests/test_live_ingestion.py -v --run-integration
```

## What Tests Detect

### YouTube Changes
- ✅ Video listing endpoint changes
- ✅ Metadata format changes
- ✅ Error message changes
- ✅ Rate limiting changes
- ✅ Bot detection measures

### Code Regressions
- ✅ Filtering logic breaks
- ✅ Duration parsing errors
- ✅ Members-only detection fails
- ✅ Performance degradation
- ✅ Data integrity issues

## Adding New Tests

### Unit Test Template
```python
def test_new_feature(self):
    """Test description"""
    # Arrange
    input_data = ...
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_value
```

### Integration Test Template
```python
@pytest.mark.integration
def test_live_feature(self):
    """Test against real YouTube"""
    lister = YtDlpVideoLister()
    videos = lister.list_channel_videos(CHANNEL_URL)
    
    assert len(videos) > MIN_EXPECTED
```

## Troubleshooting

### Tests Fail After YouTube Update
1. Check if yt-dlp needs updating: `pip install --upgrade yt-dlp`
2. Review error messages for new patterns
3. Update detection logic in `ingest_youtube.py`
4. Update test assertions

### Integration Tests Timeout
- Increase timeout in `pytest.ini`: `timeout = 600`
- Check network connectivity
- Verify YouTube is accessible

### False Positives
- Review test assertions
- Check for flaky tests (timing-dependent)
- Add retries for network tests

## Maintenance

### Weekly
- Run integration tests to detect YouTube changes
- Review test output for warnings

### Monthly
- Update yt-dlp: `pip install --upgrade yt-dlp`
- Review and update test expectations
- Check for new YouTube error patterns

### After Code Changes
- Run all unit tests
- Run integration tests before merging
- Update tests if behavior changes intentionally
