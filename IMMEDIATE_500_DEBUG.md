# Debugging Immediate 500 Errors on /answer Endpoint

## Symptom

Detailed answers return **500 Internal Server Error immediately** (not after 60s timeout).

## Most Likely Causes

### 1. Rate Limiting (3 detailed requests/minute)

**Check**: Are you testing repeatedly?

**Limit**: 3 detailed answers per minute per IP

**Solution**:
```bash
# Wait 60 seconds between tests
# Or test from different IPs
# Or temporarily disable rate limiting
```

**How to verify**:
Check Render logs for:
```
[Answer API] Rate limit exceeded for <IP>, style: detailed
```

### 2. Database Connection Failed

**Check**: Is DATABASE_URL set in Render?

**Solution**:
```bash
# In Render dashboard → Environment
# Verify DATABASE_URL is set and valid
psql $DATABASE_URL -c "SELECT 1"
```

**How to verify**:
Check Render logs for:
```
Database connection failed
Unable to connect to the database
```

### 3. OpenAI API Key Missing/Invalid

**Check**: Is OPENAI_API_KEY set in Render?

**Solution**:
```bash
# Test the key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**How to verify**:
Check Render logs for:
```
OpenAI API key not configured
401 Unauthorized
```

### 4. Embedding Service Down

**Check**: Is EMBEDDING_SERVICE_URL accessible?

**Solution**:
```bash
# Test the embedding service
curl $EMBEDDING_SERVICE_URL/health

# Or check if it's set
echo $EMBEDDING_SERVICE_URL
```

**How to verify**:
Check Render logs for:
```
Failed to generate query embedding
Connection refused
```

### 5. Cache Check Failing

**Check**: Does answer_cache table exist?

**Solution**:
```sql
-- Check if table exists
\d answer_cache

-- If not, create it
-- (see DETAILED_ANSWER_DEBUG.md for SQL)
```

**How to verify**:
Check Render logs for:
```
relation "answer_cache" does not exist
```

## Debugging Steps

### Step 1: Check Render Logs

With the new logging, you should see:

**Successful request**:
```
[Answer API] Query: "ketosis explained", maxContext: 100, style: detailed
[Answer API] Client ID: 123.456.789.0
[Answer API] Rate limit passed for detailed style
[Answer API] Processing query: "ketosis explained", style: detailed, refresh: false
```

**Failed request** (look for where it stops):
```
[Answer API] Query: "ketosis explained", maxContext: 100, style: detailed
[Answer API] Rate limit exceeded for 123.456.789.0, style: detailed
```

Or:
```
[Answer API] Query: "ketosis explained", maxContext: 100, style: detailed
[Answer API] Client ID: 123.456.789.0
[Answer API] Rate limit passed for detailed style
❌ [Answer API] Unhandled error: <error message>
[Answer API] Error stack: <full stack trace>
```

### Step 2: Test with curl

```bash
# Test detailed answer
curl -X POST https://your-app.onrender.com/api/answer \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test query",
    "style": "detailed",
    "top_k": 100
  }' \
  -v

# Look for:
# - HTTP status code (500 = error)
# - Response body (should have error message)
# - Response time (immediate = not timeout)
```

### Step 3: Check Environment Variables

In Render dashboard → Environment, verify:

```bash
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...
EMBEDDING_SERVICE_URL=https://...
SUMMARIZER_MODEL=gpt-4o-mini  # Optional
```

### Step 4: Test Components Individually

**Test database**:
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM segments"
```

**Test OpenAI**:
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Test embedding service**:
```bash
curl $EMBEDDING_SERVICE_URL/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'
```

## Quick Fixes

### Fix 1: Disable Rate Limiting Temporarily

In Render environment variables:
```bash
RATE_LIMIT_DETAILED=1000  # Effectively unlimited
```

### Fix 2: Skip Cache Check

Add `refresh=true` to your request:
```bash
curl -X POST https://your-app.onrender.com/api/answer \
  -d '{"query": "test", "style": "detailed", "refresh": true}'
```

### Fix 3: Use Concise Style

If detailed fails but concise works:
```bash
# Test with concise
curl -X POST https://your-app.onrender.com/api/answer \
  -d '{"query": "test", "style": "concise"}'
```

This tells us if it's a style-specific issue.

## Common Error Messages

### "Rate limit exceeded"

**Cause**: Too many requests (3 detailed/minute)

**Fix**: Wait 60 seconds or increase limit

### "Database configuration missing"

**Cause**: DATABASE_URL not set

**Fix**: Set DATABASE_URL in Render environment

### "OpenAI API key not configured"

**Cause**: OPENAI_API_KEY not set

**Fix**: Set OPENAI_API_KEY in Render environment

### "relation 'answer_cache' does not exist"

**Cause**: Table not created

**Fix**: Run migration or create table manually

### "Connection refused"

**Cause**: Embedding service down

**Fix**: Check EMBEDDING_SERVICE_URL or start service

## What the New Logging Shows

With the enhanced logging deployed, you'll see exactly where it fails:

```
[Answer API] Query: "..." ← Request received ✅
[Answer API] Client ID: ... ← Rate limit check starting ✅
[Answer API] Rate limit passed ← Rate limit OK ✅
[Answer API] Processing query ← Main handler starting ✅
[Answer API] Generating embedding ← Embedding service called ✅
[Answer API] Initial retrieval: X chunks ← Database query OK ✅
[callSummarizer] Generating answer ← OpenAI API called ✅
❌ [Answer API] Unhandled error ← Something failed ❌
```

The last log line before the error tells you exactly what failed.

## Next Steps

1. **Check Render logs** - look for the new detailed logging
2. **Identify where it stops** - that's where the error is
3. **Share the error message** - I can help fix it
4. **Test components** - verify database, OpenAI, embedding service

The enhanced logging will make it obvious what's failing!
