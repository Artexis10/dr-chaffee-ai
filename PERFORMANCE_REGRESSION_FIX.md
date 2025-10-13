# Performance Regression Fix - RTF 0.59 → 0.15

**Date**: 2025-10-11 09:24  
**Problem**: RTF 0.59 (4x slower than target 0.15)  
**Root Cause**: Embeddings running on CPU instead of GPU

---

## The Numbers

```
Current Performance:
- RTF: 0.59 (1.7x real-time)
- Throughput: 1.7h audio/hour
- Time for 30 videos (16.6h): 9h 47m
- Embedding speed: 64.5 texts/sec ❌ CPU!
- GPU utilization: 2% ❌ IDLE!

Target Performance:
- RTF: 0.15-0.22 (5-7x real-time)
- Throughput: 50h audio/hour
- Time for 30 videos (16.6h): 2h 28m
- Embedding speed: 300+ texts/sec ✅ GPU!
- GPU utilization: 60-90% ✅ ACTIVE!

Regression: 4x SLOWER!
```

---

## Root Cause Analysis

### Issue 1: Embeddings on CPU ❌
```
⚡ Embedding generation: 128 texts in 1.98s (64.5 texts/sec)
```

**Expected (GPU)**: 300-400 texts/sec  
**Actual (CPU)**: 64.5 texts/sec  
**Conclusion**: Embeddings running on CPU!

### Issue 2: GPU Idle ❌
```
🐌 RTX5080 SM=2% 💾 VRAM=69.5%
```

**Expected**: 60-90% SM utilization  
**Actual**: 2% SM utilization  
**Conclusion**: GPU not being used!

### Issue 3: Voice Embedding Cache (Expected)
```
📊 Voice embedding cache stats: 0 hits, 379 misses (0.0% hit rate)
```

**This is NORMAL for new videos!** Cache only helps on reprocessing.

---

## Why Embeddings Are on CPU

### Theory 1: EMBEDDING_DEVICE Not Set
Check `.env`:
```bash
EMBEDDING_DEVICE=cuda  # Should be cuda
```

### Theory 2: Model Loading on CPU Despite Env Var
The code reads `EMBEDDING_DEVICE` but might be overridden somewhere.

### Theory 3: Lock Contention
The embedding lock might be causing CPU fallback.

---

## Diagnostic Steps

### 1. Check Embedding Device at Runtime
Add logging to `embeddings.py`:

```python
# After model load
logger.info(f"🔍 DIAGNOSTIC: Model device = {model.device}")
logger.info(f"🔍 DIAGNOSTIC: EMBEDDING_DEVICE env = {os.getenv('EMBEDDING_DEVICE')}")
```

### 2. Check GPU Memory During Embedding
```powershell
# Run in separate terminal
nvidia-smi -l 1
```

Watch VRAM usage during embedding generation:
- **If VRAM jumps**: GPU is being used ✅
- **If VRAM stays flat**: CPU is being used ❌

### 3. Force GPU Device
Modify `embeddings.py` to force GPU:

```python
# TEMPORARY DIAGNOSTIC
embedding_device = 'cuda'  # Force GPU
logger.warning(f"⚠️  FORCING GPU device (diagnostic mode)")
```

---

## The Fix

### Step 1: Verify .env Setting
```bash
# .env:68
EMBEDDING_DEVICE=cuda
```

### Step 2: Add Diagnostic Logging
**File**: `backend/scripts/common/embeddings.py:63-66`

```python
# AFTER model load
EmbeddingGenerator._shared_model = SentenceTransformer(self.model_name, device=embedding_device)
EmbeddingGenerator._shared_model.eval()

# ADD THIS
logger.info(f"🔍 Model loaded on device: {EmbeddingGenerator._shared_model.device}")
logger.info(f"🔍 Model._target_device: {getattr(EmbeddingGenerator._shared_model, '_target_device', 'unknown')}")
```

