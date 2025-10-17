# Debugging Detailed Answer Failures

## Current Status

✅ **Fixed**: Timestamp format (now MM:SS instead of H:MM:SS)
✅ **Fixed**: Vercel-specific config removed
✅ **Fixed**: Enhanced error logging
❌ **Issue**: Detailed answers returning 500 Internal Server Error
❌ **Issue**: answer_cache table mostly empty (only 1 row)

## Debugging Steps

### Step 1: Check Render Logs for Detailed Answer Errors

**What to look for**:
```bash
# In Render dashboard → Logs tab, search for:
"detailed"
"500"
"❌ [Answer API]"
"Error stack"
```

**Expected log pattern for successful detailed answer**:
```
[Answer API] Query: "autoimmune conditions", maxContext: 100, style: detailed
[Answer API] Generating embedding for query...
[Answer API] Embedding generated: 768 dimensions
[Answer API] Using model: nomic-v1.5 (768 dims)
[Answer API] Initial retrieval: 72 chunks
[Answer API] Final chunks for summarization: 50
[callSummarizer] Generating detailed answer with 50 chunks
[callSummarizer] ⚠️ Limiting from 72 to 50 chunks (detailed style limit)
[callSummarizer] Estimated input tokens: ~8500
[callSummarizer] Generated answer: 2456 words (target: 2000-3000, min: 2000)
✅ [callSummarizer] Answer length is perfect: 2456 words in target range 2000-3000
```

**If you see errors, look for**:
```
❌ [Answer API] Unhandled error: <error message>
[Answer API] Error stack: <full stack trace>
```

### Step 2: Test Detailed Answer Directly

```bash
# Test from command line
curl -X POST https://your-app.onrender.com/api/answer \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ketosis explained",
    "style": "detailed",
    "top_k": 100
  }' \
  -v

# Look for:
# - HTTP status code (should be 200, not 500)
# - Response body (should have answer, citations, confidence)
# - Response time (should be 60-90s)
```

### Step 3: Check answer_cache Table

```sql
-- Connect to production database
psql $DATABASE_URL

-- Check if table exists
\d answer_cache

-- Expected schema:
--   id SERIAL PRIMARY KEY
--   query_text TEXT NOT NULL
--   query_embedding_384 vector(384)
--   query_embedding_768 vector(768)
--   query_embedding_1536 vector(1536)
--   embedding_profile TEXT NOT NULL
--   style TEXT NOT NULL
--   answer_md TEXT NOT NULL
--   citations JSONB NOT NULL
--   confidence FLOAT NOT NULL
--   notes TEXT
--   used_chunk_ids TEXT[] NOT NULL
--   source_clips JSONB
--   ttl_hours INTEGER NOT NULL
--   created_at TIMESTAMP DEFAULT NOW()
--   expires_at TIMESTAMP (generated column)

-- Check row count
SELECT COUNT(*) FROM answer_cache;

-- Check recent entries
SELECT 
  id, 
  query_text, 
  embedding_profile, 
  style, 
  LENGTH(answer_md) as answer_length,
  created_at 
FROM answer_cache 
ORDER BY created_at DESC 
LIMIT 10;

-- Check for errors in logs (if you have error logging)
SELECT * FROM answer_cache WHERE notes LIKE '%error%' OR notes LIKE '%failed%';
```

### Step 4: Monitor Cache Save Attempts

**In Render logs, search for**:
```
"[Cache Save]"
```

**Successful save**:
```
[Cache Save] Generating embedding for cache...
[Cache Save] Got embedding: 768 dims (nomic profile)
[Cache Save] Inserting into answer_cache table...
[Cache Save] Using column: query_embedding_768 profile: nomic
✅ [Cache Save] Successfully cached answer (nomic profile), cache ID: 123
```

**Failed save**:
```
❌ [Cache Save] Failed to save to answer_cache
[Cache Save] Error: <error message>
[Cache Save] Error message: <details>
[Cache Save] Error stack: <stack trace>
[Cache Save] Failed data: { query: "...", style: "detailed", ... }
```

## Common Issues & Solutions

### Issue 1: "relation 'answer_cache' does not exist"

**Cause**: Table not created in production database.

