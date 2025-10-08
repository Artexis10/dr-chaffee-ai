# Test Coverage Gaps - Diarization & Batching Fixes

## ✅ Existing Test Coverage

### `tests/test_asr_diarize_v4.py`
- ✅ WordItem creation
- ✅ Turn creation  
- ✅ Speaker assignment to words
- ✅ Segment creation from words
- ✅ Speaker statistics
- ✅ Speaker change detection
- ✅ Max length/words segmentation

## ❌ Missing Test Coverage

### 1. Segment Splitting at Speaker Boundaries
**File:** `backend/scripts/common/enhanced_asr.py::_split_segments_at_speaker_boundaries()`

**Needs tests for:**
- Splitting Whisper segments that cross diarization boundaries
- Using word timestamps to split accurately
- Handling segments before diarization starts (0.0 boundary)
- Preserving metadata (logprob, compression_ratio)
- No split when no boundaries crossed

**Test file:** `tests/unit/test_segment_splitting.py` (to be created)

### 2. Voice Embedding Batching
**File:** `backend/scripts/common/voice_enrollment_optimized.py::_extract_embeddings_from_audio()`

**Needs tests for:**
- Batch processing (32 segments at once)
- Fallback to sequential on batch failure
- MP4 to WAV conversion for audio loading
- Empty/invalid audio handling
- Performance verification (batching faster than sequential)

**Test file:** `tests/unit/test_voice_embedding_batching.py` (to be created)

### 3. Speaker Smoothing Logic
**File:** `backend/scripts/common/enhanced_asr.py::_identify_speakers()` (POST-PROCESSING section)

**Needs tests for:**
- Smoothing isolated segments (<60s) surrounded by same speaker
- Not smoothing segments at boundaries (first/last)
- Not smoothing longer segments (≥60s)
- Counting smoothed segments correctly

**Test file:** `tests/unit/test_speaker_smoothing.py` (to be created)

### 4. Config Threshold Usage
**File:** `backend/scripts/common/enhanced_asr.py::_identify_speakers()` (per-segment identification)

**Needs tests for:**
- Using config.chaffee_min_sim instead of hardcoded 0.65
- High confidence threshold = chaffee_threshold + 0.13
- Temporal context for medium confidence
- Debug logging of similarity scores

**Test file:** `tests/unit/test_speaker_thresholds.py` (to be created)

### 5. Text Embedding Caching
**File:** `backend/scripts/common/embeddings.py::EmbeddingGenerator`

**Needs tests for:**
- Class-level model cache shared across instances
- Model loaded only once
- Model reused for multiple batches
- Thread safety of shared cache

**Test file:** `tests/unit/test_embedding_caching.py` (to be created)

### 6. Pyannote Configuration
**File:** `backend/scripts/common/asr_diarize_v4.py::diarize_turns()`

**Needs tests for:**
- min_duration_on=0.0 parameter
- min_duration_off=0.0 parameter
- MP4 to WAV conversion
- ffmpeg availability check
- Temp file cleanup

**Test file:** `tests/unit/test_pyannote_config.py` (to be created)

## Priority Order

1. **HIGH**: Segment splitting (critical for accuracy)
2. **HIGH**: Voice embedding batching (critical for performance)
3. **MEDIUM**: Speaker smoothing (affects accuracy)
4. **MEDIUM**: Config threshold usage (affects accuracy)
5. **LOW**: Text embedding caching (performance optimization)
6. **LOW**: Pyannote configuration (edge cases)

## Test Creation Commands

```bash
# Create test files
touch tests/unit/test_segment_splitting.py
touch tests/unit/test_voice_embedding_batching.py
touch tests/unit/test_speaker_smoothing.py
touch tests/unit/test_speaker_thresholds.py
touch tests/unit/test_embedding_caching.py
touch tests/unit/test_pyannote_config.py

# Run tests
pytest tests/unit/test_segment_splitting.py -v
pytest tests/unit/test_voice_embedding_batching.py -v
pytest tests/unit/test_speaker_smoothing.py -v
```

## Notes

- All tests should use mocked audio/models to avoid GPU dependencies
- Use pytest fixtures for common test data
- Include both positive and negative test cases
- Test edge cases (empty inputs, boundary conditions)
- Verify performance improvements where applicable
