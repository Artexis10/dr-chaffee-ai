# Production Deployment Guide

## Overview

**Ask Dr. Chaffee** production deployment on **Hetzner + Coolify** with CPU-only backend.

This guide covers deploying the backend API (FastAPI) on Hetzner VPS using Coolify for container orchestration.

## Architecture

```
User Browser
    ↓
Frontend (Vercel/Netlify/Cloudflare Pages)
    ↓ HTTPS API calls
Coolify Reverse Proxy (Traefik)
    ↓ Port 80/443 → 8000
Backend API Container (Docker)
    ↓
PostgreSQL Database (Hetzner Managed or Self-hosted)
```

## Prerequisites

- **Hetzner VPS**: CPX21 or better (2 vCPU, 4GB RAM minimum)
- **Coolify**: Installed and configured on Hetzner VPS
- **PostgreSQL**: Managed database or self-hosted
- **Domain**: DNS configured to point to Hetzner VPS IP
- **SSL**: Coolify handles Let's Encrypt automatically

---

## Backend Deployment (Hetzner + Coolify)

### 1. Hetzner VPS Setup

**Recommended Specs:**
- **CPX21**: 2 vCPU, 4GB RAM, 80GB SSD (~€8/month)
- **CPX31**: 4 vCPU, 8GB RAM, 160GB SSD (~€16/month) - for higher traffic

**Initial Setup:**
```bash
# SSH into your Hetzner VPS
ssh root@your-vps-ip

# Update system
apt update && apt upgrade -y

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Coolify (one-command install)
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

### 2. Coolify Configuration

1. **Access Coolify UI**: `http://your-vps-ip:8000`
2. **Create new project**: "Ask Dr. Chaffee Backend"
3. **Add GitHub repository**:
   - Repository: `your-username/dr-chaffee-ai`
   - Branch: `main`
   - Build Pack: `Dockerfile`
   - Dockerfile path: `./Dockerfile`

### 3. Environment Variables (Coolify)

Set these in Coolify UI under "Environment Variables":

```bash
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/askdrchaffee

# OpenAI (for answer generation)
OPENAI_API_KEY=sk-proj-your_production_key_here

# Embedding Configuration (CPU-only)
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSIONS=384
EMBEDDING_DEVICE=cpu

# API Configuration
PORT=8000
SKIP_WARMUP=false

# CORS (update with your frontend domain)
CORS_ORIGINS=https://askdrchaffee.com,https://www.askdrchaffee.com
```

### 4. Domain & SSL Setup

**In Coolify:**
1. Go to your application settings
2. Add custom domain: `api.askdrchaffee.com`
3. Coolify automatically provisions Let's Encrypt SSL
4. Traefik reverse proxy maps 80/443 → 8000

**DNS Configuration (at your domain registrar):**
```
A Record: api.askdrchaffee.com → your-vps-ip
```

### 5. Deploy

**Automatic Deployment:**
- Push to `main` branch → Coolify auto-deploys
- Webhook configured automatically by Coolify

**Manual Deployment:**
- Click "Deploy" in Coolify UI
- Monitor build logs in real-time

### 6. Health Check

Coolify uses the Dockerfile `HEALTHCHECK` directive:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1
```

**Verify deployment:**
```bash
curl https://api.askdrchaffee.com/health
# Should return: {"status":"ok","checks":{"database":"ok","embeddings":"ok"}}
```

---

## Frontend Deployment

### Platform: Vercel (Recommended)

**Why Vercel:**
- Zero-config Next.js deployment
- Automatic HTTPS & CDN
- Preview deployments for PRs
- Free tier sufficient for most use cases

### Deployment Steps:

1. **Connect GitHub Repository:**
   - Go to [vercel.com](https://vercel.com)
   - Import `dr-chaffee-ai` repository
   - Select `frontend` directory as root

2. **Configure Build Settings:**
   - Framework Preset: Next.js
   - Build Command: `npm run build`
   - Output Directory: `.next`
   - Install Command: `npm install`

3. **Environment Variables:**
```bash
# Backend API URL (CRITICAL)
NEXT_PUBLIC_BACKEND_URL=https://api.askdrchaffee.com

# Database (for Next.js API routes)
DATABASE_URL=postgresql://user:password@host:5432/askdrchaffee

# OpenAI (for answer generation)
OPENAI_API_KEY=sk-proj-your_key_here
SUMMARIZER_MODEL=gpt-4o-mini

# Backend API (for server-side calls)
BACKEND_API_URL=https://api.askdrchaffee.com

