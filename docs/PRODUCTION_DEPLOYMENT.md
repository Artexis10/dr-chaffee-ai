# Production Deployment Guide

Guide for deploying Dr. Chaffee AI to production without GPU.

## Architecture

### Hybrid Processing Model

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL MACHINE (GPU)                       │
│  - RTX 5080 for fast processing                            │
│  - Bulk ingestion (1200h audio in ~24h)                    │
│  - Initial corpus processing                                │
│  - Historical backlog                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ One-time bulk sync
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  PRODUCTION (CPU-only)                       │
│  - Serves API requests (fast)                               │
│  - Semantic search on embeddings                            │
│  - Incremental processing (new videos only)                 │
│  - CPU is fine for 1-2 videos/day                          │
│  - Cost: ~$30/month                                         │
└─────────────────────────────────────────────────────────────┘
```

### Why This Works

**Bulk Processing (Local GPU)**
- Process 1200h historical content once
- Takes ~24h with RTX 5080
- One-time operation

**Incremental Processing (Production CPU)**
- Only 1-2 new videos per day (~30min audio)
- CPU can handle this easily (~3-5 hours)
- Runs overnight, ready by morning
- Cheap and sustainable

## Production Configuration

### Environment Variables

```bash
# .env.production
DATABASE_URL=postgresql://user:pass@host:5432/db

# CPU-only mode (no GPU needed)
CUDA_VISIBLE_DEVICES=""
TORCH_DEVICE=cpu

# Enable lightweight incremental processing
ENABLE_INGESTION=true  # Allow processing new videos
INCREMENTAL_ONLY=true  # Only process new videos, not bulk

# Scheduled ingestion (daily at 2 AM)
INGESTION_SCHEDULE="0 2 * * *"  # Cron format
INGESTION_LIMIT=5  # Process max 5 new videos per day
```

### requirements-production.txt

Create a minimal production requirements file:

```txt
# Core API dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
psycopg2-binary>=2.9.9
sqlalchemy>=2.0.07
alembic>=1.13.0

# Embeddings (CPU-only)
sentence-transformers==2.2.2
torch>=2.2.0,<2.9.0  # CPU version is fine
transformers==4.33.2

# Utilities
python-dotenv==1.0.0
numpy>=1.24.3,<2.0.0
tqdm==4.66.1

# Note: No whisperx, pyannote, librosa needed in production
# These are only for ingestion which happens locally
```

## Deployment Steps

### 1. Local Processing (GPU Machine)

```bash
# Run bulk ingestion locally with GPU
python backend/scripts/ingest_youtube.py \
  --source yt-dlp \
  --limit 1200 \
  --limit-unprocessed \
  --store-audio-locally

# This will:
# - Download videos
# - Transcribe with Whisper (GPU)
# - Identify speakers (GPU)
# - Generate embeddings (GPU)
# - Store in local database
```

### 2. Database Replication

#### Option A: pg_dump/pg_restore (Recommended)

```bash
# On local machine: Export database
pg_dump $LOCAL_DATABASE_URL > dr_chaffee_backup.sql

# On production: Import database
psql $PRODUCTION_DATABASE_URL < dr_chaffee_backup.sql
```

#### Option B: Continuous Replication

```bash
# Set up PostgreSQL logical replication
# Local DB → Production DB (read replica)

# On local (primary):
ALTER SYSTEM SET wal_level = logical;
CREATE PUBLICATION dr_chaffee_pub FOR ALL TABLES;

# On production (replica):
CREATE SUBSCRIPTION dr_chaffee_sub 
  CONNECTION 'postgresql://local_host:5432/db' 
  PUBLICATION dr_chaffee_pub;
```

#### Option C: Incremental Sync

```bash
# Export only new data since last sync
pg_dump --data-only \
  --table=sources \
  --table=segments \
  --where="created_at > '2025-10-05'" \
  $LOCAL_DATABASE_URL > incremental.sql

# Import to production
psql $PRODUCTION_DATABASE_URL < incremental.sql
```

### 3. Production Deployment

#### Docker (Recommended)

```dockerfile
# Dockerfile.production
FROM python:3.12-slim

# Install only production dependencies
COPY requirements-production.txt /app/
RUN pip install --no-cache-dir -r /app/requirements-production.txt

# Copy API code only (no ingestion scripts)
COPY backend/api /app/backend/api
COPY backend/scripts/common/embeddings.py /app/backend/scripts/common/

# Set environment
ENV API_ONLY_MODE=true
ENV TORCH_DEVICE=cpu
ENV ENABLE_INGESTION=false

# Run API
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Railway/Render

```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "pip install -r requirements-production.txt && uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "envVars": {
      "API_ONLY_MODE": "true",
      "TORCH_DEVICE": "cpu",
      "ENABLE_INGESTION": "false"
    }
  }
}
```

## Safety Checks

### Prevent Accidental Ingestion in Production

Add to `backend/scripts/ingest_youtube.py`:

