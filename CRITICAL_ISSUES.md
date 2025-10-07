# Critical Performance Issues - Summary

## Current Status: ❌ BROKEN

Processing 5 videos is taking **hours** instead of minutes. Multiple critical issues identified.

## Issue 1: ❌ AudioDecoder Error (CRITICAL)

### Error:
```
NameError: name 'AudioDecoder' is not defined
File: pyannote/audio/core/io.py, line 86
```

### Impact:
- **Diarization fails completely**
- Falls back to single speaker
- Triggers per-segment speaker ID (221 chunks!)
- 15+ minutes per video just for speaker ID

### Root Cause:
- torchcodec not properly installed
- FFmpeg DLLs missing
- pyannote v4 requires torchcodec for audio loading

### Fix Required:
Install torchcodec with FFmpeg support OR use audio preloading workaround

---

## Issue 2: ❌ Excessive Voice Embedding Extraction

### Problem:
```
Extracted 19 embeddings × 221 chunks = 4,199 embeddings per video!
Time: 3-5 seconds per chunk × 221 = 15+ minutes
```

### Why This Happens:
1. Diarization fails → single 6606s segment
2. System detects "high variance" → splits into 221 chunks
3. Extracts voice embeddings for each chunk sequentially
4. **This is the main bottleneck!**

### Fix Required:
- Fix diarization (Issue #1)
- OR optimize voice embedding extraction (batch processing)
- OR disable per-segment speaker ID when diarization fails

---

## Issue 3: ❌ Low GPU Utilization (6%)

### Problem:
```
RTX5080 SM=6% (target: >90%)
VRAM=33.6% (plenty of headroom)
```

### Why:
- Voice embedding extraction is CPU-bound (librosa)
- Sequential processing (no parallelization)
- GPU sitting idle during speaker ID

### Fix Required:
- Batch voice embedding extraction
- Use GPU for audio processing
- Parallelize speaker ID

---

## Issue 4: ⚠️ Embedding Generation Lock

### Status:
Fixed but not tested yet (added lock to prevent GPU contention)

### Expected Impact:
- Should improve embedding speed 10-20x
- But won't help if diarization is broken

---

## Priority Fix Order:

### 1. **FIX AUDIODECODER ERROR** (CRITICAL - blocks everything)
   - Install torchcodec properly
   - OR implement audio preloading workaround
   - This will fix diarization

### 2. **Optimize Voice Embedding Extraction**
   - Batch processing instead of sequential
   - Use GPU for audio loading
   - Cache embeddings

### 3. **Fix GPU Utilization**
   - Increase ASR concurrency
   - Parallelize speaker ID
   - Better pipeline balancing

---

## Expected Performance After Fixes:

### Before (Current - BROKEN):
- **5 videos**: Hours ❌
- **Diarization**: Fails ❌
- **Speaker ID**: 15+ min per video ❌
- **GPU**: 6% utilization ❌

### After (All Fixes):
- **5 videos**: 10-15 minutes ✅
- **Diarization**: Works ✅
- **Speaker ID**: <1 min per video ✅
- **GPU**: >90% utilization ✅

---

## Immediate Action Required:

**Fix AudioDecoder error first!** Everything else depends on diarization working.

### Option A: Install torchcodec properly
```bash
pip install torchcodec
# Ensure FFmpeg 4/5/6/7 is in PATH
```

### Option B: Audio preloading workaround
Modify `asr_diarize_v4.py` to preload audio before calling pyannote:
```python
import librosa
import soundfile as sf

# Preload audio
audio, sr = librosa.load(audio_path, sr=16000, mono=True)
temp_wav = "temp.wav"
sf.write(temp_wav, audio, sr)

# Pass preloaded audio to pyannote
diarization = pipeline({"waveform": torch.from_numpy(audio), "sample_rate": sr})
```

---

## Summary:

🔴 **CRITICAL**: AudioDecoder error breaks diarization
🔴 **CRITICAL**: 221× voice embedding extractions per video
🟡 **HIGH**: Low GPU utilization (6%)
🟢 **FIXED**: Embedding generation lock (not tested)

**Total time wasted per video**: 15+ minutes on broken speaker ID
**Expected time after fixes**: <1 minute

**Fix AudioDecoder first, then everything else will work!**