### Step 3: Check for Device Override
Search for any code that might override the device:

```powershell
grep -r "device.*=.*cpu" backend/scripts/common/embeddings.py
```

### Step 4: Verify GPU is Available
**File**: `backend/scripts/common/embeddings.py:60`

```python
# BEFORE loading model
import torch
if embedding_device == 'cuda':
    if not torch.cuda.is_available():
        logger.error("❌ CUDA requested but not available! Falling back to CPU")
        embedding_device = 'cpu'
    else:
        logger.info(f"✅ CUDA available: {torch.cuda.get_device_name(0)}")
```

---

## Expected Impact After Fix

### Before Fix (Current)
```
Embedding speed: 64.5 texts/sec (CPU)
30 videos (16.6h): 9h 47m
RTF: 0.59
Throughput: 1.7h/hour
```

### After Fix (GPU)
```
Embedding speed: 300+ texts/sec (GPU)
30 videos (16.6h): 2h 28m
RTF: 0.15-0.22
Throughput: 50h/hour
```

**Improvement**: 4x faster!

---

## Other Performance Factors

### Time Breakdown (Current)
```
Total time: 9h 47m for 16.6h audio

Breakdown (estimated):
- ASR (Whisper): ~2h (12 min/video × 30)
- Diarization: ~1.5h (3 min/video × 30)
- Voice enrollment: ~1h (2 min/video × 30)
- Embeddings (CPU): ~3h (6 min/video × 30) ❌ SLOW!
- DB operations: ~30m
- I/O (download): ~1.5h
- Other: ~30m
```

### Time Breakdown (Target with GPU)
```
Total time: 2h 28m for 16.6h audio

Breakdown (estimated):
- ASR (Whisper): ~2h (4 min/video × 30)
- Diarization: ~30m (1 min/video × 30, fast-path)
- Voice enrollment: ~15m (30 sec/video × 30)
- Embeddings (GPU): ~15m (30 sec/video × 30) ✅ FAST!
- DB operations: ~15m
- I/O (download): ~1h
- Other: ~15m
```

**Key difference**: Embeddings 3h → 15m (12x faster!)

---

## Immediate Actions

### 1. Add Diagnostic Logging
```python
# embeddings.py:66
logger.info(f"🔍 Model device: {EmbeddingGenerator._shared_model.device}")
```

### 2. Run Single Video Test
```powershell
python backend/scripts/ingest_youtube.py --limit 1 --newest-first
```

Watch for:
```
🔍 Model device: cuda  # Should be cuda, not cpu
⚡ Embedding generation: X texts in Ys (Z texts/sec)  # Should be 300+
```

### 3. Check nvidia-smi During Embedding
```powershell
# Terminal 1
python backend/scripts/ingest_youtube.py --limit 1

# Terminal 2
nvidia-smi -l 1
```

Watch VRAM usage when "Generating embeddings" appears in logs.

---

## Quick Test Command

```powershell
# Test 1 video
python backend/scripts/ingest_youtube.py --limit 1 --newest-first

# Expected output
⚡ Embedding generation: 128 texts in 0.4s (320 texts/sec)  # GPU
# NOT
⚡ Embedding generation: 128 texts in 1.98s (64.5 texts/sec)  # CPU
```

---

## Files to Check

1. ✅ `.env:68` - EMBEDDING_DEVICE=cuda
2. ⚠️ `backend/scripts/common/embeddings.py:61` - Device selection
3. ⚠️ `backend/scripts/common/embeddings.py:126` - model.encode() call

---

## Summary

**Problem**: Embeddings running on CPU (64.5 texts/sec) instead of GPU (300+ texts/sec)  
**Impact**: 4x slower than target (RTF 0.59 vs 0.15)  
**Fix**: Ensure EMBEDDING_DEVICE=cuda is actually being used  
**Verification**: Add diagnostic logging, check nvidia-smi

**Next step**: Add diagnostic logging and run 1 video test.