```python
def main():
    """Main entry point"""
    # Safety check: prevent ingestion in production
    if os.getenv('API_ONLY_MODE') == 'true':
        logger.error("❌ Ingestion disabled in API_ONLY_MODE")
        logger.error("Run ingestion locally with GPU, then replicate database")
        sys.exit(1)
    
    # ... rest of main()
```

### Database Connection Check

```python
# Check if database is read-only
def check_database_mode():
    """Check if database is in read-only mode"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    cur.execute("SHOW transaction_read_only")
    read_only = cur.fetchone()[0] == 'on'
    conn.close()
    return read_only

if check_database_mode():
    logger.info("✅ Database in read-only mode (production)")
else:
    logger.warning("⚠️  Database is writable")
```

## CPU-Only Performance

### What Works on CPU

✅ **API requests** - Fast  
✅ **Semantic search** - Fast (embeddings already generated)  
✅ **Database queries** - Fast  
✅ **Embedding similarity** - Fast (numpy operations)  

### What's Slow on CPU (Don't Run in Production)

❌ **Whisper transcription** - 100x slower than GPU  
❌ **Speaker diarization** - 50x slower than GPU  
❌ **Embedding generation** - 10x slower than GPU  

## Workflow

### Initial Setup (One-Time)

```bash
# Step 1: Bulk processing on local GPU machine
python backend/scripts/ingest_youtube.py \
  --source yt-dlp \
  --limit 1200 \
  --limit-unprocessed

# Step 2: Sync to production
export LOCAL_DATABASE_URL=postgresql://localhost/dr_chaffee_local
export PRODUCTION_DATABASE_URL=postgresql://prod_host/dr_chaffee_prod
python backend/scripts/sync_to_production.py

# Step 3: Deploy production with scheduled ingestion
# Production will now handle new videos automatically
```

### Daily Operations (Automatic)

```bash
# Production runs scheduled ingestion daily at 2 AM
# Processes 1-2 new videos automatically
# No manual intervention needed

# Command that runs automatically:
python backend/scripts/ingest_youtube.py \
  --source yt-dlp \
  --limit 5 \
  --limit-unprocessed \
  --skip-shorts \
  --newest-first
```

### Manual Sync (If Needed)

```bash
# If you process videos locally and want to sync
python backend/scripts/sync_to_production.py

# Or use pg_dump for full backup
pg_dump $LOCAL_DB > backup.sql
psql $PROD_DB < backup.sql
```

## Monitoring

### Production Health Checks

```python
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "mode": "production",
        "gpu_available": False,
        "ingestion_enabled": False,
        "database_mode": "read-only",
        "total_segments": get_segment_count(),
        "last_updated": get_last_update_time()
    }
```

### Metrics to Track

- **API response time** (should be <100ms)
- **Database connection pool** (should not be exhausted)
- **Memory usage** (embeddings in RAM)
- **Segment count** (grows with each sync)

## Cost Optimization

### Local Machine (GPU)

- **One-time cost:** RTX 5080 (~$1000)
- **Electricity:** ~$5/month for 24h processing
- **Total:** ~$1000 upfront, minimal ongoing

### Production (CPU)

- **Railway/Render:** ~$20/month
- **Database:** ~$10/month (Supabase/Neon)
- **Total:** ~$30/month

**Savings vs GPU in production:** ~$500/month

## Security

### Production Database

```sql
-- Create read-only user for production
CREATE USER prod_api WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE dr_chaffee TO prod_api;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO prod_api;

-- Prevent writes
REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM prod_api;
```

### API Keys

```bash
# Production .env
DATABASE_URL=postgresql://prod_api:pass@host:5432/db  # Read-only user
OPENAI_API_KEY=sk-...  # For API features only
ENABLE_INGESTION=false  # Hard disable
```

## Troubleshooting

### "No GPU detected" Warning

**Expected in production!** This is normal and safe.

```
⚠️  No GPU detected - will use CPU (slower)
```

Just ignore this warning in production logs.

### Slow Embedding Search

If semantic search is slow:

```python
# Pre-load embeddings into memory
embeddings_cache = load_all_embeddings()

# Use FAISS for faster similarity search
import faiss
index = faiss.IndexFlatIP(1536)  # Inner product for cosine similarity
index.add(embeddings_cache)
```

### Database Connection Issues

```bash
# Check connection
psql $DATABASE_URL -c "SELECT COUNT(*) FROM segments"

# Check read-only mode
psql $DATABASE_URL -c "SHOW transaction_read_only"
```

## Summary

### Local Machine (GPU)
- ✅ Run ingestion with RTX 5080
- ✅ Process 1200h audio in ~24h
- ✅ Generate all embeddings
- ✅ Write to local database

### Production (CPU)
- ✅ Deploy API only
- ✅ No GPU required
- ✅ Read-only database
- ✅ Serve requests fast
- ❌ No ingestion/transcription

### Data Flow
```
Local (GPU) → Process videos → Local DB → Replicate → Production DB → API
```

**Best of both worlds: GPU power locally, cheap CPU in production!** 🎯
