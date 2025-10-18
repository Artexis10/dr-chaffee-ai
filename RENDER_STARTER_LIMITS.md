# Render Starter Plan Configuration

## Critical Constraints

### Render Starter Plan Limits
- **RAM:** 512MB (shared)
- **CPU:** Shared CPU (no dedicated cores)
- **Disk:** 1GB ephemeral storage
- **Timeout:** 12 hours max (we use 3 hours to be safe)
- **Cost:** $7/month

### Ingestion Configuration

**Maximum Safe Settings:**
```bash
--limit 2                    # Process max 2 videos per run
--io-concurrency 2           # Minimal I/O threads
--asr-concurrency 1          # Single ASR thread (CPU-bound)
--db-concurrency 2           # Minimal DB threads
--embedding-batch-size 32    # Small batches for 512MB RAM
```

**Memory Limit:** 450MB (stay under 512MB to avoid OOM kills)

## Expected Performance

### Per-Run Metrics
- **Videos processed:** 1-2 videos
- **Time per video:** 30-60 minutes (CPU transcription is slow)
- **Total run time:** 1-2 hours
- **Memory usage:** 300-450MB peak

### Daily Capacity
- **Videos per day:** 1-2 (one cron run at 2 AM)
- **Audio hours per day:** ~1-2 hours
- **Catch-up time:** Very slow (would take months for backlog)

## Recommended Workflow

### 1. Daily Incremental Updates (Render Cron)
```bash
# Runs automatically at 2 AM daily
# Processes 1-2 newest videos only
--days-back 2 --limit 2 --limit-unprocessed
```

**Use for:**
- ✅ Daily new video ingestion
- ✅ Keeping up with recent content
- ✅ Automated maintenance

**Don't use for:**
- ❌ Bulk processing (too slow)
- ❌ Backlog catch-up (would take forever)
- ❌ Historical content (use local GPU)

### 2. Bulk Processing (Local GPU)
```bash
# Run on your local machine with RTX 5080
python3 scripts/ingest_youtube.py \
    --source yt-dlp \
    --days-back 30 \
    --limit 100 \
    --io-concurrency 12 \
    --asr-concurrency 2 \
    --db-concurrency 12
```

**Use for:**
- ✅ Initial bulk ingestion
- ✅ Historical content processing
- ✅ Backlog catch-up
- ✅ Reprocessing with new models

## Memory Optimization Tips

### 1. Environment Variables
Set in `.env` on Render (use SAME values as local):
```bash
# CRITICAL: Use same embedding model as local for consistency
EMBEDDING_PROVIDER=nomic  # Same as local
EMBEDDING_MODEL=nomic-embed-text-v1.5  # Same as local
EMBEDDING_DIMENSIONS=768  # Same as local
NOMIC_API_KEY=nk-your-key-here  # Required for Nomic API

# Whisper model - MUST use tiny.en or base.en for Render Starter
WHISPER_MODEL=tiny.en  # REQUIRED for 512MB RAM (distil-large-v3 needs 2-3GB)

# Reduce batch sizes for 512MB RAM
EMBEDDING_BATCH_SIZE=32  # Instead of 256
BATCH_SIZE=32  # Instead of 1024

# Cleanup to save disk space
CLEANUP_AUDIO_AFTER_PROCESSING=true
```

### 2. Model Configuration
**CRITICAL: Use the same models everywhere for consistency**

The ingestion script will automatically use models from `.env`:
```bash
EMBEDDING_PROVIDER=nomic
EMBEDDING_MODEL=nomic-embed-text-v1.5  # 768 dimensions
NOMIC_API_KEY=nk-your-key-here
WHISPER_MODEL=distil-large-v3  # Or whatever you're using locally
```

**Do NOT change embedding models** - this would require re-embedding all existing content.

**Nomic Benefits:**
- ✅ Free: 10M tokens/month
- ✅ Exact local/API parity (same embeddings)
- ✅ 768 dimensions (smaller than GTE-Qwen2, saves memory)

**Whisper Model - CRITICAL for Render Starter:**

