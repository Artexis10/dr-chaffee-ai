# 🚀 Production Ready Checklist - Deploy Tomorrow

## ❌ CRITICAL BLOCKERS (Fix These First!)

### 1. **Embedding Model on CPU** (HIGHEST PRIORITY)
**Status**: ❌ **BLOCKING PRODUCTION**

**Problem**: Embeddings running at 2 texts/sec instead of 30 texts/sec
- **Impact**: Pipeline 15x slower than target (10h/hour vs 50h/hour)
- **Cause**: Missing `EMBEDDING_DEVICE=cuda` in environment

**Fix** (5 minutes):
```bash
# Create .env file in backend directory
cd backend
cp .env.production .env

# Edit .env and set:
EMBEDDING_DEVICE=cuda
EMBEDDING_MODEL=Alibaba-NLP/gte-Qwen2-1.5B-instruct
EMBEDDING_BATCH_SIZE=128
```

**Verify Fix**:
```bash
# Run test script
python scripts/test_embedding_speed.py

# Should see:
# ✅ GPU acceleration active (30+ texts/sec)
```

---

### 2. **Database Transaction Errors**
**Status**: ⚠️ **NON-BLOCKING** (gracefully handled but needs fix)

**Problem**: `current transaction is aborted, commands ignored until end of transaction block`
- **Impact**: Voice embedding cache misses (slower but works)
- **Cause**: Previous query error not properly rolled back

**Fix**: ✅ **ALREADY APPLIED** in `segments_database.py`
- Added `conn.reset()` after rollback
- Should resolve in next run

---

## ✅ PRODUCTION REQUIREMENTS

### Infrastructure

- [ ] **PostgreSQL Database**
  - Version: 15+
  - Extension: pgvector installed
  - Connection string in `.env`
  - Connection pooling configured

- [ ] **GPU Server**
  - NVIDIA GPU with CUDA support
  - Drivers: Latest NVIDIA drivers installed
  - VRAM: 16GB+ recommended (RTX 5080 ideal)
  - CUDA: Version 11.8+ or 12.x

- [ ] **Storage**
  - Disk space: 100GB+ for models and cache
  - Fast SSD recommended for database

### Environment Configuration

- [ ] **Backend `.env` file created**
  ```bash
  cd backend
  cp .env.production .env
  # Edit with your values
  ```

- [ ] **Critical variables set**:
  ```bash
  # Database
  DATABASE_URL=postgresql://user:pass@host:5432/dbname
  
  # GPU (CRITICAL!)
  EMBEDDING_DEVICE=cuda
  WHISPER_DEVICE=cuda
  
  # OpenAI
  OPENAI_API_KEY=sk-...
  
  # Performance
  EMBEDDING_BATCH_SIZE=128
  VOICE_ENROLLMENT_BATCH_SIZE=4
  MAX_IO_WORKERS=12
  MAX_ASR_WORKERS=2
  MAX_DB_WORKERS=12
  ```

- [ ] **Frontend `.env` file**
  ```bash
  cd frontend
  # Create .env.local with:
  DATABASE_URL=postgresql://user:pass@host:5432/dbname
  OPENAI_API_KEY=sk-...
  RAG_SERVICE_URL=http://localhost:8000
  ```

### Dependencies

- [ ] **Python packages installed**
  ```bash
  cd backend
  pip install -r requirements.txt
  ```

- [ ] **Node packages installed**
  ```bash
  cd frontend
  npm install
  ```

- [ ] **FFmpeg installed**
  ```bash
  # Windows: Download from ffmpeg.org
  # Linux: sudo apt install ffmpeg
  # macOS: brew install ffmpeg
  ```

### Database Schema

- [ ] **Tables created**
  ```bash
  cd backend
  python scripts/setup_database.py
  ```

- [ ] **pgvector extension enabled**
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```

### Models Downloaded

- [ ] **Whisper model cached**
  - First run will download distil-large-v3 (~1.5GB)
  - Cached in `~/.cache/huggingface/`

- [ ] **Embedding model cached**
  - First run will download gte-Qwen2-1.5B (~3GB)
  - Cached in `~/.cache/huggingface/`

- [ ] **SpeechBrain model cached**
  - First run will download ECAPA-TDNN (~100MB)
  - Cached in `backend/pretrained_models/`

### Testing

- [ ] **GPU verification**
  ```bash
  cd backend
  python scripts/test_voice_gpu.py
  # Should see: ✅ SUCCESS: Model is on GPU!
  ```

- [ ] **Embedding speed test**
  ```bash
  python scripts/test_embedding_speed.py
  # Should see: 30+ texts/sec
  ```

- [ ] **Single video test**
  ```bash
  python scripts/ingest_youtube_enhanced_asr.py --video-ids "dQw4w9WgXcQ" --force
  # Should complete without errors
  ```

- [ ] **Database connectivity**
  ```bash
  python -c "import psycopg2; conn = psycopg2.connect('$DATABASE_URL'); print('✅ Connected')"
  ```

---

## 🚀 DEPLOYMENT STEPS (Tomorrow)

### Step 1: Environment Setup (30 minutes)

1. **Create `.env` files**:
   ```bash
   cd backend
   cp .env.production .env
   # Edit with your credentials
   
   cd ../frontend
   # Create .env.local with your settings
   ```

2. **Verify GPU**:
   ```bash
   nvidia-smi  # Should show your GPU
   python -c "import torch; print(torch.cuda.is_available())"  # Should print True
   ```

3. **Install dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   
   cd ../frontend
   npm install
   ```

