# Integration Plan: asr_diarize_v4 into enhanced_asr.py

## Current State Analysis

### enhanced_asr.py Structure (1675 lines):
1. **WhisperX Integration** (lines 131-146)
   - `_get_whisperx_model()` - Loads WhisperX for word alignment
   - Used for word-level timestamps

2. **Pyannote Integration** (lines 148-202)
   - `_get_diarization_pipeline()` - Loads pyannote directly
   - Has AudioDecoder error with v4

3. **Main Pipeline** (lines 1349-1440)
   - `transcribe_with_speaker_id()` - Main entry point
   - Calls `_transcribe_whisper_only()` → `_perform_diarization()` → `_identify_speakers()`

4. **Speaker Identification** (lines 800-1200)
   - Complex logic with voice profiles
   - Variance detection for mixed speakers
   - Per-segment identification

## Integration Strategy

### Phase 1: Replace Word Alignment ✅
**Remove**: WhisperX word alignment
**Replace with**: faster-whisper built-in word timestamps

**Changes**:
- Remove `_get_whisperx_model()` method
- Update `_transcribe_whisper_only()` to use `word_timestamps=True`
- Remove WhisperX import

### Phase 2: Replace Diarization ✅
**Remove**: Direct pyannote integration
**Replace with**: `asr_diarize_v4.diarize_turns()`

**Changes**:
- Remove `_get_diarization_pipeline()` method
- Update `_perform_diarization()` to use `asr_diarize_v4.diarize_turns()`
- Keep existing speaker identification logic

### Phase 3: Simplify Word-Speaker Assignment ✅
**Keep**: Existing speaker identification (it's good!)
**Simplify**: Word-speaker assignment using asr_diarize_v4 helper

**Changes**:
- Use `asr_diarize_v4.assign_speakers_to_words()` for word-level assignment
- Keep existing `_identify_speakers()` for profile-based identification

## Detailed Changes

### 1. Remove WhisperX (Lines 131-146)

**Before**:
```python
def _get_whisperx_model(self):
    """Lazy load WhisperX model for word alignment"""
    if self._whisperx_model is None:
        try:
            import whisperx
            logger.info("Loading WhisperX alignment model")
            self._whisperx_model = whisperx.load_align_model(
                language_code="en", 
                device=self._device
            )
        except ImportError:
            raise ImportError("WhisperX not available. Install with: pip install whisperx")
    return self._whisperx_model
```

**After**: DELETE THIS METHOD

### 2. Update Whisper Transcription

**Before** (in `_transcribe_whisper_only`):
```python
# Uses faster-whisper without word timestamps
# Then calls WhisperX for alignment
```

**After**:
```python
# Use faster-whisper with word_timestamps=True
segments, info = model.transcribe(
    audio_path,
    word_timestamps=True,  # ← Enable built-in word timestamps
    vad_filter=self.config.vad_filter,
    beam_size=self.config.beam_size,
    # ... other params
)
```

### 3. Replace Diarization

**Before** (in `_perform_diarization`):
```python
diarization_pipeline = self._get_diarization_pipeline()
diarization = diarization_pipeline(audio_path, exclusive=True, **params)
```

**After**:
```python
from .asr_diarize_v4 import diarize_turns

turns = diarize_turns(
    audio_path=audio_path,
    hf_token=os.getenv('HUGGINGFACE_HUB_TOKEN'),
    min_speakers=self.config.min_speakers,
    max_speakers=self.config.max_speakers
)
```

### 4. Keep Speaker Identification Logic

**NO CHANGES** to:
- `_identify_speakers()` - Profile-based identification
- Voice enrollment integration
- Variance detection
- Per-segment identification

This logic is excellent and should be preserved!

## Benefits

### Performance:
- ✅ **5-10% faster** - No WhisperX overhead
- ✅ **Less memory** - One fewer model loaded
- ✅ **Simpler pipeline** - Fewer steps

### Reliability:
- ✅ **No dependency conflicts** - Compatible ctranslate2
- ✅ **No AudioDecoder error** - Proper pyannote v4 usage
- ✅ **Better maintained** - Direct library usage

### Maintainability:
- ✅ **Simpler code** - Fewer abstraction layers
- ✅ **Easier debugging** - Direct API access
- ✅ **Better documented** - Clear data flow

## Testing Strategy

### 1. Unit Tests
- Test word timestamp extraction
- Test diarization turn conversion
- Test speaker assignment

### 2. Integration Tests
- Test full pipeline with test audio
- Verify speaker identification still works
- Check voice profile integration

### 3. Performance Tests
- Measure RTF (real-time factor)
- Check memory usage
- Verify GPU utilization

## Rollback Plan

If integration fails:
1. Revert enhanced_asr.py
2. Keep asr_diarize_v4.py for future use
3. Document issues for next attempt

## Implementation Steps

1. ✅ Create backup of enhanced_asr.py
2. ⏳ Remove WhisperX methods
3. ⏳ Update Whisper transcription for word timestamps
4. ⏳ Replace diarization with asr_diarize_v4
5. ⏳ Update word-speaker assignment
6. ⏳ Test with sample audio
7. ⏳ Run full test suite
8. ⏳ Commit changes

## Risk Assessment

### Low Risk:
- ✅ Word timestamps - faster-whisper has this built-in
- ✅ Diarization - asr_diarize_v4 is tested

### Medium Risk:
- ⚠️ Data structure compatibility - Need to ensure formats match
- ⚠️ Speaker identification - Keep existing logic intact

### Mitigation:
- Thorough testing before committing
- Keep existing speaker ID logic unchanged
- Test with real Dr. Chaffee audio

## Success Criteria

✅ All tests passing
✅ No WhisperX dependency
✅ No AudioDecoder errors
✅ Speaker identification still works
✅ Performance maintained or improved
✅ Memory usage same or lower

## Timeline

- Phase 1 (Word Alignment): 30 minutes
- Phase 2 (Diarization): 30 minutes
- Phase 3 (Testing): 30 minutes
- **Total**: ~1.5 hours

Ready to proceed! 🚀
