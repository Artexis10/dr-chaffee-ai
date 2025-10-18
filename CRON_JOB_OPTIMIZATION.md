# Cron Job Optimization Summary

## Changes Made

### 1. **Fixed `--days-back` Parameter Implementation**

#### Problem
- Systemd service referenced `--days-back 2` parameter
- `ingest_youtube_enhanced_asr.py` didn't implement this parameter
- `ingest_youtube.py` (the correct script) used `--since-published` instead

#### Solution
- Added `--days-back` convenience parameter to `ingest_youtube.py`
- Automatically converts to `--since-published` internally
- Example: `--days-back 2` → `--since-published 2025-10-15`

### 2. **Updated Systemd Service Configuration**

#### Old Configuration (Broken)
```bash
ExecStart=/usr/bin/python3 /path/to/ask-dr-chaffee/backend/scripts/ingest_youtube_enhanced_asr.py \
    --channel-url "https://www.youtube.com/@anthonychaffeemd" \
    --days-back 2 \
    --skip-existing
```

#### New Configuration (Fixed)
```bash
ExecStart=/usr/bin/python3 /path/to/ask-dr-chaffee/backend/scripts/ingest_youtube.py \
    --source yt-dlp \
    --days-back 2 \
    --limit 2 \
    --limit-unprocessed \
    --skip-shorts \
    --newest-first \
    --io-concurrency 2 \
    --asr-concurrency 1 \
    --db-concurrency 2 \
    --embedding-batch-size 32
```

**Key Improvements:**
- Uses correct script: `ingest_youtube.py`
- **Render Starter Plan optimized** (512MB RAM, shared CPU)
- `--limit 2`: Process max 2 videos per run (avoid OOM/timeout)
- `--limit-unprocessed`: Only processes new videos (efficient)
- `--skip-shorts`: Skips videos < 120 seconds
- `--newest-first`: Prioritizes recent content
- `--embedding-batch-size 32`: Small batches to fit in 512MB RAM
- Minimal concurrency to avoid memory exhaustion

### 3. **Deprecated Old Scripts**

Moved to `backend/scripts/legacy/`:
- `ingest_youtube_enhanced_asr.py` → **DEPRECATED**

**Current Production Script:**
- `ingest_youtube.py` - RTX 5080 optimized, full feature set

### 4. **Updated Documentation**

Updated files:
- `backend/deployment/README.md` - Added note about script change
- `backend/deployment/drchaffee-ingest.service` - Updated command
- `backend/scripts/common/list_videos_yt_dlp.py` - Added `days_back` parameter

## How to Deploy

### On Production Server

```bash
# 1. Pull latest changes
cd /path/to/ask-dr-chaffee
git pull

# 2. Reload systemd configuration
sudo systemctl daemon-reload

# 3. Restart the timer
sudo systemctl restart drchaffee-ingest.timer

# 4. Verify it's working
sudo systemctl status drchaffee-ingest.timer
sudo systemctl list-timers drchaffee-ingest.timer
```

### Test Manually

```bash
# Test the ingestion command (Render Starter Plan optimized)
cd /path/to/ask-dr-chaffee/backend
python3 scripts/ingest_youtube.py \
    --source yt-dlp \
    --days-back 2 \
    --limit 2 \
    --limit-unprocessed \
    --skip-shorts \
    --newest-first \
    --io-concurrency 2 \
    --asr-concurrency 1 \
    --db-concurrency 2 \
    --embedding-batch-size 32 \
    --dry-run  # Remove for actual run
```

## Configuration Options

### Environment Variables (`.env`)

The script reads from `.env` file. **CRITICAL:** Use the same configuration on production and local:

```bash
# Required
DATABASE_URL=postgresql://...
YOUTUBE_CHANNEL_URL=https://www.youtube.com/@anthonychaffeemd

# Models (MUST match local for consistency)
EMBEDDING_PROVIDER=nomic
EMBEDDING_MODEL=nomic-embed-text-v1.5
EMBEDDING_DIMENSIONS=768
NOMIC_API_KEY=nk-your-key-here

# Whisper - Use tiny.en for Render Starter (512MB), distil-large-v3 locally
WHISPER_MODEL=tiny.en  # For Render: tiny.en or base.en only
WHISPER_COMPUTE=int8_float16

# Speaker ID (required)
ENABLE_SPEAKER_ID=true
VOICES_DIR=voices
```

### Command Line Arguments

```bash
# Process last 2 days only
--days-back 2

# Only process unprocessed videos (smart limit)
--limit-unprocessed

# Skip short videos (< 120s)
--skip-shorts

# Process newest first
--newest-first

# Dry run (no database writes)
--dry-run

# Force reprocess existing videos
--force-reprocess
```