### Step 2: Database Setup (15 minutes)

1. **Create database**:
   ```sql
   CREATE DATABASE drchaffee_prod;
   \c drchaffee_prod
   CREATE EXTENSION vector;
   ```

2. **Run schema setup**:
   ```bash
   cd backend
   python scripts/setup_database.py
   ```

3. **Verify tables**:
   ```sql
   \dt  # Should show: sources, segments, etc.
   ```

### Step 3: Initial Ingestion (2-4 hours for 50 videos)

1. **Create video list**:
   ```bash
   # Create videos.txt with one video ID per line
   echo "dQw4w9WgXcQ" > videos.txt
   echo "jNQXAC9IVRw" >> videos.txt
   # ... add more
   ```

2. **Start ingestion**:
   ```bash
   cd backend
   python scripts/ingest_youtube_enhanced_asr.py \
     --video-ids-file videos.txt \
     --batch-size 50
   ```

3. **Monitor progress**:
   - Watch for GPU utilization: `nvidia-smi -l 1`
   - Check logs for errors
   - Expected: 10-15h audio per hour throughput

### Step 4: Frontend Deployment (30 minutes)

1. **Build frontend**:
   ```bash
   cd frontend
   npm run build
   ```

2. **Start production server**:
   ```bash
   npm start
   # Or deploy to Vercel/Netlify
   ```

3. **Verify**:
   - Open http://localhost:3000
   - Test search functionality
   - Test answer generation

### Step 5: Production Monitoring

1. **Set up monitoring**:
   - GPU utilization: `nvidia-smi -l 10`
   - Database connections: Check pgAdmin or `pg_stat_activity`
   - Disk space: `df -h`

2. **Error tracking**:
   - Check logs in `backend/logs/`
   - Monitor for CUDA OOM errors
   - Watch for database connection issues

---

## 📊 EXPECTED PERFORMANCE

### Current Performance (After Fixes)
- **Throughput**: 40-50h audio per hour
- **Real-Time Factor**: 0.15-0.22 (5-7x faster than real-time)
- **GPU Utilization**: 90%+ during ASR
- **VRAM Usage**: 6-10GB peak

### Ingestion Estimates
| Videos | Total Audio | Time to Process |
|--------|-------------|-----------------|
| 50     | 30-40h      | 1-2 hours       |
| 200    | 120-160h    | 4-6 hours       |
| 1000   | 600-800h    | 20-30 hours     |
| 1200   | 700-900h    | 24-36 hours     |

### Bottlenecks to Watch
1. **Embedding generation**: Should be 30+ texts/sec
2. **Voice enrollment**: Should be 10-15 emb/sec
3. **Whisper ASR**: Should be 5-7x real-time
4. **Database writes**: Should be <100ms per batch

---

## ⚠️ COMMON ISSUES & FIXES

### Issue: Embeddings Still Slow After Setting EMBEDDING_DEVICE=cuda

**Symptoms**:
```
⚠️  Slow embedding generation (2.0 texts/sec)
```

**Fix**:
1. Verify `.env` file is in correct location:
   ```bash
   ls -la backend/.env  # Should exist
   ```

2. Check environment is loaded:
   ```bash
   cd backend
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('EMBEDDING_DEVICE'))"
   # Should print: cuda
   ```

3. Restart pipeline completely (kill all Python processes)

4. If still slow, check GPU availability:
   ```bash
   python -c "import torch; print(torch.cuda.is_available())"
   ```

### Issue: CUDA Out of Memory

**Symptoms**:
```
CUDA error: out of memory
```

**Fix**:
1. Reduce batch sizes in `.env`:
   ```bash
   EMBEDDING_BATCH_SIZE=64  # Down from 128
   VOICE_ENROLLMENT_BATCH_SIZE=2  # Down from 4
   ```

