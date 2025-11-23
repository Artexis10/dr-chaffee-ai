# Dr. Chaffee AI - Backend Technical Summary (Part 2/3)

## 9. API ENDPOINTS

### Core Search Endpoints

**POST /api/search** - Semantic search with embeddings
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "autoimmune disease treatment",
    "top_k": 50,
    "min_similarity": 0.5,
    "rerank": true
  }'
```

**GET /api/search** - Simple search
```bash
curl "http://localhost:8000/api/search?query=metabolic+health&top_k=50"
```

### Admin Endpoints

**GET /api/admin/status** - System status
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  http://localhost:8000/api/admin/status
```

**GET /api/admin/jobs** - List processing jobs
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  http://localhost:8000/api/admin/jobs
```

**GET /api/admin/jobs/{job_id}** - Get job status
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  http://localhost:8000/api/admin/jobs/abc123
```

### Upload Endpoints

**POST /api/upload** - Upload SRT/VTT files
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@transcripts.zip" \
  -F "source_type=manual" \
  -F "description=Manual transcripts"
```

**GET /api/upload/status/{job_id}** - Upload status
```bash
curl http://localhost:8000/api/upload/status/abc123
```

### YouTube Ingestion Endpoints

**POST /api/ingest/youtube** - Start YouTube ingestion
```bash
curl -X POST http://localhost:8000/api/ingest/youtube \
  -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 100,
    "use_proxy": false
  }'
```

**GET /api/ingest/youtube/status/{job_id}** - Ingestion status
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  http://localhost:8000/api/ingest/youtube/status/abc123
```

### Tuning Endpoints (AI Configuration)

**GET /api/tuning/instructions** - List all instruction sets
```bash
curl http://localhost:8000/api/tuning/instructions
```

**GET /api/tuning/instructions/active** - Get active set
```bash
curl http://localhost:8000/api/tuning/instructions/active
```

**POST /api/tuning/instructions** - Create new instruction set
```bash
curl -X POST http://localhost:8000/api/tuning/instructions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Autoimmune Focus",
    "description": "Emphasize autoimmune conditions",
    "instructions": "Always mention autoimmune mechanisms..."
  }'
```

**PUT /api/tuning/instructions/{id}** - Update instruction set
```bash
curl -X PUT http://localhost:8000/api/tuning/instructions/abc123 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "instructions": "Updated instructions..."
  }'
```

**POST /api/tuning/instructions/{id}/activate** - Activate instruction set
```bash
curl -X POST http://localhost:8000/api/tuning/instructions/abc123/activate
```

**POST /api/tuning/instructions/preview** - Preview merged prompt
```bash
curl -X POST http://localhost:8000/api/tuning/instructions/preview \
  -H "Content-Type: application/json" \
  -d '{
    "instructions": "Your custom instructions here"
  }'
```

**GET /api/tuning/instructions/{id}/history** - Version history
```bash
curl http://localhost:8000/api/tuning/instructions/abc123/history
```

**POST /api/tuning/instructions/{id}/rollback/{version}** - Rollback to version
```bash
curl -X POST http://localhost:8000/api/tuning/instructions/abc123/rollback/2
```

### Answer Generation (Optional)

**POST /api/answer** - Generate LLM answer from search results
```bash
curl -X POST http://localhost:8000/api/answer \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is autoimmune disease?",
    "top_k": 40,
    "model": "gpt-3.5-turbo"
  }'
```

**GET /api/answer/cache/{query_hash}** - Get cached answer
```bash
curl http://localhost:8000/api/answer/cache/abc123hash
```

### Documentation

**GET /docs** - Swagger UI (interactive API documentation)
```
http://localhost:8000/docs
```

**GET /redoc** - ReDoc (alternative API documentation)
```
http://localhost:8000/redoc
```

---

## 10. DEPLOYMENT CHECKLIST FOR HETZNER VPS + COOLIFY

### Pre-Deployment