**Solution**:
```bash
# Option A: Run Alembic migration
cd backend
alembic upgrade head

# Option B: Create manually
psql $DATABASE_URL -f backend/migrations/create_answer_cache_768.sql

# Option C: Create with SQL
psql $DATABASE_URL << 'EOF'
CREATE TABLE IF NOT EXISTS answer_cache (
  id SERIAL PRIMARY KEY,
  query_text TEXT NOT NULL,
  query_embedding_384 vector(384),
  query_embedding_768 vector(768),
  query_embedding_1536 vector(1536),
  embedding_profile TEXT NOT NULL,
  style TEXT NOT NULL,
  answer_md TEXT NOT NULL,
  citations JSONB NOT NULL,
  confidence FLOAT NOT NULL,
  notes TEXT,
  used_chunk_ids TEXT[] NOT NULL,
  source_clips JSONB,
  ttl_hours INTEGER NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP GENERATED ALWAYS AS (created_at + (ttl_hours || ' hours')::INTERVAL) STORED
);

CREATE INDEX IF NOT EXISTS idx_answer_cache_embedding_768 
  ON answer_cache USING ivfflat (query_embedding_768 vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_answer_cache_expires 
  ON answer_cache(expires_at);
EOF
```

### Issue 2: "column 'query_embedding_768' does not exist"

**Cause**: Table schema mismatch.

**Solution**:
```sql
-- Add missing columns
ALTER TABLE answer_cache ADD COLUMN IF NOT EXISTS query_embedding_384 vector(384);
ALTER TABLE answer_cache ADD COLUMN IF NOT EXISTS query_embedding_768 vector(768);
ALTER TABLE answer_cache ADD COLUMN IF NOT EXISTS query_embedding_1536 vector(1536);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_answer_cache_embedding_384 
  ON answer_cache USING ivfflat (query_embedding_384 vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_answer_cache_embedding_768 
  ON answer_cache USING ivfflat (query_embedding_768 vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_answer_cache_embedding_1536 
  ON answer_cache USING ivfflat (query_embedding_1536 vector_cosine_ops);
```

### Issue 3: "type 'vector' does not exist"

**Cause**: pgvector extension not installed.

**Solution**:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Issue 4: Detailed Answers Timeout

**Symptoms**:
- Request takes >180s
- Returns 500 or timeout error
- Logs show "generating..." but never completes

**Possible causes**:
1. OpenAI API slow/rate limited
2. Too many chunks (>50)
3. Token limit exceeded
4. Network issues

**Solutions**:

**A. Check OpenAI API status**:
```bash
# Test OpenAI API directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Should return 200 OK with model list
```

**B. Reduce chunk limit** (if needed):
```bash
# In Render environment variables, add:
MAX_CLIPS_DETAILED=40  # Reduced from 50
```

**C. Check token usage in logs**:
```
[callSummarizer] Estimated input tokens: ~8500
```
If >10k, reduce MAX_CLIPS_DETAILED.

**D. Increase Render timeout**:
- Go to Render dashboard → Service Settings
- Ensure you're on Standard plan (300s timeout)
- Starter plan only allows 60s (not enough)

### Issue 5: OpenAI API Errors

**401 Unauthorized**:
```
[Answer API] Error: 401 Unauthorized
```
**Solution**: Check OPENAI_API_KEY in Render environment variables.

**429 Rate Limit**:
```
[Answer API] Error: 429 Too Many Requests
```
**Solution**: 
- Wait a few minutes
- Upgrade OpenAI plan
- Add rate limiting on frontend

**500 Internal Server Error from OpenAI**:
```
[Answer API] Error: 500 Internal Server Error
```
**Solution**: OpenAI is having issues, retry later.

### Issue 6: Database Connection Errors

**Symptoms**:
```
[Cache Save] Error: Connection terminated unexpectedly
[Answer API] Error: database connection failed
```

**Solutions**:

**A. Check DATABASE_URL**:
```bash
# In Render dashboard, verify DATABASE_URL is set
# Format: postgresql://user:password@host:5432/database?sslmode=require
```

**B. Test connection**:
```bash
psql $DATABASE_URL -c "SELECT 1"
# Should return: 1
```

**C. Check database is running**:
- If using Render PostgreSQL, check database dashboard
- Ensure database is not paused/sleeping

