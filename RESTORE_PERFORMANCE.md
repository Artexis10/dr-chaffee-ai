# Restore Performance: RTF 0.59 → 0.15

**Date**: 2025-10-11 09:24  
**Status**: Diagnostic logging added  
**Target**: Restore RTF from 0.59 to 0.15-0.22 (4x speedup)

---

## Current vs Target Performance

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| **RTF** | 0.59 | 0.15-0.22 | 4x slower |
| **Throughput** | 1.7h/hour | 50h/hour | 29x slower |
| **30 videos (16.6h)** | 9h 47m | 2h 28m | 4x slower |
| **Embedding speed** | 64.5 texts/sec | 300+ texts/sec | 5x slower |
| **GPU utilization** | 2% | 60-90% | 45x lower |

**Bottom line**: You're 4x slower than your previous working state!

---

## Root Cause: Embeddings on CPU

### Evidence
```
⚡ Embedding generation: 128 texts in 1.98s (64.5 texts/sec)  ❌ CPU!
🐌 RTX5080 SM=2% 💾 VRAM=69.5%  ❌ GPU IDLE!
```

**CPU speed**: 50-100 texts/sec  
**GPU speed**: 300-400 texts/sec  
**Your speed**: 64.5 texts/sec = **CPU!**

---

## Diagnostic Logging Added ✅

### File: `backend/scripts/common/embeddings.py`

**Changes**:
1. **Lines 62-86**: CUDA availability check + device verification
2. **Lines 142-176**: Performance timing + warnings

**New logs you'll see**:
```
✅ CUDA available: NVIDIA GeForce RTX 5080
Loading local embedding model: Alibaba-NLP/gte-Qwen2-1.5B-instruct on cuda
✅ Local embedding model loaded successfully
🔍 Requested device: cuda
🔍 Actual device: cuda:0  ← Should be cuda:0, NOT cpu
🚀 GPU acceleration enabled for embeddings (5-10x faster)

Generated 128 local embeddings in 0.4s (320.0 texts/sec)  ← Should be 300+
🚀 GPU acceleration active (320.0 texts/sec)
```

**If on CPU, you'll see**:
```
🔍 Actual device: cpu  ← PROBLEM!
⚠️  WARNING: Requested CUDA but model is on CPU!
⚠️  This will cause 5-10x slower embedding generation!

Generated 128 local embeddings in 1.98s (64.5 texts/sec)
⚠️  Slow embedding generation (64.5 texts/sec) - likely running on CPU!
⚠️  Expected GPU speed: 300+ texts/sec. Check EMBEDDING_DEVICE setting.
```

---

## Test Command

```powershell
# Test 1 video to see diagnostic logs
python backend/scripts/ingest_youtube.py --limit 1 --newest-first
```

**Watch for**:
1. Model loading logs (should show `cuda:0`)
2. Embedding generation logs (should show 300+ texts/sec)
3. GPU utilization (should jump to 60%+ during embedding)

---

## Expected Output (GPU Working)

```
2025-10-11 XX:XX:XX - INFO - scripts.common.embeddings - ✅ CUDA available: NVIDIA GeForce RTX 5080
2025-10-11 XX:XX:XX - INFO - scripts.common.embeddings - Loading local embedding model: Alibaba-NLP/gte-Qwen2-1.5B-instruct on cuda
2025-10-11 XX:XX:XX - INFO - scripts.common.embeddings - ✅ Local embedding model loaded successfully
2025-10-11 XX:XX:XX - INFO - scripts.common.embeddings - 🔍 Requested device: cuda
2025-10-11 XX:XX:XX - INFO - scripts.common.embeddings - 🔍 Actual device: cuda:0
2025-10-11 XX:XX:XX - INFO - scripts.common.embeddings - 🚀 GPU acceleration enabled for embeddings (5-10x faster)

[... processing ...]

2025-10-11 XX:XX:XX - INFO - scripts.common.embeddings - Generated 128 local embeddings in 0.4s (320.0 texts/sec)
2025-10-11 XX:XX:XX - INFO - scripts.common.embeddings - 🚀 GPU acceleration active (320.0 texts/sec)
```

---

## Expected Output (CPU Problem)

```
2025-10-11 XX:XX:XX - INFO - scripts.common.embeddings - ✅ CUDA available: NVIDIA GeForce RTX 5080
2025-10-11 XX:XX:XX - INFO - scripts.common.embeddings - Loading local embedding model: Alibaba-NLP/gte-Qwen2-1.5B-instruct on cuda
2025-10-11 XX:XX:XX - INFO - scripts.common.embeddings - ✅ Local embedding model loaded successfully
2025-10-11 XX:XX:XX - INFO - scripts.common.embeddings - 🔍 Requested device: cuda
2025-10-11 XX:XX:XX - ERROR - scripts.common.embeddings - 🔍 Actual device: cpu  ← PROBLEM!
2025-10-11 XX:XX:XX - ERROR - scripts.common.embeddings - ⚠️  WARNING: Requested CUDA but model is on CPU!
2025-10-11 XX:XX:XX - ERROR - scripts.common.embeddings - ⚠️  This will cause 5-10x slower embedding generation!

[... processing ...]

2025-10-11 XX:XX:XX - INFO - scripts.common.embeddings - Generated 128 local embeddings in 1.98s (64.5 texts/sec)
2025-10-11 XX:XX:XX - WARNING - scripts.common.embeddings - ⚠️  Slow embedding generation (64.5 texts/sec) - likely running on CPU!
2025-10-11 XX:XX:XX - WARNING - scripts.common.embeddings - ⚠️  Expected GPU speed: 300+ texts/sec. Check EMBEDDING_DEVICE setting.
```

