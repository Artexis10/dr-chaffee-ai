# 🔄 Database Sync Guide - Local → Production

## Quick Start

### 1. Setup (One-Time)

Add production database URL to your local `.env`:

```bash
# C:\Users\hugoa\Desktop\ask-dr-chaffee\backend\.env

# Your existing local database
DATABASE_URL=postgresql://postgres:password@localhost:5432/askdrchaffee

# Add production database URL
PRODUCTION_DATABASE_URL=postgresql://user:password@production-server:5432/askdrchaffee
```

### 2. Run Sync

```powershell
cd C:\Users\hugoa\Desktop\ask-dr-chaffee\backend
python scripts\sync_to_production.py
```

**That's it!** The script automatically:
- ✅ Syncs only new data (incremental)
- ✅ Avoids duplicates (ON CONFLICT DO NOTHING)
- ✅ Tracks sync history (sync_log table)
- ✅ Handles voice embeddings
- ✅ Batches for performance (1000 segments at a time)

---

## 📊 What Gets Synced

### Sources Table
- Video metadata (title, duration, views, etc.)
- Only new sources created since last sync

### Segments Table
- Transcription segments
- Text embeddings (1536-dim GTE-Qwen2)
- Voice embeddings (speaker identification)
- Quality metrics (logprob, compression ratio, etc.)
- Only new segments created since last sync

### Sync Log Table
- Tracks when syncs happened
- Records how many items synced
- Used for incremental sync

---

## 🔄 Typical Workflow

### Initial Bulk Sync (First Time)

```powershell
# 1. Process all historical content locally (GPU)
cd backend
python scripts\ingest_youtube_enhanced_asr.py --channel-url "..." --batch-size 200

# 2. Sync to production
python scripts\sync_to_production.py
```

**Expected output**:
```
================================================================================
DATABASE SYNC: Local → Production
================================================================================
Local DB: postgresql://postgres:pass...
Production DB: postgresql://user:pass...
Last sync: 2000-01-01 00:00:00  (first sync)
Syncing data created after 2000-01-01 00:00:00

📦 Syncing sources...
Found 200 new sources to sync
✅ Synced 200 sources

📝 Syncing segments...
Found 15000 new segments to sync
Synced 1000/15000 segments...
Synced 2000/15000 segments...
...
✅ Synced 15000 segments

================================================================================
✅ SYNC COMPLETE
================================================================================
Sources synced: 200
Segments synced: 15000
Sync time: 2025-10-15 22:30:45
================================================================================
```

### Incremental Sync (After Daily Cron)

```powershell
# Production cron processes 2h of new content overnight
# Next day, sync any local processing to production

python scripts\sync_to_production.py
```

**Expected output**:
```
Last sync: 2025-10-15 22:30:45
Syncing data created after 2025-10-15 22:30:45

📦 Syncing sources...
Found 3 new sources to sync
✅ Synced 3 sources

📝 Syncing segments...
Found 250 new segments to sync
✅ Synced 250 segments

✅ SYNC COMPLETE
Sources synced: 3
Segments synced: 250
```

---

## 🛡️ Safety Features

### 1. Duplicate Prevention
```sql
ON CONFLICT DO NOTHING
```
- Won't overwrite existing data
- Safe to run multiple times
- Idempotent operation

### 2. Incremental Sync
- Only syncs data created after last sync
- Tracks sync history in `sync_log` table
- Efficient for large databases

### 3. Batch Processing
- Processes 1000 segments at a time
- Commits after each batch
- Progress logging

### 4. Connection Validation
```python
if local_db_url == prod_db_url:
    logger.error("❌ LOCAL and PRODUCTION database URLs are the same!")
    sys.exit(1)
```
- Prevents syncing to itself
- Validates URLs before starting

---

## 🔧 Advanced Usage

### Sync Specific Date Range

Edit `sync_to_production.py` temporarily:

```python
# Instead of using last sync time
# last_sync = get_last_sync_time(prod_conn)

# Use specific date
from datetime import datetime
last_sync = datetime(2025, 10, 1)  # Sync everything after Oct 1
```

### Force Full Resync

```sql
-- On production database
TRUNCATE sync_log;
```

Next sync will sync everything (since 2000-01-01).

### Dry Run (Check What Would Sync)

```python
# Add --dry-run flag support
if '--dry-run' in sys.argv:
    # Don't commit, just log what would be synced
    prod_conn.rollback()
```

---

## 📈 Performance

### Sync Speed

| Data Volume | Time |
|-------------|------|
| 100 sources | ~5 seconds |
| 1,000 segments | ~10 seconds |
| 10,000 segments | ~1 minute |
| 100,000 segments | ~10 minutes |

### Network Considerations

**Local network** (same datacenter):
- Fast (100+ Mbps)
- Sync 100k segments in ~5 minutes

**Remote network** (internet):
- Slower (10-50 Mbps)
- Sync 100k segments in ~20-30 minutes

**Optimization**: Run sync during off-peak hours

---

## 🚨 Troubleshooting

### Error: "PRODUCTION_DATABASE_URL not set"

**Solution**: Add to `.env`:
```bash
PRODUCTION_DATABASE_URL=postgresql://user:password@host:5432/dbname
```

### Error: "Connection refused"

