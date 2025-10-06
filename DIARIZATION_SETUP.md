# Speaker Diarization Setup - Dr. Chaffee AI Pipeline

## ✅ Current Configuration

### Model
- **Model:** `pyannote/speaker-diarization-community-1`
- **Version:** pyannote.audio 4.0.0
- **Status:** ✅ Verified working

### Implementation

```python
from pyannote.audio import Pipeline
import os

# Load pipeline
hf_token = os.getenv("HUGGINGFACE_HUB_TOKEN")
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    token=hf_token  # pyannote 4.x uses 'token' parameter
)

# Run diarization (expects 16 kHz mono WAV)
diarization = pipeline("audio.wav")

# Iterate through results
for turn, _, speaker in diarization.itertracks(yield_label=True):
    print(f"{turn.start:.2f} {turn.end:.2f} {speaker}")
```

## Configuration Files

### 1. Model Configuration
**File:** `backend/scripts/common/enhanced_asr_config.py`
```python
diarization_model: str = "pyannote/speaker-diarization-community-1"
```

### 2. Environment Variables
**File:** `.env`
```bash
# Required
HUGGINGFACE_HUB_TOKEN=hf_your_token_here
ENABLE_SPEAKER_ID=true

# Optional tuning
PYANNOTE_CLUSTERING_THRESHOLD=0.6  # Lower = more sensitive (default: 0.7)
ASSUME_MONOLOGUE=false  # Must be false to detect guests
ENABLE_FAST_PATH=false  # Disable to force diarization
```

## Community-1 Advantages

1. **Improved speaker assignment** - Better accuracy in identifying who said what
2. **Better speaker counting** - More accurate detection of number of speakers  
3. **Simpler reconciliation** - Exclusive speaker diarization (no overlaps)
4. **Offline use** - Can run without internet after download
5. **Optimized for production** - Better performance and reliability

## Verification

### Test Script
Run `test_pyannote_direct.py` to verify setup:
```bash
python test_pyannote_direct.py
```

Expected output:
```
================================================================================
PYANNOTE IS WORKING CORRECTLY!
================================================================================
```

### Integration Test
Run `test_new_profile_live.py` to test full pipeline:
```bash
python test_new_profile_live.py
```

Look for:
```
================================================================================
PYANNOTE DETECTED X SPEAKERS
================================================================================
```

## Error Logging

The pipeline now has prominent error logging:

### If Pyannote Fails to Load
```
================================================================================
CRITICAL WARNING: Pyannote diarization FAILED to load!
Using fallback single-speaker mode - interviews will be mislabeled!
================================================================================
```

### If Fallback is Used
```
================================================================================
CRITICAL: USING FALLBACK DIARIZATION (SINGLE SPEAKER)!
Pyannote is NOT running - all audio will be labeled as one speaker!
This WILL cause incorrect attribution in interviews!
================================================================================
```

### If Only 1 Speaker Detected
```
WARNING: Only 1 speaker detected - may be monologue or clustering too aggressive
Consider lowering PYANNOTE_CLUSTERING_THRESHOLD if this is an interview
```

## Troubleshooting

### Issue: All speakers labeled as Chaffee
**Cause:** Pyannote detecting only 1 speaker
**Solutions:**
1. Lower `PYANNOTE_CLUSTERING_THRESHOLD` (try 0.5 or 0.4)
2. Verify audio quality (16 kHz mono WAV)
3. Check if voices are genuinely very similar
4. Ensure `ASSUME_MONOLOGUE=false` and `ENABLE_FAST_PATH=false`

### Issue: Pyannote fails to load
**Cause:** Missing token or model download issue
**Solutions:**
1. Verify `HUGGINGFACE_HUB_TOKEN` is set correctly
2. Accept model conditions at https://huggingface.co/pyannote/speaker-diarization-community-1
3. Check internet connection for first download
4. Run `test_pyannote_direct.py` to diagnose

### Issue: "use_auth_token" error
**Cause:** Using pyannote 3.x syntax with 4.x
**Solution:** Use `token=` parameter instead of `use_auth_token=`

## Voice Profile

### Current Profile
- **File:** `voices/chaffee.json`
- **Dimensions:** 192 (ECAPA-TDNN for speaker identification)
- **Embeddings:** 90,224 from 18 high-quality videos
- **Model:** Simplified ECAPA-TDNN
- **Status:** ✅ Working correctly

### Profile vs Diarization
- **Voice Profile (192 dims):** Identifies if speaker is Chaffee
- **Diarization:** Separates speakers in audio
- **Text Embeddings (1536 dims):** Semantic search (separate system)

## Pipeline Flow

```
Audio Input (16 kHz mono WAV)
    ↓
Pyannote Diarization (community-1)
    ↓
Speaker Segments [(start, end, speaker_id), ...]
    ↓
Whisper Transcription
    ↓
Merge Segments with Transcripts
    ↓
Voice Profile Matching (Chaffee vs Guest)
    ↓
Final Segments with Speaker Labels
```

## Status Summary

✅ **Pyannote 4.0** installed and working  
✅ **community-1 model** loaded successfully  
✅ **Voice profile** regenerated (192 dims, 90K embeddings)  
✅ **Error logging** prominent and clear  
✅ **Test scripts** available for validation  
✅ **Configuration** optimized for multi-speaker detection  

## Next Steps

1. ✅ Pyannote setup complete
2. ⏳ Test with interview video (in progress)
3. ⏳ Verify multi-speaker detection
4. ⏳ Tune clustering threshold if needed
5. ⏳ Resume full ingestion pipeline

---

**Last Updated:** 2025-10-06  
**Pyannote Version:** 4.0.0  
**Model:** pyannote/speaker-diarization-community-1
