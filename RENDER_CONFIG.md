# Render Configuration Guide

## 🎯 Services Overview

You should have **2 services** on Render:
1. **Backend Web Service** - API endpoints (lightweight, no ML)
2. **Cron Job** - Daily ingestion (includes Whisper)

---

## 1️⃣ Backend Web Service

**Service Name**: `drchaffee-backend`

### Build Settings
```bash
# Build Command
pip install -r requirements-render.txt

# Start Command
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

### Environment Variables

**Essential (Required)**:
```bash
DATABASE_URL=postgresql://user:password@host:5432/database
HUGGINGFACE_HUB_TOKEN=hf_your_token_here
```

**Optional (Can delete if not using)**:
```bash
# These are NOT needed for the web service
WHISPER_MODEL=❌ DELETE
WHISPER_COMPUTE=❌ DELETE
WHISPER_DEVICE=❌ DELETE
BEAM_SIZE=❌ DELETE
TEMPERATURE=❌ DELETE
IO_WORKERS=❌ DELETE
ASR_WORKERS=❌ DELETE
DB_WORKERS=❌ DELETE
SEGMENT_MIN_CHARS=❌ DELETE
SEGMENT_MAX_CHARS=❌ DELETE
SEGMENT_MAX_GAP_SECONDS=❌ DELETE
SEGMENT_MAX_MERGE_DURATION=❌ DELETE
ENABLE_SPEAKER_ID=❌ DELETE
ASSUME_MONOLOGUE=❌ DELETE
CHAFFEE_MIN_SIM=❌ DELETE
GUEST_MIN_SIM=❌ DELETE
PYANNOTE_CLUSTERING_THRESHOLD=❌ DELETE
EMBEDDING_PROFILE=❌ DELETE
EMBEDDING_DEVICE=❌ DELETE
SKIP_SHORTS=❌ DELETE
NEWEST_FIRST=❌ DELETE
CLEANUP_AUDIO_AFTER_PROCESSING=❌ DELETE
STORE_AUDIO_LOCALLY=❌ DELETE
YOUTUBE_CHANNEL_URL=❌ DELETE
YOUTUBE_API_KEY=❌ DELETE
```

**Keep Only These**:

**Minimal (Required)**:
```bash
DATABASE_URL=postgresql://user:password@host:5432/database
HUGGINGFACE_HUB_TOKEN=hf_your_token_here
```

**Recommended (Embedding optimization)**:
```bash
EMBEDDING_PROFILE=quality
EMBEDDING_DEVICE=cpu
```

**Optional (Admin API)**:
```bash
ADMIN_API_KEY=your_secret_key
YOUTUBE_API_KEY=your_youtube_key  # Only if triggering ingestion via API
APP_PASSWORD=your_password  # Legacy, use ADMIN_API_KEY instead
```

---

## 2️⃣ Cron Job (Daily Ingestion)

**Service Name**: `drchaffee-daily-ingest`

### Build Settings
```bash
# Build Command
pip install -r requirements-cron.txt

# Start Command (runs the ingestion script)
python scripts/scheduled_ingestion.py
```

### Schedule
```
0 2 * * *
```
(Runs daily at 2 AM UTC)

### Environment Variables

**Essential (Required)**:
```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# YouTube
YOUTUBE_CHANNEL_URL=https://www.youtube.com/@anthonychaffeemd

# Whisper (CPU-optimized)
WHISPER_MODEL=base
WHISPER_COMPUTE=int8
WHISPER_DEVICE=cpu
BEAM_SIZE=3

# Concurrency (CPU-optimized)
IO_WORKERS=4
ASR_WORKERS=1
DB_WORKERS=4

# Segmentation
SEGMENT_MIN_CHARS=1100
SEGMENT_MAX_CHARS=1400
SEGMENT_MAX_GAP_SECONDS=5.0
SEGMENT_MAX_MERGE_DURATION=120.0

# Speaker ID
ENABLE_SPEAKER_ID=true
ASSUME_MONOLOGUE=true
CHAFFEE_MIN_SIM=0.62
GUEST_MIN_SIM=0.82
PYANNOTE_CLUSTERING_THRESHOLD=0.3

# Embeddings
EMBEDDING_PROFILE=quality
EMBEDDING_DEVICE=cpu

# Processing
SKIP_SHORTS=true
NEWEST_FIRST=true
CLEANUP_AUDIO_AFTER_PROCESSING=true
STORE_AUDIO_LOCALLY=false

# API Keys
HUGGINGFACE_HUB_TOKEN=hf_your_token_here
```

**Optional (Can add if needed)**:
```bash
# YouTube API (faster video listing)
YOUTUBE_API_KEY=your_youtube_api_key