❌ **distil-large-v3 will NOT work** (requires ~2-3GB RAM, Render has 512MB)

✅ **Use `tiny.en` or `base.en` instead:**
```bash
# For Render Starter (512MB RAM) - REQUIRED
WHISPER_MODEL=tiny.en  # 39M params, ~150MB RAM ✅ RECOMMENDED
# OR
WHISPER_MODEL=base.en  # 74M params, ~250MB RAM ✅ Safe alternative
```

⚠️ **Quality Trade-off:**
- `tiny.en`: Faster, less accurate (WER ~5-10% higher)
- `base.en`: Slower, better accuracy (WER ~3-5% higher than distil-large-v3)
- Both are acceptable for daily incremental updates

**For Production Quality:**
Use your local GPU with `distil-large-v3` for bulk processing, then use Render cron only for daily updates with `tiny.en`.

### 3. Monitor Memory Usage
```bash
# Check memory usage during ingestion
sudo journalctl -u drchaffee-ingest -f | grep -i "memory\|oom"

# Check systemd service memory stats
systemctl show drchaffee-ingest | grep Memory
```

## Troubleshooting

### Issue: OOM Kills (Out of Memory)
**Symptoms:**
- Service stops unexpectedly
- Logs show "Killed" or "OOM"
- Exit code 137

**Solutions:**
1. Reduce `--limit` to 1 video per run
2. Switch to `tiny.en` Whisper model
3. Reduce `--embedding-batch-size` to 16
4. Disable concurrent processing: `--io-concurrency 1 --db-concurrency 1`

### Issue: Timeouts
**Symptoms:**
- Service stops after 3 hours
- Incomplete processing

**Solutions:**
1. Reduce `--limit` to 1 video
2. Use faster Whisper model (`tiny.en`)
3. Skip long videos: `--skip-shorts` (already enabled)
4. Increase timeout in service file (max 12h on Render)

### Issue: Slow Performance
**Expected behavior:**
- CPU transcription is 10-20x slower than GPU
- 1 hour video = 2-3 hours processing time
- This is normal for Render Starter

**Not a bug, it's a feature** (of having 512MB RAM and shared CPU)

## Cost Analysis

### Render Starter Plan
- **Cost:** $7/month
- **Capacity:** 1-2 videos/day = ~30-60 videos/month
- **Cost per video:** ~$0.12-0.23

### Alternative: Upgrade to Standard
- **Cost:** $25/month
- **RAM:** 2GB (4x more)
- **CPU:** Dedicated 0.5 CPU
- **Capacity:** 5-10 videos/day = ~150-300 videos/month
- **Cost per video:** ~$0.08-0.17

### Recommendation
**Starter Plan is fine if:**
- You publish 1-2 videos per day
- You do bulk processing locally
- You're okay with 1-2 hour processing time

**Upgrade to Standard if:**
- You publish 5+ videos per day
- You need faster processing
- You don't have local GPU access

## Monitoring Checklist

### Daily
- [ ] Check cron ran successfully: `systemctl status drchaffee-ingest`
- [ ] Verify videos were processed: Check database or logs
- [ ] Monitor memory usage: No OOM kills

### Weekly
- [ ] Review error logs: `journalctl -u drchaffee-ingest --since "1 week ago"`
- [ ] Check for failed videos: Look for error patterns
- [ ] Verify embedding generation: Check database

### Monthly
- [ ] Review total videos processed
- [ ] Check for backlog accumulation
- [ ] Consider bulk processing session on local GPU

## Summary

**Render Starter Plan Configuration:**
- ✅ Works for daily incremental updates (1-2 videos)
- ✅ Very cost-effective ($7/month)
- ⚠️ Very slow (CPU transcription)
- ⚠️ Limited capacity (512MB RAM)
- ❌ Not suitable for bulk processing

**Best Practice:**
1. Use Render cron for daily updates (1-2 videos)
2. Use local GPU for bulk processing (10-100 videos)
3. Monitor memory usage to avoid OOM kills
4. Use `tiny.en` or `base.en` Whisper model