**D. Check connection pool**:
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- If >100, you may be hitting connection limit
-- Solution: Reduce pool size or upgrade database plan
```

## Monitoring Commands

### Real-time Log Monitoring

**In Render dashboard**:
1. Go to your service
2. Click "Logs" tab
3. Enable "Auto-scroll"
4. Filter by:
   - `detailed` - see detailed answer attempts
   - `❌` - see all errors
   - `[Cache Save]` - see cache operations
   - `[Citation` - see citation issues

### Database Monitoring

```sql
-- Cache hit rate (run periodically)
WITH stats AS (
  SELECT 
    COUNT(*) as total_cached,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') as last_hour,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as last_day
  FROM answer_cache
)
SELECT * FROM stats;

-- Most cached queries
SELECT 
  query_text, 
  style, 
  COUNT(*) as cache_count,
  MAX(created_at) as last_cached
FROM answer_cache 
GROUP BY query_text, style 
ORDER BY cache_count DESC 
LIMIT 10;

-- Cache size
SELECT 
  pg_size_pretty(pg_total_relation_size('answer_cache')) as total_size,
  COUNT(*) as row_count
FROM answer_cache;
```

### Performance Metrics

```bash
# In Render logs, extract metrics:

# Average response time (detailed)
grep "detailed" logs.txt | grep "Answer API response" | awk '{print $NF}' | \
  awk '{sum+=$1; count++} END {print "Avg:", sum/count, "s"}'

# Success rate
total=$(grep "Answer API attempt" logs.txt | wc -l)
errors=$(grep "500\|error" logs.txt | wc -l)
echo "Success rate: $(( (total - errors) * 100 / total ))%"

# Cache save success rate
saves=$(grep "\[Cache Save\] Inserting" logs.txt | wc -l)
failures=$(grep "❌ \[Cache Save\]" logs.txt | wc -l)
echo "Cache save success: $(( (saves - failures) * 100 / saves ))%"
```

## Expected Behavior

### Successful Detailed Answer Flow

1. **Request received**:
```
[Answer API] Query: "autoimmune conditions", maxContext: 100, style: detailed
```

2. **Embedding generated**:
```
[Answer API] Embedding generated: 768 dimensions
[Answer API] Using model: nomic-v1.5 (768 dims)
```

3. **Chunks retrieved**:
```
[Answer API] Initial retrieval: 72 chunks
[Answer API] Similarity range: 0.856 - 0.623
[Answer API] Final chunks for summarization: 50
```

4. **LLM called**:
```
[callSummarizer] Generating detailed answer with 50 chunks
[callSummarizer] Estimated input tokens: ~8500
```

5. **Answer generated**:
```
[callSummarizer] Generated answer: 2456 words (target: 2000-3000, min: 2000)
✅ [callSummarizer] Answer length is perfect: 2456 words
[callSummarizer] Token usage: { prompt: 8234, completion: 4567, total: 12801 }
```

6. **Citations validated**:
```
[Citation Validation] 11 citations validated
[Citation Fix] Fuzzy matched 2 citations
```

7. **Cached**:
```
[Cache Save] Generating embedding for cache...
[Cache Save] Got embedding: 768 dims (nomic profile)
✅ [Cache Save] Successfully cached answer (nomic profile), cache ID: 123
```

8. **Response sent**:
```
Answer API response: 200 OK (87.3s)
```

### Performance Targets

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| **Detailed response time** | 60-90s | 90-120s | >120s |
| **Concise response time** | 12-18s | 18-30s | >30s |
| **Success rate** | >95% | 90-95% | <90% |
| **Cache save rate** | >90% | 80-90% | <80% |
| **Word count (detailed)** | 2000-3000 | 1500-2000 | <1500 |
| **Word count (concise)** | 600-800 | 500-600 | <500 |
| **Confidence score** | 0.8-0.95 | 0.7-0.8 | <0.7 |

## Next Steps

1. **Check Render logs** for detailed answer errors
2. **Verify answer_cache table** exists and has correct schema
3. **Test detailed answer** with curl command
4. **Monitor cache saves** - should see successful saves in logs
5. **If still failing**, share:
   - Full error message from logs
   - answer_cache table schema (`\d answer_cache`)
   - Environment variables (DATABASE_URL, OPENAI_API_KEY set?)
   - Render plan (Starter or Standard?)

## Quick Fixes

### If detailed answers are failing:

```bash
# 1. Reduce chunk limit
# In Render env vars:
MAX_CLIPS_DETAILED=40

# 2. Reduce word target
# (requires code change)
# targetWords: '2000-3000' → '1500-2000'

# 3. Check OpenAI key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### If cache is not saving:

```sql
-- 1. Check table exists
SELECT EXISTS (
  SELECT FROM information_schema.tables 
  WHERE table_name = 'answer_cache'
);

-- 2. Check pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 3. Create table if missing
-- (see Issue 1 solution above)
```

The fixes deployed should help with logging. Once you check the Render logs, we can pinpoint the exact issue!
