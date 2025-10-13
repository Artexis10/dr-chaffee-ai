# Migration Plan: video_id → source_id

## Rationale
The term `video_id` is misleading since sources can be:
- YouTube videos
- Local audio files
- Podcasts
- API sources
- Any audio content

Renaming to `source_id` makes the schema more accurate and future-proof.

## Scope
- **Database tables**: `sources`, `segments`
- **Python files**: ~880 files with 7853 matches (mostly in venv, ~50 in actual code)
- **Core files to update**:
  - `backend/scripts/common/segments_database.py` (38 matches)
  - `backend/scripts/ingest_youtube.py` (83 matches)
  - `backend/scripts/common/enhanced_transcript_fetch.py` (41 matches)
  - `backend/scripts/common/transcript_fetch.py` (35 matches)

## Migration Steps

### Phase 1: Database Schema Migration (SAFE - Additive)
1. Add `source_id` column to `sources` table (copy from `video_id`)
2. Add `source_id` column to `segments` table (copy from `video_id`)
3. Create indexes on `source_id` columns
4. Keep `video_id` columns for backward compatibility

### Phase 2: Code Migration (Gradual)
1. Update `segments_database.py` to use `source_id` internally
2. Update ingestion scripts to use `source_id`
3. Update API/frontend to use `source_id`
4. Add deprecation warnings for `video_id` usage

### Phase 3: Cleanup (After Testing)
1. Drop `video_id` columns from tables
2. Remove backward compatibility code
3. Update all remaining references

## SQL Migration Script

```sql
-- Phase 1: Add source_id columns (SAFE - no data loss)
BEGIN;

-- Add source_id to sources table
ALTER TABLE sources 
ADD COLUMN IF NOT EXISTS source_id VARCHAR(255);

-- Copy video_id to source_id
UPDATE sources 
SET source_id = video_id 
WHERE source_id IS NULL;

-- Add source_id to segments table
ALTER TABLE segments 
ADD COLUMN IF NOT EXISTS source_id VARCHAR(255);

-- Copy video_id to source_id
UPDATE segments 
SET source_id = video_id 
WHERE source_id IS NULL;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_sources_source_id ON sources(source_id);
CREATE INDEX IF NOT EXISTS idx_segments_source_id ON segments(source_id);

COMMIT;

-- Phase 3: Cleanup (RUN AFTER TESTING!)
-- BEGIN;
-- ALTER TABLE sources DROP COLUMN video_id;
-- ALTER TABLE segments DROP COLUMN video_id;
-- COMMIT;
```

## Recommendation

**DO NOT run this migration now!** This is a major refactoring that should be:
1. Planned carefully
2. Tested in a staging environment
3. Run during a maintenance window
4. Done with proper backups

For now, we can:
- Keep using `video_id` (it works fine)
- Add `source_id` as an alias in new code
- Plan the full migration for later

## Immediate Action

Focus on fixing the **text embedding GPU issue** first, which is more critical for performance.