---

## Troubleshooting Steps

### If Model Loads on CPU Despite EMBEDDING_DEVICE=cuda

**Possible causes**:

1. **PyTorch not detecting CUDA**
   ```powershell
   python -c "import torch; print(torch.cuda.is_available())"
   ```
   Should print: `True`

2. **SentenceTransformers version issue**
   ```powershell
   pip show sentence-transformers
   ```
   Should be: `>=2.0.0`

3. **CUDA/PyTorch version mismatch**
   ```powershell
   python -c "import torch; print(torch.version.cuda)"
   ```
   Should match your CUDA version (12.x)

4. **Model too large for VRAM**
   - GTE-Qwen2-1.5B needs ~4GB VRAM
   - If ASR models already using 11GB, might not fit
   - Solution: Reduce ASR workers or use smaller embedding model

### If GPU Utilization Still Low

**Check concurrency**:
```bash
# .env
ASR_WORKERS=1  # Currently 1 (safe for VRAM)
DB_WORKERS=12  # Embedding generation happens here
```

**Increase DB workers** (if VRAM allows):
```bash
DB_WORKERS=24  # More parallel embedding generation
```

---

## Performance Breakdown

### Time Spent Per Video (Current - 9h 47m for 30 videos)

```
Average per video: 19.6 minutes

Breakdown (estimated):
- Download: 1.5 min (I/O bound)
- ASR (Whisper): 4 min (GPU bound)
- Diarization: 3 min (GPU bound)
- Voice enrollment: 2 min (GPU bound)
- Embeddings: 6 min (CPU bound!) ❌ BOTTLENECK!
- DB operations: 2 min
- Other: 1 min
```

### Time Spent Per Video (Target - 2h 28m for 30 videos)

```
Average per video: 5 minutes

Breakdown (estimated):
- Download: 1 min (I/O bound)
- ASR (Whisper): 1.5 min (GPU bound, fast-path)
- Diarization: 0.5 min (GPU bound, fast-path)
- Voice enrollment: 0.5 min (GPU bound)
- Embeddings: 0.5 min (GPU bound!) ✅ FAST!
- DB operations: 0.5 min
- Other: 0.5 min
```

**Key difference**: Embeddings 6 min → 0.5 min (12x faster with GPU!)

---

## Action Plan

### Step 1: Run Diagnostic Test ✅
```powershell
python backend/scripts/ingest_youtube.py --limit 1 --newest-first
```

**Look for**:
- `🔍 Actual device: cuda:0` (good) or `cpu` (bad)
- `Generated X embeddings in Ys (Z texts/sec)` - should be 300+

### Step 2: Verify .env Setting
```bash
# .env:68
EMBEDDING_DEVICE=cuda  # Should be cuda
```

### Step 3: Check PyTorch CUDA
```powershell
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}')"
```

### Step 4: Monitor GPU During Embedding
```powershell
# Terminal 1
python backend/scripts/ingest_youtube.py --limit 1

# Terminal 2
nvidia-smi -l 1
```

Watch VRAM usage when "Generating embeddings" appears:
- **VRAM jumps**: GPU is being used ✅
- **VRAM flat**: CPU is being used ❌

### Step 5: If Still on CPU, Force GPU
```python
# embeddings.py:60 (temporary diagnostic)
embedding_device = 'cuda'  # Force GPU, ignore env
logger.warning("⚠️  FORCING GPU (diagnostic mode)")
```

---

## Success Criteria

After fix, you should see:

```
✅ Model device: cuda:0
✅ Embedding speed: 300+ texts/sec
✅ GPU utilization: 60-90% during embedding
✅ RTF: 0.15-0.22
✅ Throughput: 50h/hour
✅ 30 videos in ~2.5 hours (not 9.8 hours)
```

---

## Files Modified

1. ✅ `backend/scripts/common/embeddings.py`
   - Lines 62-86: CUDA check + device verification
   - Lines 142-176: Performance timing + warnings

---

## Next Steps

1. **Run test**: `python backend/scripts/ingest_youtube.py --limit 1`
2. **Check logs**: Look for device and speed diagnostics
3. **Report back**: Share the device and speed logs
4. **Fix if needed**: Based on diagnostic output

---

## Summary

**Problem**: Embeddings running on CPU (64.5 texts/sec) instead of GPU (300+ texts/sec)  
**Impact**: 4x slower than target (RTF 0.59 vs 0.15)  
**Fix**: Added diagnostic logging to identify root cause  
**Next**: Run 1 video test and check diagnostic logs

🚀 **Let's get your performance back to RTF 0.15!**
