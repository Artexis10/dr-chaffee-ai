# Complete Railway Deployment Guide

## Prerequisites
- Railway account (free at railway.app)
- Railway CLI installed
- Git push access to your repo

---

## Step 1: Install Railway CLI

Run from **any directory** (not just backend):

```bash
npm install -g @railway/cli
```

Verify installation:
```bash
railway --version
```

---

## Step 2: Login to Railway

```bash
railway login
```

This opens a browser to authenticate. Once done, you're logged in globally.

---

## Step 3: Initialize Railway Project

**From your project root** (`c:\Users\hugoa\Desktop\dr-chaffee-ai`):

```bash
railway init
```

This will prompt you:
1. **Project name**: `dr-chaffee-ai` (or whatever you want)
2. **Environment**: `production` (or `staging` for testing)

Creates a `.railway` folder (don't commit this).

---

## Step 4: Link to GitHub (Optional but Recommended)

Instead of manual deploys, auto-deploy from `railway-migration` branch:

1. Go to railway.app dashboard
2. Click your project
3. Settings → GitHub Integration
4. Connect your GitHub repo
5. Select `railway-migration` branch

**Then Railway auto-deploys on every push!**

---

## Step 5: Set Environment Variables

### Option A: Via Railway CLI (Recommended)

```bash
# Set each variable
railway variables set DATABASE_URL="postgresql://user:pass@host.render.com:5432/dbname"
railway variables set OPENAI_API_KEY="sk-..."
railway variables set OPENAI_MODEL="gpt-4o-mini"
railway variables set EMBEDDING_PROVIDER="sentence-transformers"
railway variables set EMBEDDING_MODEL="BAAI/bge-small-en-v1.5"
railway variables set EMBEDDING_DIMENSIONS="384"
railway variables set TUNING_PASSWORD="your_secure_password"
railway variables set PORT="8000"
railway variables set PYTHONUNBUFFERED="1"
railway variables set SKIP_WARMUP="false"
railway variables set ANSWER_ENABLED="true"
railway variables set ANSWER_TOPK="100"
railway variables set ANSWER_TTL_HOURS="336"
railway variables set ANSWER_STYLE_DEFAULT="concise"
railway variables set MAX_CLIPS_CONCISE="30"
railway variables set MAX_CLIPS_DETAILED="100"
railway variables set RATE_LIMIT_CONCISE="10"
railway variables set RATE_LIMIT_DETAILED="3"
```

### Option B: Via Railway Dashboard

1. Go to railway.app
2. Select your project
3. Click "Variables"
4. Paste all from `.env.railway.example`
5. Save

---

## Step 6: Deploy Backend

### Option A: Manual Deploy (One-time)

**From project root** (`c:\Users\hugoa\Desktop\dr-chaffee-ai`):

```bash
railway up
```

Railway will:
1. Detect Python + Node.js monorepo
2. Read `railway.json` config
3. Build backend (`cd backend && pip install -r requirements.txt`)
4. Start backend (`cd backend && uvicorn api.main:app --host 0.0.0.0 --port 8000`)
5. Give you a URL like `https://dr-chaffee-ai-prod.railway.app`

**Wait 2-3 minutes for deployment.**

### Option B: Auto-Deploy via GitHub (Recommended)

If you linked GitHub:
1. Push to `railway-migration` branch
2. Railway automatically deploys
3. Check status in dashboard

---

## Step 7: Verify Deployment

Once Railway shows "Running":

### Test Health Check
```bash
curl https://your-app.railway.app/health
```

Expected response:
```json
{"status": "healthy"}
```

### Test Embedding Endpoint
```bash
curl -X POST https://your-app.railway.app/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "test query"}'
```

Expected response:
```json
{
  "embedding": [0.123, -0.456, ...],
  "dimensions": 384,
  "text": "test query"
}
```

### Test Search Endpoint
```bash
curl "https://your-app.railway.app/api/search?q=ketosis&top_k=5"
```

Should return search results.

---

## Step 8: Update Frontend on Vercel

### Get Your Railway URL

From Railway dashboard:
- Go to your project
- Click "Deployments"
- Copy the URL (e.g., `https://dr-chaffee-ai-prod.railway.app`)

### Update Vercel Environment Variables

1. Go to vercel.com
2. Select your frontend project
3. Settings → Environment Variables
4. Update or create:
   ```
   BACKEND_API_URL=https://your-railway-url.railway.app
   ```
5. Save and redeploy

### Redeploy Frontend

```bash
# Option 1: Via Vercel dashboard
# Click "Deployments" → "Redeploy" on latest

# Option 2: Via CLI
vercel --prod
```

---

## Step 9: Test End-to-End

### Test Answer Endpoint

```bash
curl -X POST https://your-vercel-url.vercel.app/api/answer \
  -H "Content-Type: application/json" \
  -d '{"q": "What is ketosis?", "style": "concise"}'
```

Should return:
```json
{
  "answer_md": "...",
  "citations": [...],
  "confidence": 0.85,
  "cached": false
}
```

### Test in Browser

1. Go to your frontend URL
2. Ask a question
3. Should get answer (no timeout!)
4. Check browser console for logs

---

## Troubleshooting

### Deployment Fails

Check logs:
```bash
railway logs
```

Common issues:
- **Missing env vars**: Add all vars from Step 5
- **Database connection**: Verify `DATABASE_URL` is correct
- **Port conflict**: Railway auto-assigns PORT, should be fine

### Embedding Timeout

If embedding still times out:
1. Check Railway logs: `railway logs`
2. Verify model is loading: Look for "Loading embedding model"
3. Increase timeout in frontend (currently 10s)

### Database Connection Error

```bash
# Test database connection
railway variables get DATABASE_URL
# Copy the URL and test with psql or pgAdmin
```

### Model Not Loading

Check if model cache is working:
```bash
railway logs | grep -i "embedding\|model"
```

Should see:
```
Loading embedding model: BAAI/bge-small-en-v1.5
Model loaded successfully
```

---

## Monitoring

### View Logs

```bash
# Real-time logs
railway logs -f

# Last 100 lines
railway logs -n 100
```

### Check Status

```bash
# See deployment status
railway status
```

### Monitor Performance

Railway dashboard shows:
- CPU usage
- Memory usage
- Network I/O
- Deployment history

---

## Rollback Plan

If something breaks:

### Quick Rollback (Keep Railway)
1. Go to Railway dashboard
2. Click "Deployments"
3. Select previous working deployment
4. Click "Redeploy"

### Full Rollback (Back to Render)
1. Update Vercel: `BACKEND_API_URL=https://drchaffee-backend.onrender.com`
2. Redeploy frontend
3. Delete Railway project (optional)

---

## File Structure Reference

Your project structure (Railway understands this):

```
dr-chaffee-ai/
├── backend/
│   ├── api/
│   │   ├── main.py          ← Railway runs this
│   │   ├── tuning.py
│   │   └── ...
│   ├── requirements.txt      ← Railway installs these
│   ├── migrations/
│   └── ...
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
├── railway.json             ← Railway config (tells it what to do)
├── .env.railway.example     ← Reference for env vars
└── RAILWAY_MIGRATION.md     ← This guide
```

Railway reads `railway.json` and knows:
1. Build: `cd backend && pip install -r requirements.txt`
2. Start: `cd backend && uvicorn api.main:app --host 0.0.0.0 --port 8000`
3. Health check: `/health`

---

## Quick Reference Commands

```bash
# Login
railway login

# Initialize project
railway init

# Set a variable
railway variables set KEY=value

# Deploy
railway up

# View logs
railway logs -f

# Check status
railway status

# View all variables
railway variables

# Open dashboard
railway open
```

---

## Expected Timeline

- **Step 1-2**: 2 minutes (install + login)
- **Step 3**: 1 minute (init)
- **Step 4**: 5 minutes (GitHub link, optional)
- **Step 5**: 5 minutes (set env vars)
- **Step 6**: 3-5 minutes (deploy)
- **Step 7**: 2 minutes (verify)
- **Step 8**: 3 minutes (update Vercel)
- **Step 9**: 2 minutes (test)

**Total: ~20-30 minutes**

---

## Success Checklist

- [ ] Railway CLI installed and logged in
- [ ] Railway project created
- [ ] All environment variables set
- [ ] Backend deployed successfully
- [ ] Health check passes
- [ ] Embedding endpoint works
- [ ] Search endpoint works
- [ ] Frontend updated with new backend URL
- [ ] Frontend redeployed on Vercel
- [ ] Answer endpoint works end-to-end
- [ ] No timeout errors in logs

---

## Next Steps After Deployment

1. **Monitor for 24-48 hours**
   - Check logs regularly
   - Test various queries
   - Verify no cold starts

2. **If stable, merge to main**
   ```bash
   git checkout main
   git merge railway-migration
   git push
   ```

3. **Delete Render backend** (optional)
   - Keep Render PostgreSQL
   - Delete Render backend service
   - Save $7/month

4. **Update documentation**
   - Update README with Railway info
   - Document the migration

---

## Support

If you get stuck:
1. Check `railway logs -f` for errors
2. Verify all env vars are set
3. Test endpoints with curl
4. Check Railway dashboard for resource usage
5. Refer to Railway docs: railway.app/docs

Good luck! 🚀
