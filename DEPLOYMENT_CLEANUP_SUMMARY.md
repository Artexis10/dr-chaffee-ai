# Backend Deployment Cleanup Summary

## Overview

Completed comprehensive cleanup and optimization of the Dr. Chaffee AI backend for **CPU-only production deployment** on **Hetzner + Coolify**.

---

## Changes Made

### 1. ✅ Created Production Requirements (`backend/requirements-production.txt`)

**Purpose**: Minimal CPU-only dependencies for API-only deployment

**Excluded from production:**
- ❌ GPU dependencies (CUDA, cuDNN)
- ❌ ASR/transcription (faster-whisper, ctranslate2)
- ❌ Diarization (pyannote.audio, speechbrain)
- ❌ Audio processing (soundfile, webvtt-py)
- ❌ YouTube ingestion (yt-dlp, youtube-transcript-api, google-api-python-client)
- ❌ Background jobs (celery, redis)
- ❌ Development tools (pytest, black, ruff)

**Included (API essentials only):**
- ✅ FastAPI + Uvicorn
- ✅ PostgreSQL (psycopg2-binary, alembic, sqlalchemy)
- ✅ PyTorch CPU-only (via `--index-url https://download.pytorch.org/whl/cpu`)
- ✅ Embeddings (sentence-transformers, transformers)
- ✅ OpenAI (for answer generation)
- ✅ Core utilities (numpy, python-dotenv, psutil, isodate)

**Result**: Significantly smaller Docker image (<2GB target)

---

### 2. ✅ Optimized Dockerfile

**Changes:**
- Uses `requirements-production.txt` instead of `requirements-simple.txt`
- Removed unnecessary stages (YouTube, audio transcription, utilities)
- Consolidated dependencies into 3 stages (core, web API, ML/embeddings)
- **CRITICAL**: PyTorch installed from CPU-only wheels (`--index-url https://download.pytorch.org/whl/cpu`)
- Added `EXPOSE 8000` directive
- Updated healthcheck to query `/health` endpoint instead of checking yt-dlp

**Before:**
```dockerfile
HEALTHCHECK CMD python -c "import yt_dlp; print('OK')" || exit 1
```

**After:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1
```

---

### 3. ✅ Enhanced `/health` Endpoint

**Location**: `backend/api/main.py`

**Features:**
- Checks database connection (`SELECT 1`)
- Checks embedding service readiness (test embedding generation)
- Returns `200 OK` if healthy, `503 Service Unavailable` if degraded
- Detailed status for each check

**Response (Healthy):**
```json
{
  "status": "ok",
  "service": "Ask Dr. Chaffee API",
  "timestamp": "2025-01-15T10:30:00Z",
  "checks": {
    "database": "ok",
    "embeddings": "ok"
  }
}
```

**Response (Degraded):**
```json
{
  "status": "degraded",
  "service": "Ask Dr. Chaffee API",
  "timestamp": "2025-01-15T10:30:00Z",
  "checks": {
    "database": "degraded",
    "embeddings": "ok"
  }
}
```

---

### 4. ✅ Frontend Environment Configuration

**Created:**
- `frontend/.env.example` - Updated for local development
- `frontend/.env.production.example` - New file for production

**Key Addition:**
```bash
# CRITICAL: Backend API URL for client-side calls
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000  # Local
NEXT_PUBLIC_BACKEND_URL=https://api.askdrchaffee.com  # Production
```

**Note**: Frontend currently uses Next.js API routes as proxy. To use direct backend calls, update fetch URLs to use `process.env.NEXT_PUBLIC_BACKEND_URL`.

---

### 5. ✅ Comprehensive Deployment Documentation

**File**: `DEPLOYMENT.md` (completely rewritten)

**Contents:**
- Hetzner VPS setup instructions
- Coolify installation and configuration
- Environment variables reference (backend + frontend)
- Domain & SSL setup (Coolify + Let's Encrypt)
- Database setup options (managed vs self-hosted)
- Health check verification
- Monitoring & logging
- Troubleshooting guide (502, CORS, database errors)
- Security checklist
- Cost estimates (€4-36/month)
- Deployment checklist
- Rollback strategy

**Key Sections:**
1. Backend Deployment (Hetzner + Coolify)
2. Frontend Deployment (Vercel)
3. Database Setup (PostgreSQL)
4. Environment Variables Reference
5. Monitoring & Logging
6. Troubleshooting
7. Security Checklist

---

### 6. ✅ Updated GitHub Workflows

**File**: `.github/workflows/deploy-backend.yml`

**Changes:**
- Removed Railway deployment steps
- Kept test and linting jobs
- Added notification step explaining Coolify auto-deploys
- Workflow now only validates code quality

**Before:**
```yaml
deploy:
  name: Deploy to Railway
  steps:
    - name: Deploy to Railway
      run: railway up --service backend
