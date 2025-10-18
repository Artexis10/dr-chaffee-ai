# New Database Setup Guide

## Step 1: Run Migrations

Your project uses Alembic for database migrations. Here's how to set up the new database:

### Option A: Use the Migration Script (Easiest)

```bash
cd /home/hugo-kivi/Desktop/personal/dr-chaffee-ai/backend

# Set your NEW database URL
export DATABASE_URL="postgresql://new_user:new_pass@new_host/new_db"

# Run migrations
./run_migrations.sh
```

This will:
1. Create the `vector` extension
2. Create all tables
3. Set up indexes
4. Apply all schema updates

### Option B: Manual Alembic Commands

```bash
cd /home/hugo-kivi/Desktop/personal/dr-chaffee-ai/backend

# Activate virtual environment
source .venv/bin/activate

# Set database URL
export DATABASE_URL="postgresql://new_user:new_pass@new_host/new_db"

# Check current migration status
alembic current

# Show migration history
alembic history

# Apply all migrations
alembic upgrade head
```

## Step 2: Verify Migration

```bash
# Check that vector extension exists
psql "$DATABASE_URL" -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# Check tables were created
psql "$DATABASE_URL" -c "\dt"

# Should show:
# - sources
# - videos  
# - segments
# - segment_embeddings
# - answer_cache
# - alembic_version
```

## Step 3: Restore Your Data

Now that the schema is set up, restore your data:

```bash
# Restore from backup
psql "$DATABASE_URL" < backup_clean.sql
```

**Note:** If you already restored data before migrations, you might get "relation already exists" errors. That's okay - the data is there.

## Alternative: Fresh Start (If Restore Had Issues)

If your restore had problems, start fresh:

### 1. Drop and Recreate Database

```bash
# Connect to new database
psql "$DATABASE_URL"

# Drop everything
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
\q
```

### 2. Run Migrations First

```bash
cd /home/hugo-kivi/Desktop/personal/dr-chaffee-ai/backend
export DATABASE_URL="postgresql://..."
./run_migrations.sh
```

### 3. Then Restore Data

```bash
psql "$DATABASE_URL" < backup_clean.sql
```

## Migration Details

Your migrations include:

1. **001_initial_schema.py** - Creates base tables + pgvector extension
2. **002_fix_duplicates_and_speaker_labels.py** - Data cleanup
3. **003_update_embedding_dimensions.py** - Supports multiple embedding sizes
4. **004_add_video_type_classification.py** - Adds video_type column
5. **008_add_missing_segment_columns.py** - Adds re_asr, is_overlap columns
6. **009_create_answer_cache_table.py** - Creates answer cache
7. **70e48355c89e_add_voice_embedding_column.py** - Adds voice embeddings

## Troubleshooting

### Issue: "alembic: command not found"

```bash
pip install alembic psycopg2-binary python-dotenv
```

### Issue: "relation already exists"

This means tables were created during restore. That's fine! Check if data is there:

```bash
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM videos;"
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM segments;"
```

If you see data, you're good!

### Issue: "vector extension not found"

```bash
# Manually create extension
psql "$DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Issue: Migration version mismatch

```bash
# Check current version
alembic current

# If it shows a version, your DB already has migrations applied
# If it shows nothing, run:
alembic upgrade head
```

## Final Verification

```bash
# 1. Check database size
psql "$DATABASE_URL" -c "SELECT pg_size_pretty(pg_database_size(current_database()));"
# Should show ~516 MB

# 2. Check table counts
psql "$DATABASE_URL" -c "
SELECT 
  'videos' as table, COUNT(*) FROM videos
UNION ALL
SELECT 'segments', COUNT(*) FROM segments
UNION ALL
SELECT 'segment_embeddings', COUNT(*) FROM segment_embeddings
UNION ALL
SELECT 'answer_cache', COUNT(*) FROM answer_cache;
"

# 3. Test vector search
psql "$DATABASE_URL" -c "
SELECT COUNT(*) 
FROM segment_embeddings 
WHERE embedding IS NOT NULL 
LIMIT 10;
"

# 4. Check extensions
psql "$DATABASE_URL" -c "\dx"
# Should show 'vector' extension
```

## Update Environment Variables

Once migration is complete, update all services:

### Vercel (Frontend)
1. Go to Vercel dashboard
2. Project settings → Environment Variables
3. Update `DATABASE_URL` to new database URL
4. Redeploy

### Render (Backend)
1. Go to Render dashboard
2. Backend service → Environment
3. Update `DATABASE_URL` to new database URL
4. Service will auto-restart

### Local Development
```bash
# Update .env file
nano /home/hugo-kivi/Desktop/personal/dr-chaffee-ai/backend/.env

# Change DATABASE_URL to new database
DATABASE_URL=postgresql://new_user:new_pass@new_host/new_db
```

## Complete Checklist

- [ ] Run migrations on new database
- [ ] Verify vector extension exists
- [ ] Verify all tables created
- [ ] Restore data from backup
- [ ] Verify data counts match old database
- [ ] Test vector search works
- [ ] Update Vercel environment variables
- [ ] Update Render environment variables
- [ ] Update local .env file
- [ ] Test frontend search
- [ ] Test backend API
- [ ] Wait 24-48 hours to ensure stability
- [ ] Delete old database
- [ ] Save $7-15/month ✅

## Quick Commands Reference

```bash
# Run migrations
cd backend && export DATABASE_URL="..." && ./run_migrations.sh

# Verify
psql "$DATABASE_URL" -c "\dt"
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM segments;"

# Restore data
psql "$DATABASE_URL" < backup_clean.sql

# Test
curl https://your-backend.onrender.com/search \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "ketosis", "limit": 5}'
```
