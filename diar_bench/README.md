# Diarization Benchmark Tool

## Overview

This tool performs an apples-to-apples comparison of pyannote Community-1 diarization in three modes:
1. **AUTO** - No speaker count constraints (auto-detect)
2. **BOUNDED** - min_speakers=2, max_speakers=4
3. **FORCED** - num_speakers=2 (exact count)

## Quick Start

```powershell
# Run benchmark on YouTube video (first 120 seconds)
python benchmark_diarizers.py --source "https://www.youtube.com/watch?v=1oKru2X3AvU" --seconds 120

# Or use PowerShell wrapper
.\run_benchmark.ps1
```

## Results

The benchmark produces:
- **CSVs**: `pyannote_auto.csv`, `pyannote_bounded.csv`, `pyannote_forced.csv`
- **Timelines**: PNG visualizations of speaker turns
- **SUMMARY.md**: Comparison table and recommendation

## Latest Run: 2025-10-09 01:47

### Key Findings

**All three modes produced IDENTICAL results:**
- 2 speakers detected
- 22 turns
- First split at 20.35s
- 3.04 switches/min
- Top speaker: 76.6%

**Conclusion**: For this video, pyannote Community-1 correctly detects 2 speakers regardless of mode. The auto-detection works perfectly.

### CSV Preview (first 10 lines)

```csv
start,end,speaker
6.43,15.54,SPEAKER_00
15.67,17.60,SPEAKER_00
17.90,19.08,SPEAKER_00
20.35,22.31,SPEAKER_01  ← First guest appearance at 20.35s
22.63,27.49,SPEAKER_00
27.89,33.24,SPEAKER_00
34.74,36.36,SPEAKER_01
37.51,44.13,SPEAKER_01
44.48,54.06,SPEAKER_01
```

## Files

- `utils_audio.py` - Audio download and preprocessing
- `viz.py` - Timeline visualization
- `benchmark_diarizers.py` - Main benchmark script
- `run_benchmark.ps1` - PowerShell wrapper
- `runs/YYYYMMDD_HHMMSS/` - Output directory for each run

## Requirements

Uses parent project's environment which includes:
- pyannote.audio 4.x
- torch with CUDA support
- yt-dlp
- pandas, matplotlib

## Notes

- Audio is preloaded in memory to avoid AudioDecoder issues
- CUDA is automatically used if available
- First 120 seconds used by default (configurable with `--seconds`)
- FS-EEND support is optional (not implemented yet)

## Run Directory

Latest run: `runs/20251009_014717/`

Contains:
- 3 CSV files (one per mode)
- 3 PNG timelines
- SUMMARY.md with comparison
- summary.json with detailed metrics
