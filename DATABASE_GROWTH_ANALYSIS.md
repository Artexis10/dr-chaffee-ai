# Database Growth Analysis

## Current State

- **Database size:** 516 MB
- **Videos processed:** ~300 videos
- **Average per video:** 516 MB ÷ 300 = **1.72 MB/video**

## Total Content Available

- **YouTube videos:** 1,300 videos
- **Zoom recordings:** ~100s (let's say 200)
- **Total content:** ~1,500 videos

## Growth Projection

### If You Process All Content

| Scenario | Videos | Database Size | Render Plan | Cost |
|----------|--------|---------------|-------------|------|
| **Current** | 300 | 516 MB | Free (< 1GB) | $0/month ✅ |
| **All YouTube** | 1,300 | ~2.2 GB | Starter (10GB) | $7/month |
| **YouTube + Zooms** | 1,500 | ~2.6 GB | Starter (10GB) | $7/month |

### Calculation
```
Current: 300 videos = 516 MB
Per video: 516 MB ÷ 300 = 1.72 MB/video

All YouTube: 1,300 videos × 1.72 MB = 2,236 MB (2.2 GB)
+ Zooms: 200 videos × 1.72 MB = 344 MB
Total: 2,580 MB (2.6 GB)
```

## Database Plan Comparison

| Plan | Storage | Cost | Your Usage |
|------|---------|------|------------|
| **Free** | 1 GB | $0/month | 516 MB (51%) ✅ |
| **Starter** | 10 GB | $7/month | Will need this |
| **Standard** | 50 GB | $15/month | Overkill |

## Key Findings

### 1. You Can Use Free Tier NOW ✅

**Current:** 516 MB < 1 GB limit

**Action:** Move to Render Free PostgreSQL
- Save $7/month immediately
- Safe for next ~284 videos

### 2. You'll Need Starter Eventually

**When:** After processing ~580 total videos (currently at 300)

**Timeline depends on:**
- How fast you ingest
- If you process all historical content

### 3. Growth Scenarios

#### Scenario A: Gradual Growth (Recommended)
- Process new videos only (2-3/week)
- Stay on free tier for ~2-3 years
- Eventually need Starter ($7/month)

#### Scenario B: Bulk Processing
- Process all 1,300 YouTube videos now
- Need Starter immediately ($7/month)
- Database: ~2.2 GB

#### Scenario C: Everything
- Process all 1,500 videos
- Need Starter ($7/month)
- Database: ~2.6 GB

## What's Taking Up Space?

Let me break down what's stored per video:

### Per Video (~1.72 MB average)

1. **Segments table** (~1.2 MB)
   - Transcript segments
   - Timestamps
   - Speaker labels
   - Metadata

2. **Segment embeddings** (~400 KB)
   - Nomic embeddings (768 dimensions)
   - One embedding per segment
   - ~50-100 segments per video

3. **Videos metadata** (~50 KB)
   - Video info
   - Processing status
   - Timestamps

4. **Answer cache** (~100 KB)
   - Cached Q&A responses
   - Grows over time

### Size Breakdown
```
Segments:           ~1.2 MB  (70%)
Embeddings:         ~400 KB  (23%)
Metadata:           ~50 KB   (3%)
Cache:              ~100 KB  (4%)
------------------------
Total per video:    ~1.72 MB
```

## Optimization Options

### Option 1: Stay on Free Tier Longer

**How:** Only process new videos (not historical)

**Timeline:**
- Current: 300 videos (516 MB)
- Free limit: 1 GB
- Remaining: 484 MB
- Can add: ~281 more videos
- At 2-3 videos/week: ~2-3 years on free tier

**Recommendation:** ✅ Do this

### Option 2: Aggressive Cleanup

**Remove old cached answers:**
```sql
-- Delete cache entries older than 30 days
DELETE FROM answer_cache 
WHERE created_at < NOW() - INTERVAL '30 days';

-- Potential savings: ~50-100 MB
```

**Remove duplicate segments:**
```sql
-- Check for duplicates
SELECT video_id, COUNT(*) 
FROM segments 
GROUP BY video_id 
HAVING COUNT(*) > 200;

-- Potential savings: ~20-50 MB
```

### Option 3: Compress Embeddings

**Current:** 768-dim float32 = 3,072 bytes per embedding

**Optimized:** Use float16 or quantization
- Savings: 50% (1,536 bytes per embedding)
- Trade-off: Slight quality loss (~1-2%)

**Not recommended** - complexity not worth it

## Cost Optimization Strategy

### Phase 1: Now (300 videos)
```
Frontend: Vercel         $0/month
Backend: Render Starter  $7/month
Database: Render FREE    $0/month  ✅ Move here
Cron: Local              $0/month
--------------------------------
Total:                   $7/month
```

**Action:** Move database to free tier NOW
- Save $7/month ($84/year)
- Safe for next 2-3 years

### Phase 2: After ~580 Videos (Future)
```
Frontend: Vercel         $0/month
Backend: Render Starter  $7/month
Database: Render Starter $7/month  (need 10GB)
Cron: Local              $0/month
--------------------------------
Total:                  $14/month
```

**When:** In 2-3 years (if processing new videos only)

### Phase 3: All Content (~1,500 Videos)
```
Frontend: Vercel         $0/month
Backend: Render Starter  $7/month
Database: Render Starter $7/month  (2.6 GB used)
Cron: Local              $0/month
--------------------------------
Total:                  $14/month
```

**When:** If you do bulk historical processing

## Recommendations

### Immediate Actions

1. **Move database to free tier** ✅
   ```sql
   -- Verify size first
   SELECT pg_size_pretty(pg_database_size('drchaffee_db'));
   -- Should show ~516 MB
   ```
   - In Render dashboard: Create new Free PostgreSQL
   - Migrate data (pg_dump/restore)
   - Delete old Starter database
   - **Save: $7/month**

2. **Move frontend to Vercel** ✅
   - Follow migration guide
   - **Save: $7/month**

3. **Use local cron** ✅
   - Already decided
   - **Save: $0.32/month**

**Total immediate savings: $14.32/month**

### Long-term Strategy

**Option A: Gradual Growth (Recommended)**
- Process only new videos (2-3/week)
- Stay on free DB tier for 2-3 years
- Eventually upgrade to Starter when needed

**Cost timeline:**
- Years 1-3: $7/month (backend only)
- Year 3+: $14/month (backend + database)

**Option B: Bulk Processing**
- Process all 1,300 YouTube videos now
- Need Starter DB immediately
- Cost: $14/month from start

**Recommendation:** Go with Option A
- Lower cost initially
- Can always bulk process later
- Free tier is generous

## Database Migration Guide

### Step 1: Create Free PostgreSQL on Render

1. Go to Render dashboard
2. Click "New +" → "PostgreSQL"
3. Select "Free" plan
4. Name: `drchaffee-db-free`
5. Create

### Step 2: Backup Current Database

```bash
# From your local machine
pg_dump "postgresql://user:pass@host/drchaffee_db" > backup.sql

# Verify backup
ls -lh backup.sql
# Should be ~516 MB
```

### Step 3: Restore to Free Database

```bash
# Get new database URL from Render dashboard
NEW_DB_URL="postgresql://user:pass@new-host/drchaffee_db_free"

# Restore
psql "$NEW_DB_URL" < backup.sql

# Verify
psql "$NEW_DB_URL" -c "SELECT COUNT(*) FROM segments;"
# Should match old database
```

### Step 4: Update Environment Variables

**Backend (Render):**
```bash
DATABASE_URL=postgresql://user:pass@new-host/drchaffee_db_free
```

**Frontend (Vercel):**
```bash
DATABASE_URL=postgresql://user:pass@new-host/drchaffee_db_free
```

### Step 5: Test

```bash
# Test backend
curl https://your-backend.onrender.com/search \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}'

# Should return results
```

### Step 6: Delete Old Database

1. Verify everything works for 24 hours
2. In Render dashboard, delete old Starter database
3. Save $7/month ✅

## Monitoring Database Growth

### Check Size Regularly

```sql
-- Total database size
SELECT pg_size_pretty(pg_database_size('drchaffee_db'));

-- Size by table
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Video count
SELECT COUNT(*) FROM videos;

-- Segment count
SELECT COUNT(*) FROM segments;

-- Average segments per video
SELECT AVG(segment_count) FROM (
    SELECT video_id, COUNT(*) as segment_count 
    FROM segments 
    GROUP BY video_id
) sub;
```

### Set Up Alerts

**Option 1: Manual Check (Monthly)**
```bash
# Add to your local cron
0 0 1 * * psql "$DATABASE_URL" -c "SELECT pg_size_pretty(pg_database_size('drchaffee_db'));" | mail -s "DB Size" you@email.com
```

**Option 2: Render Dashboard**
- Check database metrics in Render dashboard
- Set up notifications when approaching 1GB

## Growth Rate Estimates

### Current Rate (New Videos Only)
- **Videos/week:** 2-3
- **MB/week:** 3.4-5.2 MB
- **Time to 1GB:** ~2-3 years

### If Bulk Processing
- **Videos to process:** 1,000 (1,300 - 300)
- **Size increase:** ~1.7 GB
- **Total:** ~2.2 GB
- **Need Starter immediately**

## Cost Summary

### Current Setup (Before Optimization)
```
Frontend: Render Starter    $7/month
Backend: Render Starter     $7/month
Database: Render Starter    $7/month
Cron: Disabled              $0/month
-----------------------------------
Total:                     $21/month
```

### After Optimization (Recommended)
```
Frontend: Vercel FREE       $0/month  ✅
Backend: Render Starter     $7/month
Database: Render FREE       $0/month  ✅
Cron: Local                 $0/month  ✅
-----------------------------------
Total:                      $7/month
Savings:                   $14/month ($168/year)
```

### Future (When DB > 1GB)
```
Frontend: Vercel FREE       $0/month
Backend: Render Starter     $7/month
Database: Render Starter    $7/month  (when needed)
Cron: Local                 $0/month
-----------------------------------
Total:                     $14/month
```

## Final Recommendations

### Do This Now (Save $14/month):

1. ✅ **Move database to free tier**
   - Current: 516 MB (safe)
   - Limit: 1 GB
   - Savings: $7/month

2. ✅ **Move frontend to Vercel**
   - Free tier
   - Better performance
   - Savings: $7/month

3. ✅ **Use local cron**
   - Already decided
   - Free + faster

**Result: $21/month → $7/month**

### Long-term Strategy:

- Process new videos only (2-3/week)
- Stay on free DB tier for 2-3 years
- Upgrade to Starter DB when needed (~$7/month)
- Total cost: $7-14/month (vs current $21/month)

### If You Want All Historical Content:

- Bulk process all 1,300 videos
- Need Starter DB immediately ($7/month)
- Total cost: $14/month (vs current $21/month)
- Still saves $7/month

**Either way, you save money and get better performance.**

## Conclusion

**Your database is perfectly sized for the free tier!**

**Action plan:**
1. Move DB to free tier (save $7/month)
2. Move frontend to Vercel (save $7/month)
3. Use local cron (save $0.32/month)

**Total savings: $14.32/month ($172/year)**

**New monthly cost: $7 (just backend)**

This is the optimal setup for your use case.
