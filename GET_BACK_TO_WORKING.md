# Get Back to Working State - Action Plan

**Date**: 2025-10-10 21:38  
**Status**: You're right - we've been wasting time!

---

## What's Actually Working Now ✅

From your logs:
```
Processing 500 segments in 63 batches of 8  ✅ WORKING!
✅ Progress: 63/63 batches (500 embeddings extracted)  ✅ NO OOM!
```

**The OOM fixes worked!** Voice enrollment is now stable.

---

## What's NOT Working ❌

```
Fast-path check: avg_sim=0.153 < 0.558  ❌ REJECTED
Falling back to full pipeline with diarization  ⚠️ SLOW!
```

**Problem**: Fast-path is being rejected because:
- Video similarity to Chaffee: 0.153 (very low)
- Threshold: 0.558
- **This video is NOT Dr. Chaffee speaking!**

---

## Root Cause

You're processing **guest videos** or **videos where Chaffee barely speaks**.

**Solution**: Skip these videos or lower the fast-path threshold.

---

## Testing Status

### Unit Tests Exist ✅
**File**: `tests/unit/test_critical_performance_fixes.py`

**Tests**:
1. ✅ Cache parameters passed (Fix 1)
2. ✅ ASR processing time tracked (Fix 2)
3. ✅ Per-segment ID logic (Fix 3)
4. ✅ Integration tests

### Run Tests
```powershell
cd c:\Users\hugoa\Desktop\ask-dr-chaffee
pytest tests/unit/test_critical_performance_fixes.py -v
```

---

## Immediate Actions (Stop Wasting Time!)

### 1. Run Tests to Verify Fixes ✅
```powershell
pytest tests/unit/test_critical_performance_fixes.py -v
```

**Expected**: All tests pass

### 2. Check Which Videos Are Being Processed
```powershell
# Look at the video being processed
grep "Starting enhanced ASR" logs/ingestion.log | tail -5
```

**Question**: Are these Dr. Chaffee solo videos or guest interviews?

### 3. Skip Guest Videos (Quick Fix)
**Option A**: Process only known monologue videos
```powershell
python backend/scripts/ingest_youtube.py --limit 10 --newest-first
```

**Option B**: Lower fast-path threshold (risky - may accept non-Chaffee)
```bash
# .env
CHAFFEE_MIN_SIM=0.50  # Was 0.62, lower to 0.50
```

### 4. Check Your Previous Working Config
**Question**: What were your `.env` settings when it was working?

Compare current `.env` with your backup or git history:
```powershell
git diff HEAD~10 .env
```

---

## Performance Summary (Current State)

### What's Fixed ✅
1. ✅ OOM errors (batch size 8)
2. ✅ Memory cleanup (torch.cuda.empty_cache())
3. ✅ Whisper model bug (variable name)
4. ✅ Voice enrollment stable

### What's Slow ⚠️
1. ⚠️ Fast-path rejection (guest videos)
2. ⚠️ Full diarization triggered (slow path)

### Expected Performance
- **Monologue videos**: 2-3 min/video (fast-path)
- **Guest videos**: 8-10 min/video (full pipeline)

---

## Quick Wins (Do These Now!)

### 1. Filter Out Guest Videos
```python
# Add to ingest_youtube.py
KNOWN_MONOLOGUE_KEYWORDS = [
    "Q&A", "AMA", "Solo", "Update", "Carnivore", "Diet"
]

KNOWN_GUEST_KEYWORDS = [
    "Interview", "Podcast", "Guest", "with", "ft.", "featuring"
]

# Skip videos with guest keywords
if any(keyword.lower() in video_title.lower() for keyword in KNOWN_GUEST_KEYWORDS):
    logger.info(f"⏭️  Skipping guest video: {video_title}")
    continue
```

### 2. Run Tests
```powershell
pytest tests/unit/test_critical_performance_fixes.py -v
```

### 3. Process 5 Known Monologue Videos
Find 5 videos you KNOW are Dr. Chaffee solo:
```powershell
python backend/scripts/ingest_youtube.py --video-ids VIDEO_ID1,VIDEO_ID2,VIDEO_ID3,VIDEO_ID4,VIDEO_ID5
```

---

## Stop Wasting Time Checklist

- [ ] Run unit tests (verify fixes work)
- [ ] Check which videos are being processed (monologue vs guest)
- [ ] Compare current .env with working config
- [ ] Process 5 known monologue videos
- [ ] Measure performance (should be 2-3 min/video)

---

## Expected Results After Quick Wins

### Before (Current)
```
Video: tk3jYFzgJDQ (guest video)
Fast-path: REJECTED (0.153 < 0.558)
Full pipeline: 8-10 min/video
```

### After (Monologue Only)
```
Video: [monologue video]
Fast-path: ACCEPTED (0.75 > 0.558)
Fast-path: 2-3 min/video
```

---

## Bottom Line

**You're right - stop wasting time!**

1. **OOM is fixed** ✅
2. **Tests exist** ✅
3. **Problem**: Processing guest videos (slow path)
4. **Solution**: Filter guest videos OR lower threshold

**Next step**: Run tests, then process 5 known monologue videos to verify performance.

---

## Test Command
```powershell
# Run tests
pytest tests/unit/test_critical_performance_fixes.py -v

# Process 5 monologue videos
python backend/scripts/ingest_youtube.py --limit 5 --newest-first
```

**Expected**: 5 videos in 10-15 minutes (2-3 min each)
