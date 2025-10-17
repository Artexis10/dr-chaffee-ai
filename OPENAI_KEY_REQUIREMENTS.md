# OpenAI API Key Requirements

## Summary: Where is OPENAI_API_KEY Needed?

### ✅ REQUIRED (Answer Generation Only)

| Service | Needs Key? | Purpose | Impact if Missing |
|---------|-----------|---------|-------------------|
| **Backend API** | ✅ YES | `/answer` endpoint RAG | Answer endpoint returns 503 error |
| **Frontend API** | ⚠️ OPTIONAL | Fallback RAG | Falls back to backend (recommended) |
| **Cron Jobs** | ❌ NO | Daily ingestion | Not used - only Nomic embeddings |

### ❌ NOT REQUIRED

- **Ingestion scripts** - Use Nomic embeddings only
- **Search endpoint** - Uses Nomic embeddings only  
- **Database operations** - No AI needed
- **Embedding generation** - Uses Nomic API (free)

---

## Detailed Breakdown

### 1. Backend API (`backend/api/main.py`)

**Endpoint**: `POST /answer`

```python
# File: backend/api/main.py
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    raise HTTPException(status_code=503, detail="OpenAI API key not configured")

from openai import OpenAI
client = OpenAI(api_key=openai_api_key)
response = client.chat.completions.create(...)
```

**Usage**:
- Generates AI-powered answers from search results
- Called by frontend when user asks a question
- Cost: ~$0.025 per query (GPT-4 Turbo)

**If missing**:
- `/answer` endpoint returns 503 error
- Frontend shows "Answer generation unavailable"
- Search still works (returns raw results)

---

### 2. Frontend API (`frontend/src/pages/api/answer.ts`)

**Endpoint**: `POST /api/answer`

```typescript
// File: frontend/src/pages/api/answer.ts
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const USE_MOCK_MODE = !OPENAI_API_KEY || OPENAI_API_KEY.includes('your_');

// Tries backend first
const ragResult = await callRAGService(query);

// Falls back to local RAG if backend unavailable
if (!ragResult && !USE_MOCK_MODE) {
    const llmResponse = await callSummarizer(query, clusteredChunks, style);
}
```

**Usage**:
- **Primary**: Calls backend `/answer` endpoint (recommended)
- **Fallback**: Generates answers locally if backend fails
- Only used if backend is down

**If missing**:
- Frontend uses backend exclusively (recommended)
- No fallback if backend fails
- **Recommendation**: Don't set in frontend, rely on backend

---

### 3. Cron Jobs / Ingestion Scripts

**Scripts checked**:
- `ingest_youtube_enhanced_asr.py` ❌ No OpenAI
- `daily_ingest_wrapper.py` ❌ No OpenAI
- `process_srt_files.py` ❌ No OpenAI

**Embedding generation**:
```python
# All ingestion uses Nomic embeddings
generator = EmbeddingGenerator(
    embedding_provider='nomic',
    model_name='nomic-embed-text-v1.5'
)
# Uses NOMIC_API_KEY, not OPENAI_API_KEY
```

**Conclusion**: ✅ Cron jobs do NOT need OpenAI API key

---

## Environment Variable Setup

### Backend (Render) - REQUIRED ✅

```bash
# Render Dashboard → drchaffee-backend → Environment
OPENAI_API_KEY=sk-proj-your-restricted-key-here
OPENAI_MODEL=gpt-4-turbo
```

**Key permissions needed**:
- ✅ `model.request` - Make API calls
- ❌ `api_key.*` - Manage keys (not needed)
- ❌ `organization.*` - Manage org (not needed)

**Usage limits** (set in OpenAI dashboard):
- Monthly budget: $50
- Rate limit: 60 RPM
- Email alerts: 50%, 75%, 90%

### Frontend (Vercel) - OPTIONAL ⚠️

```bash
# Vercel Dashboard → askdrchaffee → Settings → Environment Variables
# OPENAI_API_KEY=sk-proj-...  # NOT RECOMMENDED

# Instead, just point to backend:
BACKEND_API_URL=https://drchaffee-backend.onrender.com
```

