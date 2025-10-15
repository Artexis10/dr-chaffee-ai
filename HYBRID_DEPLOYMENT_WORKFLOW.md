# 🔄 Hybrid Deployment Workflow - Local GPU + Production CPU

## Overview

**Local Machine (Your RTX 5080)**:
- Bulk historical processing (1200h backlog)
- Large batch ingestion (50-200 videos)
- Full GPU acceleration (40-50h audio/hour)

**Production Server (CPU Only)**:
- Daily cron job for new uploads (~2h/day)
- CPU processing (slower but sufficient)
- Runs overnight (2 AM → 8 AM)

---

## 📋 Initial Setup (One-Time)

### 1. Local Environment (Your Machine)

```powershell
cd C:\Users\hugoa\Desktop\ask-dr-chaffee\backend

# Verify .env is configured for GPU
cat .env | Select-String "EMBEDDING_DEVICE"
# Should show: EMBEDDING_DEVICE=cuda

# Test GPU performance
python scripts/test_embedding_speed.py
# Should see: 170+ texts/sec
```

### 2. Production Server Setup

```bash
# On production server
cd /path/to/ask-dr-chaffee/backend

# Copy CPU-optimized config
cp .env.production.cpu .env

# Edit with production credentials
nano .env
# Update: DATABASE_URL, OPENAI_API_KEY, etc.

# Install dependencies
pip install -r requirements.txt

# Test CPU performance (should be slower but functional)
python scripts/test_embedding_speed.py
# Expected: 10-15 texts/sec (acceptable for daily cron)
```

---

## 🚀 Workflow: Local Bulk Processing

### Step 1: Process Historical Content Locally

```powershell
cd C:\Users\hugoa\Desktop\ask-dr-chaffee\backend

# Create video list (all historical content)
# Option A: From channel
python scripts/ingest_youtube_enhanced_asr.py --channel-url "https://www.youtube.com/@anthonychaffeemd" --batch-size 200

# Option B: From video ID list
python scripts/ingest_youtube_enhanced_asr.py --video-ids-file historical_videos.txt --batch-size 200
```

**Expected Performance**:
- **Throughput**: 40-50h audio/hour
- **200 videos (~150h)**: 3-4 hours
- **1200h backlog**: 24-30 hours

### Step 2: Export Database from Local

```powershell
# Export entire database
pg_dump -h localhost -U postgres askdrchaffee > drchaffee_backup_$(Get-Date -Format "yyyyMMdd").sql

# Or export only new data (if database already exists in production)
pg_dump -h localhost -U postgres askdrchaffee --data-only --table=segments --table=sources > drchaffee_incremental.sql
```

### Step 3: Transfer to Production

```bash
# Option A: Direct database connection (fastest)
# From local machine, connect directly to production DB
psql "postgresql://user:pass@production-server:5432/askdrchaffee" < drchaffee_backup.sql

# Option B: SCP file transfer
scp drchaffee_backup_20251015.sql user@production-server:/tmp/
# Then on production server:
psql askdrchaffee < /tmp/drchaffee_backup_20251015.sql

# Option C: Secure tunnel
ssh -L 5433:localhost:5432 user@production-server
# Then from local:
psql -h localhost -p 5433 -U postgres askdrchaffee < drchaffee_backup.sql
```

---

## 🔄 Daily Workflow: Production Cron Job

### Setup Cron Job on Production Server

```bash
# Create cron script
cat > /path/to/ask-dr-chaffee/backend/scripts/daily_ingest.sh << 'EOF'
#!/bin/bash
set -e

# Change to backend directory
cd /path/to/ask-dr-chaffee/backend

# Activate virtual environment (if using one)
# source venv/bin/activate

# Log start time
echo "=== Daily ingestion started at $(date) ===" >> logs/cron.log

# Ingest new videos from last 2 days (safety margin)
python scripts/ingest_youtube_enhanced_asr.py \
  --channel-url "https://www.youtube.com/@anthonychaffeemd" \
  --days-back 2 \
  --skip-existing \
  >> logs/cron.log 2>&1

# Log completion
echo "=== Daily ingestion completed at $(date) ===" >> logs/cron.log
echo "" >> logs/cron.log

# Optional: Send notification
# curl -X POST "https://your-monitoring-service.com/webhook" -d "status=success"
EOF

chmod +x /path/to/ask-dr-chaffee/backend/scripts/daily_ingest.sh
```

