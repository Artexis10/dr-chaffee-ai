# Voice Embedding Storage Implementation

## Problem
- Database only stores text embeddings (1536-dim for semantic search)
- Voice embeddings (192-dim for speaker ID) are NOT stored
- Cannot regenerate speaker labels without voice embeddings

## Solution
Add `voice_embedding` column and store voice embeddings during ingestion.

## Changes Made

### 1. Database Schema ✅
**File**: `add_voice_embedding_column.sql`
```sql
ALTER TABLE segments ADD COLUMN IF NOT EXISTS voice_embedding jsonb;
CREATE INDEX IF NOT EXISTS idx_segments_voice_embedding ON segments USING gin (voice_embedding);
```

**Run**: `psql $DATABASE_URL < add_voice_embedding_column.sql`

### 2. Database Insert ✅
**File**: `backend/scripts/common/segments_database.py`
- Added `voice_embedding` to INSERT query (line 130)
- Extract `voice_embedding` from segment dict (line 146)
- Pass `voice_embedding` to VALUES (line 186)

### 3. TranscriptSegment Class ✅
**File**: `backend/scripts/common/transcript_common.py`
- Added `voice_embedding: Optional[list] = None` field (line 30)

### 4. Ingestion Conversion ✅
**File**: `backend/scripts/ingest_youtube.py`
- Added `voice_embedding` to segment_dict (line 981)

### 5. Enhanced ASR - Voice Embedding Propagation ⚠️ TODO
**File**: `backend/scripts/common/enhanced_asr.py`

Need to add code to copy voice embeddings from SpeakerSegment to TranscriptSegment.

**Location**: Around line 1242-1266 where segments get speaker info

**Add this code**:
```python
# After assigning speaker to segment (around line 1262)
# Find the corresponding speaker segment to get voice embedding
for spk_seg in speaker_segments:
    # Check if this speaker segment overlaps with transcript segment
    if not (segment['end'] <= spk_seg.start or segment['start'] >= spk_seg.end):
        # Found overlapping speaker segment
        if spk_seg.embedding:
            segment['voice_embedding'] = spk_seg.embedding
            break
```

### 6. Update regenerate_speaker_labels.py ✅
**File**: `regenerate_speaker_labels.py`

Change line 73 to use `voice_embedding` instead of `embedding`:
```python
query = """
SELECT id, video_id, speaker_label, voice_embedding, start_sec, end_sec
FROM segments
WHERE video_id = %s AND voice_embedding IS NOT NULL
ORDER BY start_sec
"""
```

And line 81:
```python
emb = np.array(row[3]) if row[3] else None  # row[3] is now voice_embedding
```

## Testing

After making changes:

```bash
# 1. Add database column
psql $DATABASE_URL < add_voice_embedding_column.sql

# 2. Re-ingest a test video
python backend/scripts/ingest_youtube.py --from-json test_video.json

# 3. Check voice embeddings are stored
python -c "
from backend.scripts.common.segments_database import SegmentsDatabase
import os
db = SegmentsDatabase(os.getenv('DATABASE_URL'))
with db.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM segments WHERE voice_embedding IS NOT NULL')
        print(f'Segments with voice embeddings: {cur.fetchone()[0]}')
"

# 4. Test regeneration
python regenerate_speaker_labels.py --dry-run --batch-size 10
```

## Summary

**Pyannote Pipeline**:
```
Audio 
  → Pyannote diarization (who spoke when)
  → Extract voice embeddings per segment (SpeechBrain ECAPA 192-dim)
  → Compare to Chaffee profile (speaker identification)
  → Store voice_embedding in database ← NEW!
  → Can regenerate labels anytime using stored voice embeddings
```

**Two Types of Embeddings**:
1. **Voice embeddings** (192-dim): Speaker identification, stored in `voice_embedding` column
2. **Text embeddings** (1536-dim): Semantic search, stored in `embedding` column

Both are useful for different purposes!
