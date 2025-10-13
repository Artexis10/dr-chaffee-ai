# CUDA Out-of-Memory (OOM) Fix for Long Videos

## Problem
CUDA OOM errors occur during voice embedding extraction and Whisper transcription for long videos (>30 minutes), causing the pipeline to fail completely.

**Error symptoms**:
```
CUDA error: out of memory
❌ Batch processing failed, falling back to sequential: CUDA error: out of memory
Extracted 0 embeddings from audio file
```

## Root Causes
1. **Voice embedding extraction**: Loads entire audio file into memory, then processes all segments
2. **Whisper transcription**: GPU memory not freed between operations
3. **Long videos**: 1h50m video (6606 seconds) exceeds GPU memory capacity
```

**No model downgrades** - keeping `distil-large-v3` and `gte-Qwen2-1.5B`

**Fallback if needed:**
If OOM still occurs, reduce to `ASR_WORKERS=2` in `.env`

## Status

- [x] Fixed preprocessing_config error
- [x] Added GPU memory cleanup
- [x] Kept ASR workers at 4 (with cleanup)
- [ ] Test with full pipeline
- [ ] Monitor VRAM usage stays < 80%
- [ ] Verify success rate > 90%
- [ ] If OOM persists, reduce ASR_WORKERS to 2

## Next Steps

1. **Restart the pipeline** - Changes are committed
2. **Monitor VRAM** - Should stay stable now
3. **Check success rate** - Should be ~95% instead of 22%