```

**After:**
```yaml
notify:
  name: Notify Deployment
  steps:
    - name: Deployment notification
      run: |
        echo "✅ Tests passed! Coolify will auto-deploy backend."
        echo "Monitor deployment: https://coolify.your-domain.com"
```

---

## Environment Variables (Production)

### Backend (Coolify)

**Required:**
```bash
DATABASE_URL=postgresql://user:password@postgres:5432/askdrchaffee
OPENAI_API_KEY=sk-proj-your_production_key_here
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSIONS=384
EMBEDDING_DEVICE=cpu
PORT=8000
CORS_ORIGINS=https://askdrchaffee.com,https://www.askdrchaffee.com
```

**Optional:**
```bash
SKIP_WARMUP=false
ANSWER_TOPK=100
ANSWER_TTL_HOURS=336
SUMMARIZER_MODEL=gpt-4o-mini
```

### Frontend (Vercel)

**Required:**
```bash
NEXT_PUBLIC_BACKEND_URL=https://api.askdrchaffee.com
DATABASE_URL=postgresql://user:password@host:5432/askdrchaffee
OPENAI_API_KEY=sk-proj-your_key_here
BACKEND_API_URL=https://api.askdrchaffee.com
SUMMARIZER_MODEL=gpt-4o-mini
ANSWER_TOPK=100
```

---

## Deployment Workflow

### Initial Setup

1. **Provision Hetzner VPS** (CPX21: 2 vCPU, 4GB RAM, ~€8/month)
2. **Install Docker & Coolify**:
   ```bash
   curl -fsSL https://get.docker.com | sh
   curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
   ```
3. **Configure Coolify**:
   - Access UI: `http://your-vps-ip:8000`
   - Add GitHub repository
   - Set environment variables
   - Add custom domain: `api.askdrchaffee.com`
4. **Deploy**: Push to `main` → Coolify auto-deploys
5. **Verify**: `curl https://api.askdrchaffee.com/health`

### Continuous Deployment

1. Push to `main` branch
2. GitHub Actions runs tests
3. Coolify webhook triggers deployment
4. Monitor build logs in Coolify UI
5. Verify health check

---

## Port Mapping

**Coolify Reverse Proxy (Traefik):**
```
Internet (80/443) → Traefik → Backend Container (8000)
```

**Docker Container:**
- Exposes port `8000`
- Coolify sets `PORT=8000` environment variable
- Uvicorn binds to `0.0.0.0:8000`

**No manual port configuration needed** - Coolify handles everything.

---

## Verification Steps

### 1. Health Check
```bash
curl https://api.askdrchaffee.com/health
```

**Expected:**
```json
{"status":"ok","checks":{"database":"ok","embeddings":"ok"}}
```

### 2. Root Endpoint
```bash
curl https://api.askdrchaffee.com/
```

**Expected:**
```json
{"status":"ok","service":"Ask Dr. Chaffee API"}
```

### 3. Database Test
```bash
curl https://api.askdrchaffee.com/api/test-db
```

