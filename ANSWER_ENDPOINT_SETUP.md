# Answer Endpoint Setup Guide

## Current Issue

The `/answer` endpoint is deployed but **not working** because:

1. ✅ Code is deployed to Render
2. ❌ `OPENAI_API_KEY` environment variable is **NOT SET** in Render

## Quick Fix (5 minutes)

### Step 1: Add OpenAI API Key to Render

1. Go to https://dashboard.render.com
2. Select your backend service: `drchaffee-backend`
3. Click **Environment** tab
4. Add new environment variable:
   ```
   Key: OPENAI_API_KEY
   Value: sk-proj-... (your OpenAI API key)
   ```
5. Click **Save Changes**
6. Render will automatically redeploy (takes ~2 minutes)

### Step 2: (Optional) Set OpenAI Model

Add another environment variable:
```
Key: OPENAI_MODEL
Value: gpt-4-turbo
```

**Model Options**:
- `gpt-4-turbo` - Best quality, ~$0.025/query
- `gpt-4o` - Faster, similar quality, ~$0.015/query
- `gpt-3.5-turbo` - Cheapest, ~$0.002/query (not recommended for medical content)

### Step 3: Test

After Render redeploys, test the endpoint:

```bash
curl -X GET "https://drchaffee-backend.onrender.com/answer?query=carnivore+diet+benefits&top_k=10"
```

Expected response:
```json
{
  "answer": "Based on Dr. Chaffee's content, the carnivore diet offers...",
  "sources": [...],
  "query": "carnivore diet benefits",
  "chunks_used": 10,
  "cost_usd": 0.0234
}
```

---

## What Was Fixed

### Issue 1: Missing `style` Parameter
**Problem**: Frontend was calling `GET /answer?query=...&style=concise`  
**Backend expected**: `GET /answer?query=...&top_k=10`  
**Fix**: Added `style` parameter to GET endpoint (commit `48341dc`)

### Issue 2: Poor Error Messages
**Problem**: Generic 500 errors, hard to debug  
**Fix**: Added specific error logging for:
- Missing OPENAI_API_KEY (503 error)
- OpenAI import failures (503 error)
- General exceptions (500 error with details)

---

## Architecture After Fix

```
Frontend: GET /api/answer?query=...&style=concise
    ↓
Backend: GET /answer (FastAPI)
    ↓
1. Semantic search (Nomic 768-dim) → 10 results
2. Build RAG context
3. Call OpenAI GPT-4 ← REQUIRES OPENAI_API_KEY
    ↓
Response: AI answer + citations
```

---

## Cost Estimates

### With GPT-4 Turbo
- **Per query**: ~$0.025
- **100 queries/month**: $2.50
- **1000 queries/month**: $25.00

### With Caching (Frontend Already Has This)
- **Cache hit rate**: 70-80% after first month
- **Effective cost**: $5-7.50 per 1000 queries

---

## Troubleshooting

### Error: "OpenAI API key not configured" (503)
**Solution**: Add `OPENAI_API_KEY` to Render environment variables

### Error: "OpenAI library not available" (503)
**Solution**: Check `requirements.txt` has `openai>=2.0.0`  
**Status**: ✅ Already included (see build logs: `openai-2.4.0` installed)

### Error: "Answer generation failed" (500)
**Check logs**: 
```bash
# In Render dashboard, go to Logs tab
# Look for: "Answer generation failed: <error message>"
```

Common causes:
- Invalid OpenAI API key
- Rate limit exceeded
- OpenAI API outage

### Frontend Still Shows Error
**Possible causes**:
1. Frontend is cached (hard refresh: Ctrl+Shift+R)
2. Frontend is calling wrong URL
3. CORS issue (check browser console)

**Debug**:
```javascript
// In browser console
fetch('https://drchaffee-backend.onrender.com/answer?query=test&top_k=5')
  .then(r => r.json())
  .then(console.log)
```

---

## Next Steps

1. ✅ Code deployed (commit `48341dc`)
2. ⏳ **Add OPENAI_API_KEY to Render** ← DO THIS NOW
3. ⏳ Wait for redeploy (~2 minutes)
4. ✅ Test endpoint
5. ✅ Frontend should work automatically

---

## Environment Variables Checklist

### Backend (Render) - Required
- [x] `DATABASE_URL` - PostgreSQL connection
- [x] `NOMIC_API_KEY` - For embeddings
- [ ] `OPENAI_API_KEY` - **MISSING - ADD THIS**
- [ ] `OPENAI_MODEL` - Optional (defaults to gpt-4-turbo)

### Backend (Render) - Optional
- [ ] `PORT` - Auto-set by Render
- [ ] `PYTHON_VERSION` - Auto-detected

### Frontend (Vercel) - Required
- [ ] `DATABASE_URL` - For answer caching
- [ ] `BACKEND_API_URL` - Backend URL
- [ ] `OPENAI_API_KEY` - For fallback RAG (optional)

---

## Success Criteria

✅ **Backend deployed**: https://drchaffee-backend.onrender.com  
✅ **Search working**: 90 results for "carnivore diet benefits"  
⏳ **Answer working**: Waiting for OPENAI_API_KEY  
⏳ **Frontend working**: Depends on backend answer endpoint  

**ETA to full functionality**: 5 minutes (add API key + redeploy)