- [ ] Python 3.12.7 installed on VPS
- [ ] PostgreSQL 13+ with pgvector extension installed
- [ ] Redis installed (optional, for Celery)
- [ ] FFmpeg installed (`apt-get install ffmpeg`)
- [ ] NVIDIA CUDA 13.0 runtime installed (if using GPU)
- [ ] Git installed for repository cloning

### Environment Setup

- [ ] Create `.env` file with all required variables
- [ ] Set secure `DATABASE_URL` pointing to Hetzner PostgreSQL
- [ ] Set `ADMIN_API_KEY` to secure random string (32+ chars)
- [ ] Set `TUNING_PASSWORD` to secure random string (32+ chars)
- [ ] Set `OPENAI_API_KEY` if using LLM features
- [ ] Set `YOUTUBE_API_KEY` if ingesting YouTube
- [ ] Verify all paths are absolute (no relative paths)

### Database Setup

```bash
# Connect to PostgreSQL
psql -h db.hetzner.com -U postgres -d askdrchaffee

# Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

# Exit psql
\q
```

### Application Installation

```bash
# Clone repository
git clone https://github.com/your-repo/dr-chaffee-ai.git
cd dr-chaffee-ai/backend

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Run migrations
python -m alembic upgrade head

# Verify installation
python -c "import fastapi; import psycopg2; print('✅ Dependencies OK')"
```

### Application Startup

```bash
# Development (single worker)
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Production (4 workers)
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

# With Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.main:app --bind 0.0.0.0:8000
```

### Coolify Configuration

**Service Type:** Docker  
**Port:** 8000  
**Health Check:** `/health`  
**Restart Policy:** always  
**Memory Limit:** 2GB (adjust based on Hetzner plan)  
**CPU Limit:** 2 cores (adjust based on Hetzner plan)

**Docker Compose (for reference):**
```yaml
services:
  backend:
    image: your-registry/dr-chaffee-backend:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - ADMIN_API_KEY=...
      - TUNING_PASSWORD=...
      - WHISPER_DEVICE=cpu
      - EMBEDDING_DEVICE=cpu
    volumes:
      - /tmp/whisper_cache:/tmp/whisper_cache
      - /tmp/audio_downloads:/tmp/audio_downloads
    healthcheck:
      test: ["CMD", "python", "-c", "import yt_dlp; print('OK')"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: always
```

### Post-Deployment Verification

```bash
# Check API is running
curl http://localhost:8000/docs

# Check database connection
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" http://localhost:8000/api/admin/status

# Check embeddings are working
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 5}'

# Check logs
docker-compose logs -f backend
```

---

## 11. PRODUCTION OPTIMIZATION

### CPU-Only Production

For Hetzner VPS without GPU:

```bash
# Use CPU-only PyTorch
pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu

# Set in .env
WHISPER_DEVICE=cpu
EMBEDDING_DEVICE=cpu
SKIP_WARMUP=true
```

**Performance Impact:**
- Whisper ASR: ~5-10x slower
- Embeddings: ~2-3x slower
- Estimated ingestion time for 1300 videos: 2-3 weeks (vs 2 days with GPU)

### Memory Optimization

**For Low-Memory Environments (< 4GB):**

```bash
# Skip embedding model warmup
SKIP_WARMUP=true

# Reduce batch sizes
BATCH_SIZE=256
EMBEDDING_BATCH_SIZE=64

# Use smaller Whisper model
WHISPER_MODEL=base  # Instead of distil-large-v3
```

### Database Optimization

**Connection Pooling:**
```python
# psycopg2 uses connection pooling automatically
# For high concurrency, consider pgBouncer on VPS
```

**Vector Index Optimization:**
```sql
-- Create IVFFlat index for faster similarity search
CREATE INDEX ON segments USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Or use HNSW for even better performance
CREATE INDEX ON segments USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

### Caching Strategy

**Redis Caching (optional):**
```python
# Install redis-py
pip install redis

# Use for:
# - Answer cache (ANSWER_CACHE_TTL_HOURS)
# - Session management
# - Rate limiting
```

### Reverse Proxy Configuration (Nginx)

```nginx
upstream backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

---

## 12. TROUBLESHOOTING

### Common Issues

