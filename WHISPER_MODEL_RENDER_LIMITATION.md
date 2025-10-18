# Whisper Model Limitation on Render Starter

## Critical Issue

**distil-large-v3 CANNOT run on Render Starter Plan (512MB RAM)**

## Memory Requirements Comparison

| Model | Parameters | RAM Required | Render Starter? |
|-------|-----------|--------------|-----------------|
| `tiny.en` | 39M | ~150MB | ✅ YES |
| `base.en` | 74M | ~250MB | ✅ YES |
| `small.en` | 244M | ~500MB | ⚠️ RISKY |
| `medium.en` | 769M | ~1.5GB | ❌ NO |
| `distil-large-v3` | 756M | ~2-3GB | ❌ NO |
| `large-v3` | 1550M | ~4GB | ❌ NO |

### Why distil-large-v3 Fails

1. **Model file:** ~1.5GB (exceeds 1GB disk limit)
2. **Runtime memory:** 
   - Model weights: ~1.5GB
   - Activation memory: ~500MB-1GB
   - Processing overhead: ~500MB
   - **Total: 2-3GB minimum**
3. **Render Starter:** Only 512MB RAM available

## Solution: Two-Tier Strategy

### 1. Local GPU (Bulk Processing)
Use `distil-large-v3` for high-quality transcription:
```bash
# .env (local)
WHISPER_MODEL=distil-large-v3
WHISPER_COMPUTE=int8_float16
WHISPER_DEVICE=cuda
```

**Use for:**
- Initial bulk ingestion
- Historical content
- Backlog processing
- High-quality requirements

### 2. Render Cron (Daily Updates)
Use `tiny.en` or `base.en` for incremental updates:
```bash
# .env (Render)
WHISPER_MODEL=tiny.en  # Or base.en
WHISPER_COMPUTE=int8_float16
WHISPER_DEVICE=cpu
```

**Use for:**
- Daily new videos (1-2 per day)
- Automated maintenance
- Keeping up with recent content

## Quality Trade-offs

### tiny.en
- **Speed:** Fastest (~2-3x faster than base.en)
- **Accuracy:** ~5-10% higher WER than distil-large-v3
- **Memory:** ~150MB
- **Recommendation:** ✅ Best for Render Starter

### base.en
- **Speed:** Moderate (~1.5x faster than small.en)
- **Accuracy:** ~3-5% higher WER than distil-large-v3
- **Memory:** ~250MB
- **Recommendation:** ✅ Good alternative if quality matters more

### distil-large-v3
- **Speed:** Fast (5-7x faster than large-v3)
- **Accuracy:** Near large-v3 quality
- **Memory:** ~2-3GB
- **Recommendation:** ✅ Use locally only

## Recommended Workflow

### Step 1: Bulk Processing (Local GPU)
Process all historical content with high quality:
```bash
python3 scripts/ingest_youtube.py \
    --source yt-dlp \
    --days-back 365 \
    --limit 100 \
    --whisper-model distil-large-v3
```

### Step 2: Daily Updates (Render Cron)
Keep up with new content using smaller model:
```bash
# Runs automatically via systemd timer
# Uses tiny.en from .env
--days-back 2 --limit 2 --limit-unprocessed
```

### Step 3: Quality Check
Periodically re-process important videos locally:
```bash
python3 scripts/ingest_youtube.py \
    --from-url "https://youtube.com/watch?v=VIDEO_ID" \
    --force-reprocess \
    --whisper-model distil-large-v3
```

## Configuration Files

### Local (.env)
```bash
DATABASE_URL=postgresql://...
NOMIC_API_KEY=nk-...
WHISPER_MODEL=distil-large-v3
WHISPER_DEVICE=cuda
EMBEDDING_PROVIDER=nomic
```

### Render (.env)
```bash
DATABASE_URL=postgresql://...
NOMIC_API_KEY=nk-...
WHISPER_MODEL=tiny.en  # CRITICAL: Must use tiny.en or base.en
WHISPER_DEVICE=cpu
EMBEDDING_PROVIDER=nomic
```

## Performance Expectations

### Local GPU (distil-large-v3)
- **Throughput:** ~50 hours audio per hour
- **Quality:** High (near large-v3)
- **Use case:** Bulk processing

### Render Starter (tiny.en)
- **Throughput:** ~0.3-0.5x real-time
- **Quality:** Acceptable (5-10% lower than distil-large-v3)
- **Use case:** Daily incremental updates

## Migration Path

If you need better quality on Render:

### Option 1: Upgrade to Standard Plan ($25/month)
- **RAM:** 2GB (enough for base.en or small.en)
- **CPU:** Dedicated 0.5 CPU
- **Can use:** `base.en` or `small.en`

### Option 2: Use Render Pro ($85/month)
- **RAM:** 4GB (enough for distil-large-v3)
- **CPU:** Dedicated 1 CPU
- **Can use:** `distil-large-v3` ✅

### Option 3: Keep Starter + Local GPU (Recommended)
- **Cost:** $7/month
- **Quality:** Best (use distil-large-v3 locally)
- **Flexibility:** Process bulk locally, daily updates on Render

## Testing

### Test tiny.en locally first:
```bash
# Test with tiny.en to see quality
python3 scripts/ingest_youtube.py \
    --from-url "https://youtube.com/watch?v=VIDEO_ID" \
    --whisper-model tiny.en \
    --force-reprocess
```

### Compare quality:
```bash
# Process same video with both models
python3 scripts/ingest_youtube.py \
    --from-url "https://youtube.com/watch?v=VIDEO_ID" \
    --whisper-model distil-large-v3 \
    --force-reprocess

# Check segments table for differences
```

## Summary

**Bottom Line:**
- ❌ Cannot use `distil-large-v3` on Render Starter (512MB RAM)
- ✅ Must use `tiny.en` or `base.en` for Render cron
- ✅ Use `distil-large-v3` locally for bulk processing
- ✅ This two-tier approach gives best quality + cost balance

**Recommendation:** 
Use `tiny.en` on Render for daily updates, and periodically run bulk processing locally with `distil-large-v3` for high-quality transcription.