**Recommendation**: 
- ❌ Don't set OPENAI_API_KEY in frontend
- ✅ Let frontend call backend exclusively
- Simpler, more secure, centralized cost tracking

### Cron Jobs - NOT NEEDED ❌

```bash
# .env for cron jobs
DATABASE_URL=postgresql://...
NOMIC_API_KEY=nk-...
# OPENAI_API_KEY not needed!
```

---

## Cost Analysis

### With OpenAI Key in Backend Only (Recommended)

**Monthly costs** (1000 queries):
- Search (Nomic): $0 (free tier)
- Answers (OpenAI): ~$25
- **Total**: $25/month

**With caching** (80% hit rate after month 1):
- Cached answers: $0
- New answers: ~$5
- **Total**: $5/month

### With OpenAI Key in Both Frontend + Backend (Not Recommended)

**Issues**:
- Duplicate costs (frontend + backend both call OpenAI)
- Harder to track usage
- Two keys to manage
- Security risk (frontend key exposed)

**Recommendation**: Backend only!

---

## Testing Without OpenAI Key

### What Still Works:

✅ **Search endpoint**:
```bash
curl -X POST https://drchaffee-backend.onrender.com/search \
  -H "Content-Type: application/json" \
  -d '{"query": "carnivore diet", "top_k": 10}'
```

✅ **Embedding generation**:
```bash
curl -X POST https://drchaffee-backend.onrender.com/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "test query"}'
```

✅ **Ingestion scripts**:
```bash
python scripts/ingest_youtube_enhanced_asr.py --video-id abc123
```

❌ **Answer endpoint**:
```bash
curl -X POST https://drchaffee-backend.onrender.com/answer \
  -H "Content-Type: application/json" \
  -d '{"query": "carnivore diet", "top_k": 10}'

# Returns: 503 "OpenAI API key not configured"
```

---

## Migration Path (If Changing Keys)

### Scenario: Need to rotate OpenAI key

**Zero-downtime rotation**:

1. Create new OpenAI key with same permissions
2. Add as `OPENAI_API_KEY_NEW` in Render
3. Update code to try new key first:
   ```python
   openai_api_key = os.getenv('OPENAI_API_KEY_NEW') or os.getenv('OPENAI_API_KEY')
   ```
4. Deploy
5. Remove old `OPENAI_API_KEY`
6. Rename `OPENAI_API_KEY_NEW` → `OPENAI_API_KEY`

---

## Security Best Practices

### ✅ DO:
- Use restricted keys (only `model.request` permission)
- Set monthly budget limits ($50)
- Set rate limits (60 RPM)
- Store in environment variables
- Rotate keys quarterly
- Monitor usage weekly

### ❌ DON'T:
- Hardcode keys in code
- Commit keys to Git
- Share keys in chat/Slack
- Use same key for dev + prod
- Give keys full permissions
- Skip usage limits

---

## Troubleshooting

### Error: "OpenAI API key not configured" (503)

**Check**:
```bash
# In Render dashboard
echo $OPENAI_API_KEY  # Should show sk-proj-...
```

**Fix**: Add key to Render environment variables

### Error: "Invalid API key" (401)

**Causes**:
- Key was revoked
- Key expired
- Wrong key format

**Fix**: Create new key in OpenAI dashboard

### Error: "Rate limit exceeded" (429)

**Causes**:
- Too many requests
- Exceeded RPM limit

**Fix**: 
- Increase rate limit in OpenAI dashboard
- Add exponential backoff in code

### High costs

**Check**:
- OpenAI usage dashboard
- Look for unusual spikes
- Check if caching is working

**Fix**:
- Lower monthly budget limit
- Implement better caching
- Use cheaper model (gpt-4o instead of gpt-4-turbo)

---

## Summary

### Quick Answer: Where do I need OPENAI_API_KEY?

```
✅ Backend (Render): YES - Required for /answer endpoint
⚠️ Frontend (Vercel): NO - Use backend instead
❌ Cron jobs: NO - Only use Nomic embeddings
```

### Recommended Setup:

1. **Add to Render backend only**
2. **Set usage limits in OpenAI dashboard**
3. **Monitor costs weekly**
4. **Let frontend call backend exclusively**

**That's it!** Simple, secure, cost-effective.