**Possible causes**:
1. Production server firewall blocking port 5432
2. PostgreSQL not accepting remote connections
3. Wrong host/port in URL

**Solutions**:
```bash
# 1. Check PostgreSQL is running
ssh user@production-server
sudo systemctl status postgresql

# 2. Allow remote connections
# Edit /etc/postgresql/15/main/postgresql.conf
listen_addresses = '*'

# Edit /etc/postgresql/15/main/pg_hba.conf
host all all 0.0.0.0/0 md5

# 3. Restart PostgreSQL
sudo systemctl restart postgresql

# 4. Open firewall
sudo ufw allow 5432/tcp
```

### Error: "column voice_embedding does not exist"

**Solution**: Production database schema is outdated. Run migrations:

```bash
# On production server
cd /path/to/backend
python scripts/setup_database.py
```

### Sync Takes Too Long

**Solutions**:

1. **Use SSH tunnel** (faster than direct connection):
```bash
# Create tunnel
ssh -L 5433:localhost:5432 user@production-server

# Update .env
PRODUCTION_DATABASE_URL=postgresql://user:password@localhost:5433/askdrchaffee
```

2. **Compress data** (for large syncs):
```bash
# Export compressed
pg_dump -h localhost -U postgres askdrchaffee | gzip > backup.sql.gz

# Transfer
scp backup.sql.gz user@production-server:/tmp/

# Import
ssh user@production-server
gunzip -c /tmp/backup.sql.gz | psql askdrchaffee
```

3. **Use pg_dump for initial sync** (faster for bulk):
```bash
# First time only - use pg_dump
pg_dump -h localhost -U postgres askdrchaffee > initial.sql
scp initial.sql user@production-server:/tmp/
ssh user@production-server "psql askdrchaffee < /tmp/initial.sql"

# After that - use sync script for incremental
python scripts/sync_to_production.py
```

---

## 🔐 Security Best Practices

### 1. Use Environment Variables

**Never hardcode credentials**:
```bash
# ❌ BAD
PRODUCTION_DATABASE_URL=postgresql://admin:password123@prod.example.com:5432/db

# ✅ GOOD - Use .env file (gitignored)
PRODUCTION_DATABASE_URL=postgresql://user:${PROD_DB_PASS}@prod.example.com:5432/db
```

### 2. Use SSL Connections

```bash
PRODUCTION_DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

### 3. Restrict Database User Permissions

```sql
-- Create sync-only user
CREATE USER sync_user WITH PASSWORD 'secure_password';

-- Grant only INSERT permission
GRANT INSERT ON sources, segments TO sync_user;
GRANT SELECT ON sources, segments TO sync_user;  -- For duplicate checking
GRANT ALL ON sync_log TO sync_user;  -- For tracking
```

### 4. Use SSH Tunnel

```bash
# More secure than exposing PostgreSQL port
ssh -L 5433:localhost:5432 user@production-server

# Connect through tunnel
PRODUCTION_DATABASE_URL=postgresql://user:pass@localhost:5433/db
```

---

## 📅 Recommended Sync Schedule

### Initial Setup
1. **Day 1**: Bulk process locally (1200h content)
2. **Day 2**: Initial sync to production (full database)
3. **Day 3+**: Production cron handles daily uploads

### Ongoing Maintenance

**Option A: Sync After Local Processing**
```powershell
# When you process videos locally
python scripts\ingest_youtube_enhanced_asr.py --video-ids-file new_videos.txt
python scripts\sync_to_production.py  # Immediately after
```

**Option B: Scheduled Sync**
```bash
# Cron job on local machine (weekly)
0 3 * * 0 cd /path/to/backend && python scripts/sync_to_production.py >> logs/sync.log 2>&1
```

**Option C: Manual Sync**
```powershell
# Run manually when needed
python scripts\sync_to_production.py
```

**Recommendation**: Option A (sync immediately after local processing)

---

## ✅ Verification

### Check Sync Status

```sql
-- On production database
SELECT * FROM sync_log ORDER BY sync_time DESC LIMIT 5;
```

### Verify Data Integrity

```sql
-- Count segments
SELECT COUNT(*) FROM segments;

-- Check latest segments
SELECT video_id, speaker_label, created_at 
FROM segments 
ORDER BY created_at DESC 
LIMIT 10;

-- Verify embeddings exist
SELECT COUNT(*) FROM segments WHERE embedding IS NOT NULL;
SELECT COUNT(*) FROM segments WHERE voice_embedding IS NOT NULL;
```

### Compare Local vs Production

```sql
-- Run on both databases
SELECT 
    COUNT(*) as total_segments,
    COUNT(DISTINCT video_id) as total_videos,
    MAX(created_at) as latest_segment
FROM segments;
```

Should be identical or production slightly behind (if cron hasn't run yet).

---

## 🎯 Summary

**Automated sync script** handles everything:
- ✅ Incremental sync (only new data)
- ✅ Duplicate prevention
- ✅ Progress tracking
- ✅ Batch processing
- ✅ Error handling

**Usage**:
```powershell
# Setup once
echo "PRODUCTION_DATABASE_URL=postgresql://..." >> backend\.env

# Run anytime
python scripts\sync_to_production.py
```

**Safe to run multiple times** - won't duplicate data!