2. Process in smaller batches:
   ```bash
   # Instead of 200 videos at once, do 50 at a time
   python scripts/ingest_youtube_enhanced_asr.py --video-ids-file batch1.txt
   python scripts/ingest_youtube_enhanced_asr.py --video-ids-file batch2.txt
   ```

3. Restart pipeline between batches to clear GPU memory

### Issue: Database Connection Errors

**Symptoms**:
```
could not connect to server
connection refused
```

**Fix**:
1. Verify PostgreSQL is running:
   ```bash
   # Linux
   sudo systemctl status postgresql
   
   # Windows
   # Check Services app for PostgreSQL
   ```

2. Check connection string in `.env`:
   ```bash
   # Should be format:
   DATABASE_URL=postgresql://user:password@host:5432/database
   ```

3. Test connection:
   ```bash
   psql "$DATABASE_URL"
   ```

### Issue: Models Not Downloading

**Symptoms**:
```
Connection timeout
Failed to download model
```

**Fix**:
1. Check internet connection
2. Set HuggingFace cache directory:
   ```bash
   export HF_HOME=/path/to/large/disk
   ```
3. Pre-download models:
   ```bash
   python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('Alibaba-NLP/gte-Qwen2-1.5B-instruct')"
   ```

---

## 🔒 SECURITY CHECKLIST

- [ ] **API Keys secured**
  - `.env` files in `.gitignore`
  - Never commit API keys to git
  - Use environment variables in production

- [ ] **Database secured**
  - Strong password
  - Firewall rules configured
  - SSL/TLS enabled for remote connections

- [ ] **Frontend secured**
  - CORS configured properly
  - Rate limiting enabled
  - Input validation on all endpoints

---

## 📈 SCALING BEYOND 1200 HOURS

### Horizontal Scaling
- Run multiple ingestion workers on different machines
- Each worker processes different video batches
- All write to same PostgreSQL database

### Vertical Scaling
- Upgrade to GPU with more VRAM (e.g., A100 40GB)
- Increase batch sizes:
  ```bash
  EMBEDDING_BATCH_SIZE=256
  VOICE_ENROLLMENT_BATCH_SIZE=16
  ```

### Database Optimization
- Enable connection pooling (pgBouncer)
- Add read replicas for search queries
- Partition segments table by video_id

---

## 🎯 SUCCESS CRITERIA

Your deployment is **production-ready** when:

✅ **Performance**:
- Embedding generation: 30+ texts/sec
- Voice enrollment: 10+ emb/sec
- Whisper ASR: 5-7x real-time
- Overall throughput: 40-50h audio per hour

✅ **Reliability**:
- No CUDA OOM errors in 50+ video batch
- No database connection errors
- Graceful error recovery (fallback fast-path works)

✅ **Functionality**:
- Search returns relevant results
- Answer generation works
- Speaker attribution accurate (90%+)
- Frontend loads and responds quickly

✅ **Monitoring**:
- GPU utilization visible
- Error logs accessible
- Performance metrics tracked

---

## 🆘 EMERGENCY CONTACTS

If you encounter issues during deployment:

1. **Check logs**:
   ```bash
   tail -f backend/logs/ingestion.log
   ```

2. **GPU issues**:
   ```bash
   nvidia-smi
   # Check temperature, memory, utilization
   ```

3. **Database issues**:
   ```sql
   SELECT * FROM pg_stat_activity;
   -- Check for long-running queries
   ```

4. **Quick recovery**:
   ```bash
   # Kill all processes
   pkill -f python
   
   # Clear GPU memory
   nvidia-smi --gpu-reset
   
   # Restart with smaller batch
   python scripts/ingest_youtube_enhanced_asr.py --video-ids "test_video" --force
   ```

---

## 📝 POST-DEPLOYMENT

After successful deployment:

1. **Document your setup**:
   - Server specs
   - Database configuration
   - Performance metrics achieved

2. **Set up backups**:
   ```bash
   # Database backup
   pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
   ```

3. **Monitor for 24 hours**:
   - Watch for memory leaks
   - Check error rates
   - Verify search quality

4. **Optimize based on metrics**:
   - Adjust batch sizes if needed
   - Tune concurrency settings
   - Add more workers if bottlenecked

---

## ✅ FINAL PRE-LAUNCH CHECKLIST

**Before going live tomorrow**:

- [ ] `.env` file created with `EMBEDDING_DEVICE=cuda`
- [ ] GPU test passes (30+ texts/sec)
- [ ] Database connected and schema created
- [ ] Single video ingestion test successful
- [ ] Frontend builds without errors
- [ ] Search functionality tested
- [ ] Answer generation tested
- [ ] Monitoring tools ready
- [ ] Backup strategy in place
- [ ] Error recovery procedures documented

**If all checked**: 🚀 **YOU'RE READY TO DEPLOY!**
