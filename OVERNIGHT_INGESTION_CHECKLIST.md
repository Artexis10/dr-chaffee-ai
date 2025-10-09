# Overnight Ingestion Checklist

## Pre-Flight Checks ✈️

### 1. Database Migration
```powershell
cd backend
alembic current
# Should show: 004 (head)
```
✅ Migration 004 applied - video_type column ready

### 2. Environment Check
```powershell
# Check GPU
nvidia-smi

# Check disk space (need ~50GB for 1200h)
Get-PSDrive C | Select-Object Used,Free

# Check .env file
Test-Path .env
Get-Content .env | Select-String "DATABASE_URL"
```

### 3. Test Run (5 videos)
```powershell
cd backend/scripts
python ingest_youtube.py --source yt-dlp --limit 5 --newest-first
```

Expected output:
- ✅ Videos processed
- ✅ Segments inserted
- ✅ "Classified video X as 'monologue'" in logs
- ✅ No errors

### 4. Verify Classification Works
```powershell
python check_segments.py <video_id_from_test>
# Should show video_type in output
```

---

## Launch Command 🚀

### Recommended (Safe, Resumable)
```powershell
cd backend/scripts

# Start ingestion with logging
python ingest_youtube.py `
  --source yt-dlp `
  --limit 0 `
  --newest-first `
  --skip-shorts `
  2>&1 | Tee-Object -FilePath "ingestion_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
```

### Alternative (Incremental Batches)
```powershell
# Process in batches of 100
python ingest_youtube.py --source yt-dlp --limit 100 --newest-first
# Run multiple times until all processed
```

---

## Monitoring During Run

### Check Progress
```powershell
# In another terminal
Get-Content ingestion_*.log -Tail 50 -Wait
```

### Check GPU Usage
```powershell
# Every 5 minutes
while ($true) { nvidia-smi; Start-Sleep 300 }
```

### Check Database Growth
```sql
-- Run periodically
SELECT 
    COUNT(DISTINCT video_id) as videos_processed,
    COUNT(*) as total_segments,
    video_type,
    COUNT(DISTINCT video_id) as count_by_type
FROM segments
GROUP BY video_type;
```

---

## Expected Timeline

| Time | Progress | Videos | Segments |
|------|----------|--------|----------|
| 0h | Start | 0 | 0 |
| 4h | 20% | ~240 | ~36,000 |
| 8h | 40% | ~480 | ~72,000 |
| 12h | 60% | ~720 | ~108,000 |
| 16h | 80% | ~960 | ~144,000 |
| 20h | 95% | ~1140 | ~171,000 |
| 24h | 100% | ~1200 | ~180,000 |

---

## What to Look For

### Good Signs ✅
- "Classified video X as 'monologue'" in logs
- GPU utilization >80%
- Steady progress (2-3 videos/minute for monologues)
- No database errors
- Disk space decreasing steadily

### Warning Signs ⚠️
- GPU utilization <50% (bottleneck elsewhere)
- Repeated errors for same video (skip it)
- Disk space <10GB remaining (pause and cleanup)
- Database connection errors (check .env)

### Critical Issues 🚨
- Out of disk space → Stop immediately
- Database full → Check PostgreSQL config
- GPU out of memory → Reduce batch size
- Repeated crashes → Check logs for pattern

---

## If Something Goes Wrong

### Ingestion Crashes
```powershell
# Resume from where it left off
python ingest_youtube.py --source yt-dlp --limit 0 --skip-existing
```

### Classification Not Working
```sql
-- Check if column exists
SELECT column_name FROM information_schema.columns 
WHERE table_name='segments' AND column_name='video_type';

-- Manually classify if needed
UPDATE segments s
SET video_type = (
    SELECT CASE
        WHEN COUNT(DISTINCT speaker_label) = 1 THEN 'monologue'
        WHEN SUM(CASE WHEN speaker_label='GUEST' THEN 1 ELSE 0 END)::float / COUNT(*) > 0.15 THEN 'interview'
        ELSE 'monologue_with_clips'
    END
    FROM segments WHERE video_id = s.video_id
)
WHERE video_type IS NULL;
```

### Out of Disk Space
```powershell
# Clean up audio files (if stored locally)
Remove-Item backend/scripts/audio_storage/* -Recurse -Force

# Or disable audio storage
python ingest_youtube.py --no-store-audio --limit 0
```

### Database Too Slow
```sql
-- Create missing indexes
CREATE INDEX IF NOT EXISTS idx_segments_video_id ON segments(video_id);
CREATE INDEX IF NOT EXISTS idx_segments_video_type ON segments(video_type);
CREATE INDEX IF NOT EXISTS idx_segments_speaker_label ON segments(speaker_label);
```

---

## Post-Ingestion Verification

### 1. Check Totals
```sql
SELECT 
    COUNT(DISTINCT video_id) as total_videos,
    COUNT(*) as total_segments,
    COUNT(DISTINCT video_id) FILTER (WHERE video_type='monologue') as monologues,
    COUNT(DISTINCT video_id) FILTER (WHERE video_type='interview') as interviews,
    COUNT(DISTINCT video_id) FILTER (WHERE video_type='monologue_with_clips') as with_clips
FROM segments;
```

### 2. Check Classification
```sql
SELECT 
    video_type,
    COUNT(DISTINCT video_id) as videos,
    COUNT(*) as segments,
    ROUND(AVG(CASE WHEN speaker_label='Chaffee' THEN 1 ELSE 0 END) * 100, 1) as pct_chaffee
FROM segments
WHERE video_type IS NOT NULL
GROUP BY video_type;
```

### 3. Check Accuracy
```sql
SELECT 
    speaker_label,
    COUNT(*) as segments,
    ROUND(AVG(speaker_conf) * 100, 1) as avg_confidence
FROM segments
WHERE speaker_label IS NOT NULL
GROUP BY speaker_label;
```

### 4. Test Search
```sql
-- Test semantic search
SELECT video_id, text, speaker_label
FROM segments
WHERE embedding IS NOT NULL
ORDER BY embedding <-> (SELECT embedding FROM segments LIMIT 1)
LIMIT 10;
```

---

## Success Criteria

### Must Have ✅
- [ ] 1000+ videos processed
- [ ] 150,000+ segments
- [ ] All segments have video_type
- [ ] ~90% classified as 'monologue'
- [ ] No database errors
- [ ] Search working

### Nice to Have
- [ ] 1200 videos (full channel)
- [ ] <24 hours total time
- [ ] >90% GPU utilization
- [ ] All embeddings generated

---

## Final Commands

### Start Ingestion
```powershell
cd c:\Users\hugoa\Desktop\ask-dr-chaffee\backend\scripts
python ingest_youtube.py --source yt-dlp --limit 0 --newest-first 2>&1 | Tee-Object -FilePath "ingestion_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
```

### Monitor Progress (separate terminal)
```powershell
Get-Content backend/scripts/ingestion_*.log -Tail 50 -Wait
```

### Check Status
```powershell
python check_segments.py --stats
```

---

## When Complete

1. ✅ Review logs for errors
2. ✅ Run verification queries
3. ✅ Test search functionality
4. ✅ Test AI summarization with filtered data
5. ✅ Celebrate! 🎉

---

**You're ready to go! Good luck with the overnight run!** 🚀

**Estimated completion**: ~24 hours  
**Expected result**: 1200 videos, 180,000 segments, all classified  
**Overall accuracy**: 96.3%

**Ship it!** 🎯
