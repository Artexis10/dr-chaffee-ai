# Speaker Identification Array Shape Fix

## Problem

Speaker identification was failing with error:
```
Speaker identification failed: setting an array element with a sequence. 
The requested array has an inhomogeneous shape after 1 dimensions. 
The detected shape was (191,) + inhomogeneous part.
```

## Root Cause

When pyannote detected high variance in a cluster (indicating multiple speakers merged together), the code added a special marker `('split_cluster', None, None)` to the `cluster_embeddings` list. 

However, the code then tried to compute `np.mean(cluster_embeddings, axis=0)` on this mixed list containing both numpy arrays and the tuple marker, causing the inhomogeneous shape error.

## Solution

Modified `backend/scripts/common/enhanced_asr.py` to:

1. **Check for split marker before computing cluster embedding** (line 934-948)
   - Detect if `cluster_embeddings` contains the `'split_cluster'` marker
   - If yes, skip cluster-level embedding computation
   - Set dummy values for cluster-level variables (won't be used)

2. **Wrap cluster-level identification in conditional** (line 953-1047)
   - Only perform cluster-level speaker identification if NOT marked for split
   - Includes: similarity computation, threshold checks, margin calculation

3. **Log appropriate message** (line 1048-1050)
   - If split: Log that cluster is marked for per-segment identification
   - If not split: Log cluster-level speaker assignment

## Code Changes

### Before (Broken):
```python
# Always computed cluster embedding, even with split marker
cluster_embedding = np.mean(cluster_embeddings, axis=0)  # ❌ FAILS with mixed types

# Always did cluster-level identification
for profile_name, profile in profiles.items():
    sim = enrollment.compute_similarity(cluster_embedding, profile)
    # ...
```

### After (Fixed):
```python
# Check for split marker first
has_split_marker = any(isinstance(item, tuple) and len(item) == 3 and item[0] == 'split_cluster' 
                      for item in cluster_embeddings)

if has_split_marker:
    # Skip cluster-level computation
    cluster_embedding = None
    speaker_name = self.config.unknown_label
    confidence = 0.0
    margin = 0.0
else:
    # Compute cluster embedding normally
    cluster_embedding = np.mean(cluster_embeddings, axis=0)
    
    # Do cluster-level identification
    for profile_name, profile in profiles.items():
        sim = enrollment.compute_similarity(cluster_embedding, profile)
        # ...
```

## Impact

✅ **Fixes the array shape error** when pyannote over-merges speakers
✅ **Preserves per-segment identification** for split clusters
✅ **No change to normal flow** when clusters are homogeneous
✅ **Better logging** to indicate when per-segment ID is used

## Testing

The fix handles these scenarios:

1. **Normal cluster** (single speaker, low variance)
   - Cluster-level identification works as before
   - No per-segment split needed

2. **High variance cluster** (multiple speakers merged)
   - Split marker added
   - Cluster-level identification skipped
   - Per-segment identification performed

3. **Single massive segment** (pyannote over-merge)
   - Detected and split into 30s chunks
   - Per-segment identification performed

## Related Files

- `backend/scripts/common/enhanced_asr.py` - Main fix
- Error occurred during ingestion with pyannote v4 + exclusive mode
- Related to voice embedding storage feature

## Summary

The fix ensures that when pyannote detects mixed speakers in a cluster, the system properly skips cluster-level embedding computation and proceeds directly to per-segment speaker identification, avoiding the numpy array shape error.