### Add to Crontab

```bash
crontab -e

# Add this line (runs at 2 AM daily)
0 2 * * * /path/to/ask-dr-chaffee/backend/scripts/daily_ingest.sh

# Or with explicit PATH (recommended)
0 2 * * * PATH=/usr/local/bin:/usr/bin:/bin /path/to/ask-dr-chaffee/backend/scripts/daily_ingest.sh
```

### Expected Daily Performance

**For 2 hours of new content**:
- **Download**: 10-15 minutes
- **Whisper (CPU, base model)**: 2-3 hours
- **Embeddings (CPU, BGE-Small)**: 1-2 hours
- **Voice enrollment (CPU)**: 30-60 minutes
- **Database writes**: 15-30 minutes
- **Total**: 4-6 hours

**Cron schedule**: 2 AM → 8 AM (completes before business hours)

---

## 📊 Performance Comparison

| Task | Local (GPU) | Production (CPU) | Ratio |
|------|-------------|------------------|-------|
| **Whisper ASR** | 5-7x real-time | 0.5x real-time | 10-14x faster |
| **Embeddings** | 170 texts/sec | 10-15 texts/sec | 11-17x faster |
| **Voice Enrollment** | 10-15 emb/sec | 1-2 emb/sec | 5-10x faster |
| **Overall** | 40-50h/hour | 0.3-0.5h/hour | 80-150x faster |

**For 2h of content**:
- Local: ~3-5 minutes
- Production: ~4-6 hours

---

## 🔧 Configuration Differences

### Local `.env` (GPU)
```bash
WHISPER_MODEL=distil-large-v3  # High quality
WHISPER_DEVICE=cuda
EMBEDDING_PROFILE=quality  # GTE-Qwen2-1.5B (1536-dim)
EMBEDDING_DEVICE=cuda
EMBEDDING_BATCH_SIZE=256
VOICE_ENROLLMENT_BATCH_SIZE=16
IO_WORKERS=12
ASR_WORKERS=2
DB_WORKERS=12
```

### Production `.env` (CPU)
```bash
WHISPER_MODEL=base  # Faster for CPU
WHISPER_DEVICE=cpu
EMBEDDING_PROFILE=speed  # BGE-Small (384-dim)
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=32
VOICE_ENROLLMENT_BATCH_SIZE=4
ENABLE_RERANKER=true  # Compensate for smaller model
IO_WORKERS=4
ASR_WORKERS=1
DB_WORKERS=4
```

---

## 🎯 Quality Trade-offs (Production CPU)

### Whisper Model Change
- **Local**: `distil-large-v3` (WER: ~3-4%)
- **Production**: `base` (WER: ~5-6%)
- **Impact**: Slightly more transcription errors, but acceptable for daily content

### Embedding Model Change
- **Local**: GTE-Qwen2-1.5B (1536-dim, best quality)
- **Production**: BGE-Small (384-dim, with reranker)
- **Impact**: 3-5% quality loss, compensated by reranker

