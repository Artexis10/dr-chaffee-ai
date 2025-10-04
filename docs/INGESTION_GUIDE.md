# YouTube Ingestion Guide

Complete guide for ingesting YouTube videos into the Dr. Chaffee AI database.

## Quick Start

```bash
# Process 50 unprocessed videos
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 50 --limit-unprocessed
```

## Table of Contents

- [Basic Usage](#basic-usage)
- [Common Workflows](#common-workflows)
- [All Command-Line Options](#all-command-line-options)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)

## Basic Usage

### Process Unprocessed Videos (Most Common)

```bash
# Find and process 50 unprocessed videos
python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp \
  --limit 50 \
  --limit-unprocessed
```

**What it does:**
- Checks videos from newest to oldest
- Skips videos already in database
- Processes exactly 50 new videos
- Uses RTX 5080 optimizations

### Process All Unprocessed Videos

```bash
# Process ALL unprocessed videos (no limit)
python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp
```

⚠️ **Warning:** This will process ALL videos on the channel!

### Reprocess Existing Videos

```bash
# Reprocess 10 videos (even if already processed)
python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp \
  --limit 10 \
  --force
```

## Common Workflows

### 1. Daily Ingestion (Recommended)

Process new videos uploaded since yesterday:

```bash
python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp \
  --limit 20 \
  --limit-unprocessed \
  --newest-first
```

### 2. Backfill Old Videos

Process older videos in batches:

```bash
# Process 100 unprocessed videos
python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp \
  --limit 100 \
  --limit-unprocessed
```

### 3. Process Specific Video

```bash
python backend/scripts/ingest_youtube_enhanced.py \
  --from-url https://www.youtube.com/watch?v=VIDEO_ID
```

### 4. Process Multiple Videos

```bash
python backend/scripts/ingest_youtube_enhanced.py \
  --from-url \
    https://www.youtube.com/watch?v=VIDEO_ID_1 \
    https://www.youtube.com/watch?v=VIDEO_ID_2 \
    https://www.youtube.com/watch?v=VIDEO_ID_3
```

### 5. Dry Run (Preview)

See what would be processed without actually processing:

```bash
python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp \
  --limit 10 \
  --dry-run
```

### 6. Process Recent Videos Only

Process videos from the last 30 days:

```bash
python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp \
  --since-published 2024-01-01 \
  --limit-unprocessed
```

## All Command-Line Options

### Source Options

```bash
--source {api,yt-dlp,local}
```
- `yt-dlp` (recommended): Uses yt-dlp for robust downloading
- `api`: Uses YouTube Data API (requires API key)
- `local`: Process local video/audio files

```bash
--from-url URL [URL ...]
```
Process specific YouTube URL(s)

```bash
--from-json PATH
```
Process videos from JSON file

```bash
--from-files PATH
```
Process local files from directory (with `--source local`)

```bash
--file-patterns PATTERN [PATTERN ...]
```
File patterns to match (e.g., `*.mp4 *.wav`)

### Processing Options

```bash
--limit N
```
Maximum number of videos to check (default: all)

```bash
--limit-unprocessed
```
**Apply limit to unprocessed videos only** (finds N new videos)

```bash
--force, --force-reprocess
```
Reprocess videos even if they already exist in database

```bash
--skip-existing
```
Skip videos already in database (default: true)

```bash
--newest-first
```
Process newest videos first (default: true)

```bash
--skip-shorts
```
Skip videos shorter than 120 seconds

```bash
--dry-run
```
Show what would be processed without writing to DB

### Concurrency Options (RTX 5080 Optimized)

```bash
--io-concurrency N
```
I/O worker threads for download/ffmpeg (default: 12)

```bash
--asr-concurrency N
```
ASR worker threads (default: 6)

```bash
--db-concurrency N
```
DB/embedding worker threads (default: 16)

### Whisper Options

```bash
--whisper-model {tiny.en,base.en,small.en,medium.en,large-v3,distil-large-v3}
```
Whisper model size (default: distil-large-v3)

```bash
--force-whisper
```
Force Whisper transcription (skip YouTube captions)

### Date Filtering

```bash
--since-published DATE
```
Only process videos published after this date (ISO8601 or YYYY-MM-DD)

Examples:
- `--since-published 2024-01-01`
- `--since-published 2024-01-15T10:00:00Z`

### Content Filtering

```bash
--include-live
```
Include live streams (skipped by default)

```bash
--include-upcoming
```
Include upcoming streams (skipped by default)

```bash
--include-members-only
```
Include members-only content (skipped by default)

### Speaker Identification

```bash
--chaffee-min-sim FLOAT
```
Minimum similarity threshold for Chaffee identification (default: 0.62)

```bash
--chaffee-only-storage
```
Store only Chaffee segments (save space)

```bash
--embed-chaffee-only
```
Embed only Chaffee segments for search (default: true)

### Audio Storage

```bash
--no-store-audio
```
Don't store audio files locally

```bash
--production-mode
```
Production mode (disables audio storage)

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/db
YOUTUBE_API_KEY=your_youtube_api_key  # Only for --source api

# Optional
HUGGINGFACE_TOKEN=your_hf_token
OPENAI_API_KEY=your_openai_key

# Performance Tuning
IO_WORKERS=12
ASR_WORKERS=6
DB_WORKERS=16
WHISPER_MODEL=distil-large-v3

# Audio Storage
AUDIO_STORAGE_DIR=./audio_storage
```

### Performance Presets

#### Maximum Speed (RTX 5080)
```bash
python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp \
  --limit 100 \
  --limit-unprocessed \
  --io-concurrency 12 \
  --asr-concurrency 6 \
  --db-concurrency 16 \
  --whisper-model distil-large-v3
```

#### Conservative (Lower GPU Usage)
```bash
python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp \
  --limit 50 \
  --limit-unprocessed \
  --io-concurrency 4 \
  --asr-concurrency 2 \
  --db-concurrency 4
```

## Troubleshooting

### All Videos Skipped

**Problem:**
```
💡 All 50 videos were skipped (already in database)
```

**Solution:**
Use `--limit-unprocessed` to find unprocessed videos:
```bash
python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp \
  --limit 50 \
  --limit-unprocessed
```

Or increase the limit:
```bash
python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp \
  --limit 200 \
  --limit-unprocessed
```

### Database Connection Errors

**Problem:**
```
Failed to connect to database
```

**Solution:**
1. Check `.env` file has `DATABASE_URL`
2. Verify database is running
3. Test connection:
   ```bash
   psql $DATABASE_URL
   ```

### GPU Out of Memory

**Problem:**
```
CUDA out of memory
```

**Solution:**
Reduce concurrency:
```bash
python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp \
  --asr-concurrency 2 \
  --db-concurrency 8
```

### Slow Processing

**Problem:**
Processing is slower than expected

**Solution:**
1. Check GPU utilization:
   ```bash
   nvidia-smi
   ```

2. Increase concurrency if GPU is underutilized:
   ```bash
   --asr-concurrency 8
   ```

3. Use distil model for speed:
   ```bash
   --whisper-model distil-large-v3
   ```

### YouTube API Quota Exceeded

**Problem:**
```
YouTube API quota exceeded
```

**Solution:**
Switch to yt-dlp:
```bash
--source yt-dlp
```

## Performance Tuning

### Target Metrics (RTX 5080)

- **Real-Time Factor**: 0.15-0.22 (5-7x faster than real-time)
- **Throughput**: ~50 hours audio per hour
- **GPU Utilization**: ≥90%
- **VRAM Usage**: ≤9GB

### Monitoring Performance

Watch the logs for performance metrics:

```
🚀 RTX 5080 PERFORMANCE METRICS:
   Real-time factor (RTF): 0.219 (target: 0.15-0.22)
   Throughput: 15.3 hours audio per hour (target: ~50h/h)
   GPU SM utilization: 92%
```

### Optimization Tips

1. **Use distil-large-v3** for best speed/accuracy trade-off
2. **Tune concurrency** based on GPU utilization
3. **Enable monologue mode** for solo content (default)
4. **Use batched embeddings** (automatic)
5. **Store audio locally** for debugging (default)

## Examples

### Example 1: Daily Cron Job

```bash
#!/bin/bash
# Process new videos daily at 2 AM

cd /path/to/ask-dr-chaffee
source backend/venv/bin/activate

python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp \
  --limit 50 \
  --limit-unprocessed \
  --newest-first \
  >> logs/ingestion_$(date +%Y%m%d).log 2>&1
```

### Example 2: Backfill Script

```bash
#!/bin/bash
# Backfill 500 videos in batches of 50

for i in {1..10}; do
  echo "Batch $i of 10"
  python backend/scripts/ingest_youtube_enhanced.py \
    --source yt-dlp \
    --limit 50 \
    --limit-unprocessed
  sleep 60  # Cool down between batches
done
```

### Example 3: Process Specific Date Range

```bash
# Process videos from January 2024
python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp \
  --since-published 2024-01-01 \
  --limit-unprocessed
```

## Summary

### Most Common Command

```bash
# Process 50 unprocessed videos (daily workflow)
python backend/scripts/ingest_youtube_enhanced.py \
  --source yt-dlp \
  --limit 50 \
  --limit-unprocessed
```

### Key Flags to Remember

- `--limit-unprocessed` - Find N unprocessed videos
- `--force` - Reprocess existing videos
- `--dry-run` - Preview without processing
- `--newest-first` - Process recent videos first
- `--from-url` - Process specific video(s)

## Getting Help

```bash
# Show all options
python backend/scripts/ingest_youtube_enhanced.py --help

# Show version
python backend/scripts/ingest_youtube_enhanced.py --version
```

## Next Steps

- Read [DEPLOYMENT_SIMPLE.md](../DEPLOYMENT_SIMPLE.md) for deployment
- Read [RUN_TESTS.md](../RUN_TESTS.md) for testing
- Check [CICD_SETUP_GUIDE.md](../CICD_SETUP_GUIDE.md) for automation
