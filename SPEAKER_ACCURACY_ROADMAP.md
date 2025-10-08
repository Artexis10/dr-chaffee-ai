# Speaker Accuracy Roadmap - TDD Approach

## Current Status: ❌ BROKEN

Video `1oKru2X3AvU` (interview with Pascal Johns):
- **Expected**: ~50% Chaffee, ~50% Guest
- **Actual**: 100% Chaffee (completely wrong!)

## Root Causes Identified

### 1. ✅ Pyannote Clustering Threshold Not Configured
- **Issue**: Threshold from `.env` not being passed to pyannote
- **Fix**: Added `pipeline.klustering.clustering.threshold = 0.5`
- **Status**: Fixed but needs testing

### 2. ✅ Per-Segment ID Overriding Clusters  
- **Issue**: Low-confidence segments being mislabeled
- **Fix**: Trust diarization clusters, skip per-segment re-identification
- **Status**: Fixed but only helps if pyannote detects 2 clusters

### 3. ❌ Pyannote Still Merging Speakers
- **Issue**: Even with threshold=0.5, pyannote returns 1 cluster
- **Possible causes**:
  - Threshold not being set correctly (pipeline structure unknown)
  - Voices too similar for clustering to separate
  - Need to use `min_speakers=2` for interviews

## TDD Action Plan

### Phase 1: Write Comprehensive Tests ✅

1. **Integration Test** (`test_speaker_accuracy.py`) ✅
   - Detects 100% Chaffee in interview videos
   - Checks for low-confidence segments
   - Verifies speaker distribution

2. **Unit Test** (`test_cluster_speaker_assignment.py`) ✅
   - Tests clustering threshold configuration
   - Tests cluster assignment logic
   - Tests per-segment fallback

### Phase 2: Fix Pyannote Clustering 🔄

**Test First:**
```python
def test_pyannote_detects_two_speakers_in_interview():
    """
    Test that pyannote detects 2 distinct speakers in interview video.
    
    Video: 1oKru2X3AvU (Chaffee + Pascal Johns)
    Expected: 2 clusters
    Actual: 1 cluster (FAILING)
    """
    audio_path = download_video('1oKru2X3AvU')
    clusters = diarize_turns(audio_path, min_speakers=2, max_speakers=2)
    
    unique_speakers = set(c[2] for c in clusters)
    assert len(unique_speakers) == 2, f"Expected 2 speakers, got {len(unique_speakers)}"
```

**Implementation Options:**

**Option A: Force min_speakers=2 for interviews**
```python
# Detect interview from title
is_interview = '|' in video.title or 'interview' in video.title.lower()
min_speakers = 2 if is_interview else 1
max_speakers = 2 if is_interview else None
```

**Option B: Lower clustering threshold further**
```python
# Try threshold=0.3 (more aggressive)
PYANNOTE_CLUSTERING_THRESHOLD=0.3
```

**Option C: Use different diarization model**
```python
# Try pyannote/speaker-diarization-3.1 (older, might work better)
```

### Phase 3: Verify Fix Works 🔄

1. Re-ingest video 1oKru2X3AvU
2. Run integration tests
3. Check segments: `python check_segments.py 1oKru2X3AvU`
4. Verify ~50/50 distribution

### Phase 4: Prevent Regressions ✅

1. Add test to CI/CD
2. Test on multiple interview videos
3. Document expected behavior

## Current Blockers

1. ✅ ~~Pyannote pipeline structure unknown~~ - SOLVED
   - Found correct path: `pipeline.clustering.threshold`

2. ❌ **Clustering threshold not enough** - CONFIRMED
   - Tried 0.6 → 0.4 → 0.3
   - Pyannote still returns 1 cluster
   - Voices too similar for VBx clustering algorithm

3. ❌ **Fundamental Problem: No Guest Voice Profile**
   - Per-segment identification compares only to Chaffee
   - Without Guest profile, can't distinguish similar voices
   - Voice embeddings show variance but can't label which is which

## Real Solution Required

The fundamental issue is that **we can't distinguish similar voices without a reference**:

### Option A: Use Variance-Based Splitting (Recommended)
When variance is high (>0.05), split cluster into 2 groups:
- Group 1: Segments with high similarity to Chaffee → Chaffee
- Group 2: Segments with low similarity to Chaffee → Guest

### Option B: Force min_speakers=2 for Interviews
Detect interviews from title and force pyannote to find 2 speakers.
**Problem**: Breaks for 3+ person panels, monologues

### Option C: Create Guest Profiles
Enroll guest voices from their segments.
**Problem**: Requires manual enrollment, complex workflow

### Recommended: Option A
```python
if variance > 0.05:  # High variance = mixed speakers
    # Split by similarity to Chaffee
    for segment in segments:
        if similarity_to_chaffee > 0.65:
            segment.speaker = "Chaffee"
        else:
            segment.speaker = "GUEST"
```

## Success Criteria

- [ ] Pyannote detects 2 clusters for interview videos
- [ ] Speaker distribution is ~50/50 for interviews
- [ ] <2 low-confidence segments (was 12)
- [ ] Integration tests pass
- [ ] 100% Chaffee for monologue videos

## Lessons Learned

1. **TDD is essential** - Write tests before implementing
2. **Test with real data** - Integration tests catch real issues
3. **One fix at a time** - Don't stack multiple fixes
4. **Verify each step** - Ensure fix actually works before moving on
5. **Debug thoroughly** - Add logging to understand what's happening