### Overall Quality
- **Search relevance**: 90-95% as good as GPU version
- **Answer generation**: No impact (uses same GPT-4o)
- **Speaker attribution**: Same quality (model size doesn't affect this)

**Trade-off is acceptable** for daily incremental updates.

---

## 🔄 Periodic Bulk Reprocessing

### When to Reprocess Locally

Run bulk reprocessing on your local GPU when:
1. **Quality improvements**: New models available
2. **Backfill gaps**: Videos missed by daily cron
3. **Configuration changes**: Updated speaker profiles, thresholds
4. **Database corruption**: Need to rebuild from scratch

### Reprocessing Workflow

```powershell
# On local machine
cd C:\Users\hugoa\Desktop\ask-dr-chaffee\backend

# Get list of videos needing reprocessing
python scripts/find_videos_needing_reprocessing.py > reprocess_list.txt

# Reprocess with --force flag
python scripts/ingest_youtube_enhanced_asr.py --video-ids-file reprocess_list.txt --force --batch-size 100

# Export and sync to production
pg_dump -h localhost -U postgres askdrchaffee > drchaffee_reprocessed.sql
scp drchaffee_reprocessed.sql user@production-server:/tmp/
```

---

## 📈 Monitoring Production Cron

### Check Cron Logs

```bash
# View recent cron output
tail -f /path/to/ask-dr-chaffee/backend/logs/cron.log

# Check for errors
grep -i error /path/to/ask-dr-chaffee/backend/logs/cron.log

# Monitor processing time
grep "Daily ingestion" /path/to/ask-dr-chaffee/backend/logs/cron.log
```

### Success Indicators

```bash
# Should see in logs:
✅ Successfully processed X videos
✅ Generated Y embeddings
✅ Inserted Z segments
=== Daily ingestion completed at [timestamp] ===
```

### Failure Recovery

```bash
# If cron fails, manually run:
cd /path/to/ask-dr-chaffee/backend
python scripts/ingest_youtube_enhanced_asr.py --channel-url "..." --days-back 3 --skip-existing

# Check what failed
python scripts/check_missing_videos.py
```

---

## 🚨 Troubleshooting

### Issue: Cron Job Takes Too Long (>8 hours)

**Solutions**:
1. Reduce quality further:
   ```bash
   WHISPER_MODEL=tiny  # Fastest model
   SKIP_VOICE_EMBEDDINGS=true  # Skip speaker ID
   ```

2. Process in smaller chunks:
   ```bash
   # Split daily job into 2 runs (AM and PM)
   0 2 * * * /path/to/daily_ingest.sh --max-videos 5
   0 14 * * * /path/to/daily_ingest.sh --max-videos 5
   ```

3. Upgrade production server CPU

### Issue: Database Sync Fails

**Solutions**:
1. Use incremental sync:
   ```bash
   # Only sync new segments
   pg_dump --data-only --table=segments --where="created_at > '2025-10-15'" askdrchaffee > incremental.sql
   ```

2. Use logical replication (PostgreSQL 10+)

3. Use application-level sync (custom script)

### Issue: Quality Degradation on Production

**Solutions**:
1. Enable reranker (if not already):
   ```bash
   ENABLE_RERANKER=true
   ```

2. Increase reranker top-k:
   ```bash
   RERANK_TOP_K=300  # From 200
   ```

3. Periodically reprocess with local GPU:
   ```bash
   # Monthly reprocessing of last 30 days
   python scripts/ingest_youtube_enhanced_asr.py --days-back 30 --force
   ```

---

## ✅ Deployment Checklist

### Local Setup
- [x] `.env` configured with GPU settings
- [x] GPU tests passing (170+ texts/sec)
- [x] Database accessible
- [x] Bulk processing tested

### Production Setup
- [ ] `.env.production.cpu` copied to `.env`
- [ ] Production credentials configured
- [ ] Dependencies installed
- [ ] Cron job configured
- [ ] Log directory created
- [ ] Test run successful

### Database Sync
- [ ] Initial bulk data transferred
- [ ] Database schema matches
- [ ] Indexes created
- [ ] Backup strategy in place

### Monitoring
- [ ] Cron logs accessible
- [ ] Error alerting configured
- [ ] Disk space monitoring
- [ ] Database size monitoring

---

## 🎯 Summary

**Your hybrid approach is optimal**:
- ✅ Use local GPU for heavy lifting (1200h backlog)
- ✅ Use production CPU for daily maintenance (2h/day)
- ✅ Sync databases periodically
- ✅ Quality trade-off is acceptable for daily updates

**Expected timeline**:
- **Initial bulk**: 24-30 hours on local GPU
- **Daily cron**: 4-6 hours on production CPU (overnight)
- **Database sync**: 10-30 minutes

**You're ready to deploy!** 🚀