# Answer Settings
ANSWER_TOPK=100
ANSWER_STYLE_DEFAULT=concise

# Optional: Password protection
APP_PASSWORD=your_secure_password
```

4. **Custom Domain:**
   - Add domain in Vercel: `askdrchaffee.com`
   - Configure DNS:
     ```
     CNAME: askdrchaffee.com → cname.vercel-dns.com
     CNAME: www.askdrchaffee.com → cname.vercel-dns.com
     ```

5. **Deploy:**
   - Push to `main` → Auto-deploy
   - Vercel provides preview URLs for PRs

---

## Database Setup

### Option 1: Hetzner Managed PostgreSQL (Recommended)

**Advantages:**
- Automatic backups
- High availability
- Managed updates
- Monitoring included

**Setup:**
1. Create managed PostgreSQL instance on Hetzner Cloud
2. Note connection string
3. Add to Coolify environment variables

### Option 2: Self-hosted PostgreSQL (via Coolify)

**Setup:**
1. In Coolify, create new PostgreSQL database
2. Coolify handles container orchestration
3. Automatic backups via Coolify

**Connection String:**
```
postgresql://postgres:password@postgres:5432/askdrchaffee
```

### Database Migrations

**Run migrations after deployment:**
```bash
# SSH into Coolify container
coolify ssh <container-id>

# Run Alembic migrations
cd /app
alembic upgrade head
```

---

## Environment Variables Reference

### Backend (Required)

| Variable | Description | Example |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `OPENAI_API_KEY` | OpenAI API key for answers | `sk-proj-...` |
| `EMBEDDING_PROVIDER` | Embedding service | `sentence-transformers` |
| `EMBEDDING_MODEL` | Model name | `BAAI/bge-small-en-v1.5` |
| `EMBEDDING_DIMENSIONS` | Vector dimensions | `384` |
| `EMBEDDING_DEVICE` | Device | `cpu` |
| `PORT` | API port | `8000` |
| `CORS_ORIGINS` | Allowed origins | `https://askdrchaffee.com` |

### Backend (Optional)

| Variable | Description | Default |
|----------|-------------|----------|
| `SKIP_WARMUP` | Skip model warmup on startup | `false` |
| `ANSWER_TOPK` | Context chunks for answers | `100` |
| `ANSWER_TTL_HOURS` | Cache TTL | `336` (14 days) |
| `SUMMARIZER_MODEL` | OpenAI model | `gpt-4o-mini` |

### Frontend (Required)

| Variable | Description | Example |
|----------|-------------|----------|
| `NEXT_PUBLIC_BACKEND_URL` | Backend API URL | `https://api.askdrchaffee.com` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://...` |
| `OPENAI_API_KEY` | OpenAI key | `sk-proj-...` |
| `BACKEND_API_URL` | Backend URL (server-side) | `https://api.askdrchaffee.com` |

---

## Monitoring & Logging

### Coolify Built-in Monitoring

- **Container Logs**: Real-time logs in Coolify UI
- **Resource Usage**: CPU, Memory, Network graphs
- **Health Checks**: Automatic monitoring via healthcheck endpoint
- **Alerts**: Email/Slack notifications on failures

### Application Logs

```bash
# View backend logs
coolify logs <app-name>

# Follow logs in real-time
coolify logs <app-name> -f
```

### Health Check Endpoint

**Endpoint**: `GET /health`

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

## Troubleshooting

### Backend Issues

#### 502 Bad Gateway

**Cause**: Backend container not running or healthcheck failing

**Fix:**
```bash
# Check container status
coolify ps

# View logs
coolify logs <app-name>

# Restart container
coolify restart <app-name>
```

#### Database Connection Errors

**Cause**: Incorrect `DATABASE_URL` or database not accessible

**Fix:**
1. Verify `DATABASE_URL` in Coolify environment variables
2. Test connection:
   ```bash
   psql $DATABASE_URL -c "SELECT 1;"
   ```
3. Check database container status (if self-hosted)

#### Embedding Model Errors

**Cause**: Model download failed or insufficient memory

**Fix:**
1. Check logs for model download errors
2. Verify `EMBEDDING_MODEL` is correct
3. Increase VPS RAM if OOM errors
4. Set `SKIP_WARMUP=true` to defer model loading

### Frontend Issues

#### CORS Errors

**Cause**: Frontend domain not in `CORS_ORIGINS`

