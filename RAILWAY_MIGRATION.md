# Railway Migration Guide

## Why Railway?

### Advantages Over Render
1. **No sleep timeout** - Render Starter sleeps after 15 min inactivity
2. **Better pricing** - Pay per resource used, not per dyno hour
3. **Persistent storage** - Built-in volumes (no ephemeral filesystem)
4. **Better ML support** - Handles model loading/caching better
5. **Faster cold starts** - Better infrastructure for Python/ML apps
6. **Better scaling** - Easier to add CPU/RAM as needed

### Cost Comparison
- **Render Starter**: $7/month (512MB RAM, sleeps after 15 min)
- **Railway Hobby**: $5/month + usage (~$10-15/month for this app)
- **Railway Pro**: $20/month + usage (better for production)

## Migration Plan

### Phase 1: Backend Migration (Priority)
1. Deploy backend to Railway
2. Update environment variables
3. Test embedding endpoint
4. Test answer generation
5. Update frontend to point to Railway backend

### Phase 2: Frontend Migration (Optional)
1. Keep frontend on Vercel (recommended) OR
2. Deploy frontend to Railway as separate service

### Phase 3: Database (Keep on Render)
- PostgreSQL stays on Render (it's working well)
- Just update connection string if needed

## Step-by-Step Instructions

### 1. Install Railway CLI
```bash
npm install -g @railway/cli
railway login
```

### 2. Create Railway Project
```bash
railway init
railway link
```

### 3. Set Environment Variables
```bash
# Database
railway variables set DATABASE_URL="your_render_postgres_url"

# OpenAI
railway variables set OPENAI_API_KEY="your_openai_key"
railway variables set OPENAI_MODEL="gpt-4o-mini"

# Embedding Model
railway variables set EMBEDDING_PROVIDER="sentence-transformers"
railway variables set EMBEDDING_MODEL="BAAI/bge-small-en-v1.5"
railway variables set EMBEDDING_DIMENSIONS="384"

# Tuning Dashboard
railway variables set TUNING_PASSWORD="your_tuning_password"

# Backend Config
railway variables set PORT="8000"
railway variables set SKIP_WARMUP="false"  # Railway has enough RAM
railway variables set PYTHONUNBUFFERED="1"
```

### 4. Create Procfile for Railway
Already exists - Railway will use `railway.json` config

### 5. Deploy Backend
```bash
# Deploy from railway-migration branch
railway up

# Or link to GitHub and auto-deploy
railway link
```

### 6. Update Frontend Environment Variables
Update Vercel environment variables:
```bash
BACKEND_API_URL=https://your-app.railway.app
```

### 7. Test Endpoints
```bash
# Health check
curl https://your-app.railway.app/health

# Embedding test
curl -X POST https://your-app.railway.app/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "test query"}'

# Search test
curl https://your-app.railway.app/api/search?q=ketosis&top_k=5
```

## Railway-Specific Optimizations

### 1. Persistent Model Cache
Railway supports volumes - we can cache the BGE model:

```json
{
  "volumes": [
    {
      "name": "model-cache",
      "mountPath": "/app/.cache"
    }
  ]
}
```

### 2. Better Resource Allocation
Railway allows fine-tuning:
- **CPU**: 1-2 vCPU (enough for BGE-small)
- **RAM**: 1GB (comfortable for model + app)
- **Disk**: 1GB (for model cache)

### 3. Health Checks
Railway has better health check support:
- `/health` endpoint already exists
- 100s timeout (plenty for model loading)
- Auto-restart on failure

## Rollback Plan

If Railway doesn't work:
1. Keep `main` branch on Render (unchanged)
2. Delete Railway deployment
3. Merge learnings back to main

## Testing Checklist

- [ ] Backend deploys successfully
- [ ] Health check passes
- [ ] Embedding endpoint works (no timeout)
- [ ] Search endpoint returns results
- [ ] Answer endpoint generates responses
- [ ] Tuning dashboard accessible
- [ ] No cold start issues
- [ ] Model loads within 30s
- [ ] Frontend can connect to Railway backend
- [ ] Database queries work

## Expected Improvements

1. **Embedding latency**: 10s → 2-3s (no cold start)
2. **Answer generation**: More reliable (no 15-min sleep)
3. **Cost**: Similar or slightly higher, but better value
4. **Uptime**: 99.9% (no sleep timeout)

## Railway Configuration Files

### railway.json (already exists)
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "npm run start:all",
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Nixpacks Configuration
Railway auto-detects Python + Node.js monorepo.
If needed, create `nixpacks.toml`:

```toml
[phases.setup]
nixPkgs = ["python311", "nodejs-18_x", "postgresql"]

[phases.install]
cmds = [
  "cd backend && pip install -r requirements.txt",
  "cd frontend && npm install"
]

[start]
cmd = "npm run start:all"
```

## Next Steps

1. ✅ Create `railway-migration` branch
2. ⏳ Test Railway deployment
3. ⏳ Update frontend to use Railway backend
4. ⏳ Monitor performance for 24-48 hours
5. ⏳ Merge to main if successful

## Notes

- Keep Render deployment running during testing
- Frontend stays on Vercel (it's working great)
- Database stays on Render (PostgreSQL is fine there)
- Only migrate backend to Railway
