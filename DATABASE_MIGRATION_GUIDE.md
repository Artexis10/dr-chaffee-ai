# Database Migration Guide (Render Free Tier)

## Quick Fix for Role Errors

The errors you're seeing are **harmless** - they're just ownership warnings. Your data is being restored correctly (see the `COPY` statements).

However, to get a clean migration without errors, use these commands:

### Step 1: Backup with Clean Options

```bash
# Get your old database URL from Render
OLD_DB_URL="postgresql://drchaffee_db_user:password@host/drchaffee_db"

# Create clean backup (no ownership info)
pg_dump "$OLD_DB_URL" \
  --no-owner \
  --no-acl \
  --clean \
  --if-exists \
  > backup_clean.sql

# Verify backup size
ls -lh backup_clean.sql
# Should be ~516 MB
```

### Step 2: Restore to New Database

```bash
# Get your new FREE database URL from Render dashboard
NEW_DB_URL="postgresql://new_user:new_password@new_host/new_db"

# Restore (will be clean, no errors)
psql "$NEW_DB_URL" < backup_clean.sql
```

### Step 3: Verify Migration

```bash
# Check database size
psql "$NEW_DB_URL" -c "SELECT pg_size_pretty(pg_database_size(current_database()));"
# Should show ~516 MB

# Check table counts
psql "$NEW_DB_URL" -c "
SELECT 
  'videos' as table_name, COUNT(*) as count FROM videos
UNION ALL
SELECT 'segments', COUNT(*) FROM segments
UNION ALL
SELECT 'segment_embeddings', COUNT(*) FROM segment_embeddings
UNION ALL
SELECT 'answer_cache', COUNT(*) FROM answer_cache;
"

# Should match your old database counts
```

## Alternative: Ignore the Errors (They're Harmless)

If you already ran the restore and saw those errors, **your data is fine!** The errors are just about ownership, not data.

### Verify Everything Worked

```bash
# Connect to new database
psql "$NEW_DB_URL"

# Check tables exist
\dt

# Check data exists
SELECT COUNT(*) FROM videos;
SELECT COUNT(*) FROM segments;
SELECT COUNT(*) FROM segment_embeddings;

# If you see data, you're good! ✅
```

## Complete Migration Checklist

### Before Migration

- [ ] Get old database URL from Render
- [ ] Create new FREE PostgreSQL on Render (1 GB limit)
- [ ] Get new database URL

### Migration Steps

- [ ] Backup old database with `--no-owner --no-acl`
- [ ] Restore to new database
- [ ] Verify table counts match
- [ ] Verify database size (~516 MB)

### Update Environment Variables

- [ ] **Vercel:** Update `DATABASE_URL` in settings
- [ ] **Render Backend:** Update `DATABASE_URL` in environment variables
- [ ] **Local `.env`:** Update `DATABASE_URL` for testing

### Testing

- [ ] Test backend search endpoint
- [ ] Test frontend search
- [ ] Test answer generation
- [ ] Check logs for database errors

### Cleanup

- [ ] Wait 24-48 hours (make sure everything works)
- [ ] Delete old database from Render
- [ ] Save $7-15/month ✅

## Troubleshooting

### Issue: "COPY" statements show 0 rows

**Problem:** Data not being copied

**Solution:**
```bash
# Check if tables have data in old DB
psql "$OLD_DB_URL" -c "SELECT COUNT(*) FROM segments;"

# If 0, your old DB might be empty
# If > 0, try backup again with verbose flag
pg_dump "$OLD_DB_URL" --no-owner --no-acl --verbose > backup.sql
```

### Issue: "relation already exists"

**Problem:** Trying to restore to non-empty database

**Solution:**
```bash
# Drop all tables first (CAREFUL!)
psql "$NEW_DB_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Then restore
psql "$NEW_DB_URL" < backup_clean.sql
```

### Issue: Connection timeout

**Problem:** Database URL is wrong or database is down

**Solution:**
```bash
# Test connection
psql "$NEW_DB_URL" -c "SELECT 1;"

# If fails, check:
# 1. URL is correct (copy from Render dashboard)
# 2. Database is running (check Render dashboard)
# 3. IP whitelist (Render Free tier has no IP restrictions)
```

## Expected Output (Clean Migration)

```bash
$ psql "$NEW_DB_URL" < backup_clean.sql

SET
SET
SET
SET
CREATE EXTENSION
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE INDEX
CREATE INDEX
COPY 300        ← Videos copied
COPY 15000      ← Segments copied
COPY 15000      ← Embeddings copied
COPY 150        ← Cache entries copied
ALTER TABLE
ALTER TABLE
```

**No errors = perfect migration!**

## Post-Migration Verification Script

Save this as `verify_migration.sh`:

```bash
#!/bin/bash
set -e

NEW_DB_URL="$1"

if [ -z "$NEW_DB_URL" ]; then
    echo "Usage: ./verify_migration.sh 'postgresql://user:pass@host/db'"
    exit 1
fi

echo "🔍 Verifying database migration..."
echo ""

# Check database size
echo "📊 Database size:"
psql "$NEW_DB_URL" -t -c "SELECT pg_size_pretty(pg_database_size(current_database()));"
echo ""

# Check table counts
echo "📋 Table counts:"
psql "$NEW_DB_URL" -c "
SELECT 
  'videos' as table, COUNT(*) as count FROM videos
UNION ALL
SELECT 'segments', COUNT(*) FROM segments
UNION ALL
SELECT 'segment_embeddings', COUNT(*) FROM segment_embeddings
UNION ALL
SELECT 'answer_cache', COUNT(*) FROM answer_cache
ORDER BY table;
"
echo ""

# Check extensions
echo "🔌 Extensions:"
psql "$NEW_DB_URL" -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
echo ""

# Test vector search
echo "🔍 Testing vector search:"
psql "$NEW_DB_URL" -c "
SELECT COUNT(*) as embedding_count 
FROM segment_embeddings 
WHERE embedding IS NOT NULL;
"
echo ""

echo "✅ Migration verification complete!"
```

Run it:
```bash
chmod +x verify_migration.sh
./verify_migration.sh "postgresql://new_user:pass@host/db"
```

## Summary

**Your current errors are harmless!** The `COPY` statements show data is being restored.

**To get a clean migration:**
1. Use `pg_dump --no-owner --no-acl`
2. Restore with `psql`
3. Verify with counts

**After migration:**
- Update all environment variables
- Test thoroughly
- Delete old database after 24-48 hours
- Save $7-15/month ✅