**Fix:**
```bash
# Update CORS_ORIGINS in Coolify
CORS_ORIGINS=https://askdrchaffee.com,https://www.askdrchaffee.com

# Restart backend
coolify restart <app-name>
```

#### API Connection Errors

**Cause**: Incorrect `NEXT_PUBLIC_BACKEND_URL`

**Fix:**
1. Verify environment variable in Vercel
2. Ensure backend is accessible: `curl https://api.askdrchaffee.com/health`
3. Redeploy frontend after fixing

---

## Security Checklist

### Backend
- ✅ HTTPS only (enforced by Coolify/Traefik)
- ✅ Environment secrets (never commit `.env`)
- ✅ Database connection pooling
- ✅ CORS whitelist configured
- ✅ Healthcheck endpoint (no sensitive data)
- ✅ No GPU/CUDA dependencies (attack surface reduction)

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

### Development (Free Tier)
- **Frontend**: Vercel Free (100GB bandwidth)
- **Backend**: Hetzner CPX11 (~€4/month)
- **Database**: Self-hosted on same VPS
- **Total**: ~€4/month

### Production (Recommended)
- **Frontend**: Vercel Pro (~$20/month)
- **Backend**: Hetzner CPX21 (~€8/month)
- **Database**: Hetzner Managed PostgreSQL (~€10/month)
- **Coolify**: Free (self-hosted)
- **Total**: ~€18/month (~$20/month)

### High Traffic
- **Frontend**: Vercel Pro (~$20/month)
- **Backend**: Hetzner CPX31 (~€16/month)
- **Database**: Hetzner Managed PostgreSQL (~€20/month)
- **Total**: ~€36/month (~$40/month)

---

## Deployment Checklist

### Initial Setup
- [ ] Provision Hetzner VPS (CPX21 or better)
- [ ] Install Docker & Coolify
- [ ] Set up PostgreSQL (managed or self-hosted)
- [ ] Configure DNS A record for backend
- [ ] Create Coolify project
- [ ] Add GitHub repository to Coolify
- [ ] Configure environment variables
- [ ] Deploy backend via Coolify
- [ ] Verify health check: `curl https://api.your-domain.com/health`
- [ ] Deploy frontend to Vercel
- [ ] Configure frontend environment variables
- [ ] Add custom domain to Vercel
- [ ] Test end-to-end: frontend → backend → database

### Every Deploy
- [ ] Run tests locally: `pytest tests/`
- [ ] Build Docker image locally (optional): `docker build -t test .`
- [ ] Push to `main` branch
- [ ] Monitor Coolify build logs
- [ ] Verify health check after deployment
- [ ] Test API endpoints
- [ ] Monitor error logs for 10 minutes

---

## Rollback Strategy

### Backend (Coolify)

**Option 1: Rollback via Coolify UI**
1. Go to deployment history
2. Select previous successful deployment
3. Click "Redeploy"

**Option 2: Git Revert**
```bash
# Revert last commit
git revert HEAD
git push origin main

# Coolify auto-deploys reverted version
```

### Frontend (Vercel)

**Option 1: Vercel UI**
1. Go to deployment history
2. Click "..." on previous deployment
3. Select "Promote to Production"

**Option 2: Vercel CLI**
```bash
vercel rollback
```

---

## Alternative Platforms

### Backend Alternatives
- **Render**: Similar to Railway, $7/month starter
- **Fly.io**: Edge deployment, pay-as-you-go
- **DigitalOcean App Platform**: $5/month basic

### Frontend Alternatives
- **Netlify**: Similar to Vercel, free tier available
- **Cloudflare Pages**: Free, fast CDN
- **AWS Amplify**: AWS ecosystem integration

### Database Alternatives
- **Supabase**: Managed PostgreSQL, free tier
- **Neon**: Serverless PostgreSQL, free tier
- **Railway**: Managed PostgreSQL, $5/month

---

## Additional Resources

- **Coolify Documentation**: https://coolify.io/docs
- **Hetzner Cloud**: https://www.hetzner.com/cloud
- **Vercel Documentation**: https://vercel.com/docs
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment
- **Docker Best Practices**: https://docs.docker.com/develop/dev-best-practices
- **AWS Amplify**: AWS ecosystem

### Backend Alternatives
- **Render**: Similar to Railway
- **Fly.io**: Global edge deployment
- **AWS Lambda**: Serverless
- **Google Cloud Run**: Containerized

### Database Alternatives
- **Neon**: Serverless PostgreSQL
- **PlanetScale**: MySQL-compatible
- **AWS RDS**: Traditional managed DB