**Issue: "No module named 'api'"**
```bash
# Solution: Ensure PYTHONPATH is set
export PYTHONPATH=/app
cd /app/backend
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**Issue: "psycopg2 connection refused"**
```bash
# Check DATABASE_URL
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Verify PostgreSQL is running
systemctl status postgresql
```

**Issue: "Alembic migration timeout"**
```bash
# Solution: Migrations use batch processing
# Check migration 010_add_cascade_delete.py for example
python -m alembic upgrade head

# If still timing out, increase timeout in alembic.ini
# Or run migrations manually with longer timeout
```

**Issue: "Out of memory during embedding"**
```bash
# Solution: Reduce batch size
EMBEDDING_BATCH_SIZE=128
BATCH_SIZE=256

# Or skip warmup
SKIP_WARMUP=true

# Check available memory
free -h
```

**Issue: "YouTube download fails"**
```bash
# Solution: Install yt-dlp PO Token provider
pip install bgutil-ytdlp-pot-provider

# Or use cookies.txt in project root
# See: YOUTUBE_BOT_DETECTION_GUIDE.md

# Test yt-dlp
yt-dlp --version
```

**Issue: "Port 8000 already in use"**
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn api.main:app --host 0.0.0.0 --port 8001
```

**Issue: "pgvector extension not found"**
```bash
# Install pgvector on PostgreSQL
psql -U postgres -d askdrchaffee -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Verify installation
psql -U postgres -d askdrchaffee -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

---

## 13. MONITORING & LOGGING

### Log Files

**Docker Logs:**
```bash
docker-compose logs -f backend
```

**Application Logs:**
- Stdout: Captured by Docker/systemd
- File: Configure in logging config if needed

### Monitoring Endpoints

**System Status:**
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  http://localhost:8000/api/admin/status
```

**Job Status:**
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  http://localhost:8000/api/admin/jobs
```

**GPU Monitoring (if applicable):**
```bash
# Inside container
nvidia-smi

# Watch GPU usage
watch -n 1 nvidia-smi
```

### Performance Monitoring

**CPU Usage:**
```bash
top -p $(pgrep -f "uvicorn api.main")
```

**Memory Usage:**
```bash
ps aux | grep uvicorn
```

**Database Connections:**
```sql
SELECT count(*) FROM pg_stat_activity;
```

---

## 14. SECURITY CONSIDERATIONS

### Secrets Management

**DO NOT:**
- Commit `.env` files to git
- Hardcode API keys in code
- Use default passwords
- Log sensitive information

**DO:**
- Use environment variables for all secrets
- Rotate API keys regularly
- Use secure random strings for passwords
- Store secrets in Coolify's secret management
- Use `.gitignore` to exclude `.env` files

### CORS Security

**Current:** Allows all origins (development)

**Production:**
```python
allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
```

### Database Security

**Use SSL/TLS:**
```
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

**Restrict Access:**
```bash
# Only allow connections from application server
# Configure in PostgreSQL pg_hba.conf
host    askdrchaffee    postgres    192.168.1.100/32    md5
```

### API Key Rotation

```bash
# Generate new secure key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update in Coolify secrets
# Restart application
```

### Rate Limiting

**Implement rate limiting for production:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/search")
@limiter.limit("100/minute")
async def search(request: Request, query: str):
    # ...
```

---

## 15. DEPLOYMENT COMMANDS SUMMARY

```bash
# Clone repository
git clone https://github.com/your-repo/dr-chaffee-ai.git
cd dr-chaffee-ai/backend

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your values

# Run migrations
python -m alembic upgrade head

# Start application (production)
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.main:app --bind 0.0.0.0:8000

# Or with systemd (create /etc/systemd/system/dr-chaffee.service)
[Unit]
Description=Dr. Chaffee AI Backend
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/app/backend
Environment="PATH=/app/backend/venv/bin"
ExecStart=/app/backend/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start service
sudo systemctl enable dr-chaffee
sudo systemctl start dr-chaffee
sudo systemctl status dr-chaffee
```

---

**Continue to BACKEND_DEPLOYMENT_PART3.md for embedding models configuration and final notes.**
