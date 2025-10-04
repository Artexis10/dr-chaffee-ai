# YouTube Ingestion - Quick Start

## Most Common Command

```bash
# Process 50 unprocessed videos
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 50 --limit-unprocessed
```

## What This Does

1. ✅ Checks videos from newest to oldest
2. ✅ Skips videos already in database
3. ✅ Finds exactly 50 **unprocessed** videos
4. ✅ Downloads audio using yt-dlp
5. ✅ Transcribes with Whisper (distil-large-v3)
6. ✅ Identifies speakers (Chaffee vs Guest)
7. ✅ Generates embeddings for search
8. ✅ Stores in PostgreSQL database

## Common Use Cases

### Daily Workflow
```bash
# Process new videos (run daily)
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 20 --limit-unprocessed
```

### Backfill Old Videos
```bash
# Process 100 older videos
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 100 --limit-unprocessed
```

### Process Specific Video
```bash
python backend/scripts/ingest_youtube.py --from-url https://www.youtube.com/watch?v=VIDEO_ID
```

### Preview (Dry Run)
```bash
# See what would be processed
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 10 --dry-run
```

### Reprocess Existing Videos
```bash
# Force reprocess (for testing/updates)
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 10 --force
```

## Key Flags

| Flag | What It Does |
|------|--------------|
| `--limit-unprocessed` | Find N **unprocessed** videos (most useful!) |
| `--force` | Reprocess even if already in database |
| `--dry-run` | Preview without processing |
| `--newest-first` | Process recent videos first (default) |
| `--from-url` | Process specific video(s) |

## Requirements

### Environment Variables (.env)
```bash
DATABASE_URL=postgresql://user:pass@host:5432/db
HUGGINGFACE_TOKEN=your_token  # For speaker diarization
```

### Optional
```bash
YOUTUBE_API_KEY=your_key  # Only if using --source api
OPENAI_API_KEY=your_key   # For embeddings (if not using local)
```

## Performance (RTX 5080)

- **Speed**: 5-7x faster than real-time
- **Throughput**: ~50 hours audio per hour
- **GPU Usage**: 90%+ utilization
- **Model**: distil-large-v3 (optimized)

## Troubleshooting

### All Videos Skipped?
```
💡 All 50 videos were skipped (already in database)
```

**Solution:** Use `--limit-unprocessed` to find new videos:
```bash
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 50 --limit-unprocessed
```

### Database Connection Error?
```
Failed to connect to database
```

**Solution:** Check `.env` file has `DATABASE_URL`

### GPU Out of Memory?
```
CUDA out of memory
```

**Solution:** Reduce ASR workers:
```bash
python backend/scripts/ingest_youtube.py --source yt-dlp --asr-concurrency 2
```

## Full Documentation

For complete documentation, see: [docs/INGESTION_GUIDE.md](../../docs/INGESTION_GUIDE.md)

## Help

```bash
python backend/scripts/ingest_youtube.py --help
```
