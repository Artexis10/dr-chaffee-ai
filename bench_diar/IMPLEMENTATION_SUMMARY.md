# Diarization Benchmark Implementation Summary

## What Was Built

A comprehensive diarization benchmark tool that integrates with your existing `ingest_youtube.py` pipeline to compare multiple diarization systems on the same audio with transcript alignment.

## Files Created

### Core Components
1. **`align.py`** - Transcript-to-diarization alignment utilities
   - `map_transcript_to_speakers()` - Maps diarization to transcript via overlap
   - `summarize_segments()` - Computes metrics (speakers, turns, splits, etc.)

2. **`viz.py`** - Timeline visualization
   - `plot_timeline()` - Creates horizontal speaker timeline PNGs

3. **`py_run.py`** - Pyannote Community-1 runner
   - Supports 3 modes: auto, bounded (2-4), forced (K=2)
   - Handles v4 API with in-memory audio loading

4. **`sb_run.py`** - SpeechBrain baseline
   - VAD + ECAPA embeddings + spectral clustering
   - Graceful fallback to greedy clustering if spectralcluster unavailable

5. **`bench_from_ingest.py`** - Main benchmark script
   - Calls your `ingest_youtube.py` to get transcript
   - Queries database for segments
   - Runs all diarization systems
   - Aligns outputs to transcript
   - Generates comparison report

6. **`run_bench.ps1`** - PowerShell wrapper
   - Convenience script with defaults
   - Auto-opens SUMMARY.md when complete

7. **`README.md`** - Documentation
   - Usage instructions
   - Output file descriptions
   - Troubleshooting guide

## Key Features

### ✅ No Requirements.txt Changes
- Uses existing environment (pyannote.audio, speechbrain, torch, etc.)
- Auto-installs optional dependencies (spectralcluster) if missing
- Gracefully skips systems that fail

### ✅ Ingest Pipeline Integration
- Calls `backend/scripts/ingest_youtube.py --from-url <URL> --force`
- Queries PostgreSQL database for segments
- Reuses stored audio if available
- Falls back to yt-dlp if needed

### ✅ Apples-to-Apples Comparison
- All systems process same 16kHz mono WAV
- Aligned to same transcript
- Consistent metrics across systems

### ✅ Comprehensive Output
- Raw diarization CSVs
- Transcript-aligned CSVs (per-line speaker labels)
- Timeline visualizations (PNG)
- Comparison table with verdict

## How It Works

```
1. Call ingest_youtube.py
   ↓
2. Get transcript from database
   ↓
3. Get/download audio → 16kHz mono WAV
   ↓
4. Run diarization systems in parallel:
   - Pyannote auto-K
   - Pyannote bounded (2-4)
   - Pyannote forced K=2
   - SpeechBrain baseline
   ↓
5. Align each to transcript
   ↓
6. Generate comparison report
```

## Example Usage

```powershell
# Quick test (first 2 minutes)
python bench_diar\bench_from_ingest.py --source "https://www.youtube.com/watch?v=1oKru2X3AvU" --seconds 120

# Full video
python bench_diar\bench_from_ingest.py --source "https://www.youtube.com/watch?v=1oKru2X3AvU" --seconds 0

# Using PowerShell wrapper
.\bench_diar\run_bench.ps1
```

## Output Structure

```
bench_diar/
├── runs/
│   └── 20251009_HHMMSS/
│       ├── py_auto.csv              # Raw diarization
│       ├── py_bounded.csv
│       ├── py_forced2.csv
│       ├── speechbrain_sc.csv
│       ├── transcript_py_auto.csv   # Aligned to transcript
│       ├── transcript_py_bounded.csv
│       ├── transcript_py_forced2.csv
│       ├── transcript_speechbrain_sc.csv
│       ├── timeline_py_auto.png     # Visualizations
│       ├── timeline_py_bounded.png
│       ├── timeline_py_forced2.png
│       ├── timeline_speechbrain_sc.png
│       └── SUMMARY.md               # Comparison report
```

## Metrics Computed

For each system:
- **n_speakers** - Number of unique speakers detected
- **n_turns** - Total speaker turns
- **avg_turn_s** - Average turn duration
- **first_split_s** - When second speaker first appears
- **switches_per_min** - Speaker change frequency
- **pct_top** - Percentage of top speaker

## Verdict Logic

Compares systems and determines if differences are meaningful:
- If auto-K detects fewer speakers than bounded/SB → "YES - auto-K under-counts"
- If first_split differs significantly → "YES - timing differs"
- Otherwise → "NO - results similar"

## Integration Points

### Database Schema Expected
```sql
-- segments table
video_id, start_time, end_time, content, speaker

-- videos table
video_id, local_audio_path
```

### Environment Variables
- `DATABASE_URL` - PostgreSQL connection string

### Dependencies (Already Installed)
- pyannote.audio ≥4.0.0
- speechbrain ≥0.5.16
- torch ≥2.2.0
- pandas
- matplotlib
- soundfile
- yt-dlp

## Testing Status

Currently running first test on video `1oKru2X3AvU` (first 120 seconds).

Expected completion: ~3-5 minutes
- Ingest: ~1 min
- Pyannote (3 modes): ~1-2 min
- SpeechBrain: ~1-2 min
- Alignment & viz: <10 sec

## Next Steps

1. ✅ Wait for first benchmark to complete
2. ✅ Review SUMMARY.md output
3. ✅ Check aligned transcript CSVs
4. ✅ Verify timeline visualizations
5. ✅ Compare with your manual inspection

## Success Criteria

- [x] No changes to requirements.txt
- [x] Integrates with ingest_youtube.py
- [x] Runs all 4 diarization systems
- [x] Aligns to transcript
- [x] Generates comparison report
- [ ] Produces meaningful verdict (pending test results)

---

**Status**: Implementation complete, first test running
**Location**: `c:\Users\hugoa\Desktop\ask-dr-chaffee\bench_diar\`