## Monitoring

### Check Logs
```bash
# Live logs
sudo journalctl -u drchaffee-ingest -f

# Recent logs
sudo journalctl -u drchaffee-ingest -n 100

# Logs since yesterday
sudo journalctl -u drchaffee-ingest --since yesterday
```

### Check Status
```bash
# Timer status
sudo systemctl status drchaffee-ingest.timer

# Service status (last run)
sudo systemctl status drchaffee-ingest

# Next run time
sudo systemctl list-timers drchaffee-ingest.timer
```

## Performance Expectations

### Production (Render Starter Plan)
**Constraints:**
- **RAM:** 512MB (shared)
- **CPU:** Shared CPU (no dedicated cores)
- **Timeout:** 3 hours max per run

**Performance:**
- **Throughput:** ~0.2-0.3x real-time (very slow on shared CPU)
- **Daily ingestion:** 2 videos max per run (~1-2 hours)
- **Recommended:** Process 1-2 videos per day, bulk processing on local GPU

### Resource Limits (Systemd)
- **Memory:** 450MB max (stay under 512MB limit)
- **CPU:** 100% (1 shared core)
- **Timeout:** 3 hours (10800 seconds)

### Concurrency Settings (Render Starter Optimized)
- **I/O Workers:** 2 (minimal to save memory)
- **ASR Workers:** 1 (CPU transcription - single thread)
- **DB Workers:** 2 (minimal to save memory)
- **Embedding Batch:** 32 (small batches for 512MB RAM)

### Local Development (GPU)
For bulk processing, use your local machine with GPU:
```bash
python3 scripts/ingest_youtube.py \
    --source yt-dlp \
    --days-back 30 \
    --limit 100 \
    --io-concurrency 12 \
    --asr-concurrency 2 \
    --db-concurrency 12
```

## Troubleshooting

### Issue: Timer not running
```bash
# Check if enabled
sudo systemctl is-enabled drchaffee-ingest.timer

# Enable if needed
sudo systemctl enable drchaffee-ingest.timer
sudo systemctl start drchaffee-ingest.timer
```

### Issue: Service fails
```bash
# Check logs for errors
sudo journalctl -u drchaffee-ingest -n 50

# Common issues:
# 1. Missing .env file → Create from .env.example
# 2. Wrong paths → Run setup_systemd.sh again
# 3. Missing dependencies → pip install -r requirements.txt
```

### Issue: No new videos processed
```bash
# Check if videos exist in last 2 days
python3 scripts/ingest_youtube.py --source yt-dlp --days-back 2 --dry-run

# Increase days back if needed
# Edit /etc/systemd/system/drchaffee-ingest.service
# Change: --days-back 7
sudo systemctl daemon-reload
sudo systemctl restart drchaffee-ingest.timer
```

## Migration Notes

### If you were using `ingest_youtube_enhanced_asr.py`

The new script (`ingest_youtube.py`) includes all features plus:
- ✅ Better performance (RTX 5080 optimized)
- ✅ More robust error handling
- ✅ Better GPU memory management
- ✅ Improved speaker identification
- ✅ Segment optimization for RAG
- ✅ `--days-back` parameter support

**No action needed** - the systemd service is already updated.

### Critical: Model Consistency

**IMPORTANT:** The cron job uses the same models as your local environment via `.env`:
```bash
# These MUST match your local configuration
EMBEDDING_PROVIDER=nomic
EMBEDDING_MODEL=nomic-embed-text-v1.5
EMBEDDING_DIMENSIONS=768
NOMIC_API_KEY=nk-your-key-here

# Whisper: Use tiny.en for Render Starter (512MB RAM limit)
WHISPER_MODEL=tiny.en  # distil-large-v3 requires 2-3GB RAM
```

**Do NOT change embedding models** - this would create inconsistent embeddings and break semantic search. All content must use the same embedding model (Nomic v1.5).

### Breaking Changes
None - all functionality is preserved or improved.

## Next Steps

1. **Deploy to production** using steps above
2. **Monitor first run** to ensure it works
3. **Adjust `--days-back`** if needed (default: 2 days)
4. **Set up alerts** for failed runs (optional)

## Related Files

- `backend/scripts/ingest_youtube.py` - Main ingestion script
- `backend/deployment/drchaffee-ingest.service` - Systemd service
- `backend/deployment/drchaffee-ingest.timer` - Systemd timer
- `backend/deployment/setup_systemd.sh` - Setup script
- `backend/deployment/README.md` - Deployment guide
