# YouTube Ingestion Guide

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- `.env` file configured with:
  - `DATABASE_URL=postgresql://postgres:password@localhost:5432/askdrchaffee`
  - `YOUTUBE_CHANNEL_URL=https://www.youtube.com/@anthonychaffeemd`
  - `NOMIC_API_KEY=<your-key>`
  - Concurrency settings: `IO_WORKERS=24`, `ASR_WORKERS=8`, `DB_WORKERS=12`

### Start Services
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Run Migrations
```bash
docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

## Running Ingestion

### Full Channel Ingestion (Newest First)
```bash
docker-compose -f docker-compose.dev.yml exec backend python scripts/ingest_youtube.py --source yt-dlp --newest-first
```

### Incremental Ingestion (Unprocessed Videos Only)
```bash
docker-compose -f docker-compose.dev.yml exec backend python scripts/ingest_youtube.py --source yt-dlp --limit 5 --limit-unprocessed --skip-shorts --newest-first
```

### From Specific URL
```bash
docker-compose -f docker-compose.dev.yml exec backend python scripts/ingest_youtube.py --source yt-dlp --from-url "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Reprocess Existing Videos (Force)
```bash
docker-compose -f docker-compose.dev.yml exec backend python scripts/ingest_youtube.py --source yt-dlp --force-reprocess --newest-first
```
**Warning:** This reprocesses videos already in the database. Only use if you need to re-ingest.

## Monitoring

### Check Ingestion Status
```bash
docker-compose -f docker-compose.dev.yml exec backend tail -f youtube_ingestion_enhanced.log
```

### Database Status
```bash
docker exec drchaffee-db psql -U postgres -d askdrchaffee -c "SELECT COUNT(*) as sources, COUNT(*) FILTER (WHERE status='completed') as completed FROM sources;"
```

### Segment Count
```bash
docker exec drchaffee-db psql -U postgres -d askdrchaffee -c "SELECT COUNT(*) FROM segments;"
```

## Common Options

- `--source yt-dlp` - Use yt-dlp for downloading (no API key needed)
- `--newest-first` - Process newest videos first
- `--skip-shorts` - Skip videos under 120 seconds
- `--limit N` - Process only N videos
- `--limit-unprocessed` - Apply limit only to unprocessed videos
- `--force-reprocess` - Reprocess videos even if already in DB
- `--dry-run` - Show what would be processed without actually processing

## Troubleshooting

### Services not starting
```bash
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
```

### Database schema issues
```bash
docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

### Check backend logs
```bash
docker-compose -f docker-compose.dev.yml logs backend -f
```

## Performance Notes

- Full ingestion of ~1200 hours target: ~24 hours with RTX 5080
- Current concurrency: 24 I/O workers, 8 ASR workers, 12 DB workers
- Embedding model: Nomic (768 dimensions)
- ASR model: distil-large-v3 (fast, high quality)