# OpenAI (if cron job needs to generate answers)
OPENAI_API_KEY=sk-proj-your_key_here
SUMMARIZER_MODEL=gpt-3.5-turbo
```

---

## 🗑️ Variables to DELETE from Backend Web Service

Go to **Render Dashboard** → **drchaffee-backend** → **Environment** and delete these:

### Whisper Settings (Not needed for web service)
- ❌ `WHISPER_MODEL`
- ❌ `WHISPER_COMPUTE`
- ❌ `WHISPER_DEVICE`
- ❌ `BEAM_SIZE`
- ❌ `TEMPERATURE`
- ❌ `MAX_AUDIO_DURATION`
- ❌ `WHISPER_PARALLEL_MODELS`

### Concurrency Settings (Not needed for web service)
- ❌ `IO_WORKERS`
- ❌ `ASR_WORKERS`
- ❌ `DB_WORKERS`
- ❌ `BATCH_SIZE`

### Segmentation Settings (Not needed for web service)
- ❌ `SEGMENT_MIN_CHARS`
- ❌ `SEGMENT_MAX_CHARS`
- ❌ `SEGMENT_MAX_GAP_SECONDS`
- ❌ `SEGMENT_MAX_MERGE_DURATION`
- ❌ `SEGMENT_HARD_CAP_CHARS`
- ❌ `SEGMENT_OVERLAP_CHARS`
- ❌ `ENABLE_SEGMENT_OPTIMIZATION`

### Speaker ID Settings (Not needed for web service)
- ❌ `ENABLE_SPEAKER_ID`
- ❌ `VOICES_DIR`
- ❌ `CHAFFEE_MIN_SIM`
- ❌ `GUEST_MIN_SIM`
- ❌ `ATTR_MARGIN`
- ❌ `ASSUME_MONOLOGUE`
- ❌ `USE_SIMPLE_DIARIZATION`
- ❌ `AUTO_BOOTSTRAP_CHAFFEE`
- ❌ `PYANNOTE_CLUSTERING_THRESHOLD`

### Performance Settings (Not needed for web service)
- ❌ `CHUNK_DURATION_SECONDS`
- ❌ `ENABLE_FAST_PATH`
- ❌ `CHAFFEE_ONLY_STORAGE`
- ❌ `EMBED_CHAFFEE_ONLY`
- ❌ `VOICE_EMBEDDING_CACHE_MAX_AGE_DAYS`

### Embedding Settings (Not needed for web service)
- ❌ `EMBEDDING_PROFILE`
- ❌ `EMBEDDING_PROVIDER`
- ❌ `EMBEDDING_MODEL`
- ❌ `EMBEDDING_DIMENSIONS`
- ❌ `EMBEDDING_DEVICE`
- ❌ `EMBEDDING_BATCH_SIZE`

### Reranker Settings (Not needed for web service)
- ❌ `ENABLE_RERANKER`
- ❌ `RERANK_TOP_K`
- ❌ `RETURN_TOP_K`
- ❌ `RERANK_BATCH_SIZE`
- ❌ `VOICE_ENROLLMENT_BATCH_SIZE`
- ❌ `SKIP_VOICE_EMBEDDINGS`

### yt-dlp Settings (Not needed for web service)
- ❌ `YTDLP_BIN`
- ❌ `YTDLP_OPTS`

### Processing Settings (Not needed for web service)
- ❌ `SKIP_SHORTS`
- ❌ `NEWEST_FIRST`
- ❌ `RERANK_ENABLED`
- ❌ `CLEANUP_AUDIO_AFTER_PROCESSING`
- ❌ `STORE_AUDIO_LOCALLY`
- ❌ `AUDIO_STORAGE_DIR`

### YouTube Settings (Not needed for web service)
- ❌ `YOUTUBE_CHANNEL_URL`
- ❌ `YOUTUBE_API_KEY`

### OpenAI Settings (Not needed for web service - frontend handles this)
- ❌ `OPENAI_API_KEY`
- ❌ `SUMMARIZER_MODEL`

### Postgres Individual Settings (Redundant with DATABASE_URL)
- ❌ `POSTGRES_USER`
- ❌ `POSTGRES_PASSWORD`
- ❌ `POSTGRES_DB`

---

## ✅ Final Backend Web Service Environment Variables

After cleanup, you should have **ONLY**:

**Minimal (2 variables)**:
```bash
DATABASE_URL=postgresql://user:password@host:5432/database
HUGGINGFACE_HUB_TOKEN=hf_your_token_here
```

**Recommended (4 variables)**:
```bash
DATABASE_URL=postgresql://user:password@host:5432/database
HUGGINGFACE_HUB_TOKEN=hf_your_token_here
EMBEDDING_PROFILE=quality
EMBEDDING_DEVICE=cpu
```

**With Admin API (6-7 variables)**:
```bash
DATABASE_URL=postgresql://user:password@host:5432/database
HUGGINGFACE_HUB_TOKEN=hf_your_token_here
EMBEDDING_PROFILE=quality
EMBEDDING_DEVICE=cpu
ADMIN_API_KEY=your_secret_key
YOUTUBE_API_KEY=your_youtube_key  # Optional
APP_PASSWORD=your_password  # Legacy
```

**All other variables are STALE** (only used by ingestion scripts, not the web service).

---

## 📊 Summary

| Service | Build Command | Env Variables | Purpose |
|---------|--------------|---------------|---------|
| **Backend Web Service** | `pip install -r requirements-render.txt` | 2-3 variables | Serve API endpoints |
| **Cron Job** | `pip install -r requirements-cron.txt` | ~25 variables | Daily ingestion with Whisper |

---

## 🚀 Deployment Steps

1. **Update Backend Web Service**:
   - Change build command to `pip install -r requirements-render.txt`
   - Delete all unnecessary env variables (see list above)
   - Keep only `DATABASE_URL`, `HUGGINGFACE_HUB_TOKEN`, `APP_PASSWORD`
   - Trigger manual deploy

2. **Update Cron Job**:
   - Change build command to `pip install -r requirements-cron.txt`
   - Add all required env variables (see list above)
   - Trigger manual deploy

3. **Test**:
   - Backend should deploy in ~2-3 minutes
   - Cron job should deploy in ~3-5 minutes
   - Both should work without errors

---

## 🆘 Troubleshooting

**Backend still timing out?**
- Make sure you're using `requirements-render.txt`
- Verify no ML packages in environment variables

**Cron job still timing out?**
- Make sure you're using `requirements-cron.txt` (with pinned versions)
- Check that `WHISPER_DEVICE=cpu` (not cuda)

**Frontend can't connect to backend?**
- Update `EMBEDDING_SERVICE_URL` in frontend to point to your Render backend URL