**Expected:**
```json
{"status":"ok","segment_count":514000}
```

---

## Troubleshooting

### 502 Bad Gateway

**Cause**: Container not running or healthcheck failing

**Fix:**
```bash
# Check Coolify logs
coolify logs <app-name>

# Restart container
coolify restart <app-name>
```

### Database Connection Errors

**Cause**: Incorrect `DATABASE_URL`

**Fix:**
1. Verify environment variable in Coolify
2. Test connection: `psql $DATABASE_URL -c "SELECT 1;"`

### CORS Errors

**Cause**: Frontend domain not in `CORS_ORIGINS`

**Fix:**
```bash
# Update in Coolify
CORS_ORIGINS=https://askdrchaffee.com,https://www.askdrchaffee.com

# Restart
coolify restart <app-name>
```

---

## Security Checklist

### Backend
- ✅ HTTPS only (enforced by Coolify/Traefik)
- ✅ Environment secrets (never commit `.env`)
- ✅ Database connection pooling
- ✅ CORS whitelist configured
- ✅ Healthcheck endpoint (no sensitive data)
- ✅ No GPU/CUDA dependencies (reduced attack surface)
- ✅ CPU-only PyTorch (no CUDA libraries)

### Frontend
- ✅ HTTPS only (enforced by Vercel)
- ✅ No secrets in client code
- ✅ CSP headers configured
- ✅ API calls via environment variables

### Database
- ✅ Private network (not exposed to internet)
- ✅ Strong passwords
- ✅ Automatic backups
- ✅ SSL/TLS connections

---

## Cost Estimates

### Development
- **Frontend**: Vercel Free
- **Backend**: Hetzner CPX11 (~€4/month)
- **Database**: Self-hosted
- **Total**: ~€4/month

### Production (Recommended)
- **Frontend**: Vercel Pro (~$20/month)
- **Backend**: Hetzner CPX21 (~€8/month)
- **Database**: Hetzner Managed PostgreSQL (~€10/month)
- **Coolify**: Free (self-hosted)
- **Total**: ~€18/month (~$20/month)

---

## Files Modified

1. `Dockerfile` - Optimized for CPU-only production
2. `backend/requirements-production.txt` - New file (minimal dependencies)
3. `backend/api/main.py` - Enhanced `/health` endpoint
4. `frontend/.env.example` - Updated with `NEXT_PUBLIC_BACKEND_URL`
5. `frontend/.env.production.example` - New file
6. `DEPLOYMENT.md` - Completely rewritten (Hetzner + Coolify)
7. `.github/workflows/deploy-backend.yml` - Removed Railway, added Coolify notes

---

## Next Steps

### Before Deploying

1. **Review environment variables** in `DEPLOYMENT.md`
2. **Update CORS_ORIGINS** with your actual domain
3. **Set OpenAI API key** in Coolify
4. **Configure database connection** (managed or self-hosted)

### After Deploying

1. **Run database migrations**:
   ```bash
   coolify ssh <container-id>
   cd /app
   alembic upgrade head
   ```

2. **Verify health check**:
   ```bash
   curl https://api.your-domain.com/health
   ```

3. **Test API endpoints**:
   ```bash
   curl https://api.your-domain.com/api/test-db
   ```

4. **Monitor logs** for 10 minutes:
   ```bash
   coolify logs <app-name> -f
   ```

---

## Summary

✅ **Backend optimized** for CPU-only production deployment  
✅ **Docker image size reduced** (removed GPU/ASR dependencies)  
✅ **Health check enhanced** (database + embeddings)  
✅ **Frontend environment configured** (local + production)  
✅ **Deployment documentation complete** (Hetzner + Coolify)  
✅ **GitHub workflows updated** (removed Railway references)  
✅ **Security hardened** (HTTPS, CORS, no secrets in code)  

**Ready to deploy!** 🚀

---

## Questions?

Refer to `DEPLOYMENT.md` for detailed instructions, troubleshooting, and best practices.
