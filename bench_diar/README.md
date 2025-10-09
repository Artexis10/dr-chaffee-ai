# Diarization Benchmark Tool (Ingest Integration)

## Overview

This tool benchmarks different diarization approaches by:
1. Using your existing `ingest_youtube.py` to fetch transcript and audio
2. Running multiple diarization systems on the same audio
3. Aligning each diarization output to the transcript
4. Comparing results apples-to-apples

## Systems Tested

### Pyannote Community-1 (3 modes)
- **auto** - No speaker count constraints
- **bounded** - min_speakers=2, max_speakers=4
- **forced2** - num_speakers=2 (exact)

### SpeechBrain Baseline
- VAD: speechbrain/vad-crdnn-libriparty
- Embeddings: speechbrain/spkrec-ecapa-voxceleb
- Clustering: spectralcluster (auto-installed if missing)

## Quick Start

```powershell
# Run benchmark
.\bench_diar\run_bench.ps1

# Or with custom parameters
.\bench_diar\run_bench.ps1 -Source "https://www.youtube.com/watch?v=VIDEO_ID" -Seconds 120

# Or directly with Python
python bench_diar\bench_from_ingest.py --source "https://www.youtube.com/watch?v=1oKru2X3AvU" --seconds 120
```

## How It Works

### 1. Ingest Integration
- Calls `backend/scripts/ingest_youtube.py --from-url <URL> --force`
- Retrieves transcript segments from database
- Gets local audio path if available
- Falls back to yt-dlp if needed

### 2. Audio Preparation
- Ensures 16kHz mono WAV format
- Optional trimming to first N seconds for quick tests

### 3. Diarization
- Runs all systems on same audio
- Saves raw outputs as CSV files

### 4. Alignment
- Maps each diarization to transcript segments
- Calculates per-line speaker labels
- Computes confidence scores

### 5. Analysis
- Generates timeline visualizations (PNG)
- Creates comparison table
- Provides meaningful difference verdict

## Output Files

Each run creates a timestamped directory: `bench_diar/runs/YYYYMMDD_HHMMSS/`

### Raw Diarization
- `py_auto.csv` - Pyannote auto-K
- `py_bounded.csv` - Pyannote bounded (2-4)
- `py_forced2.csv` - Pyannote forced K=2
- `speechbrain_sc.csv` - SpeechBrain baseline

### Aligned Transcripts
- `transcript_py_auto.csv` - Transcript with auto-K labels
- `transcript_py_bounded.csv` - Transcript with bounded labels
- `transcript_py_forced2.csv` - Transcript with forced labels
- `transcript_speechbrain_sc.csv` - Transcript with SB labels

### Visualizations
- `timeline_py_auto.png`
- `timeline_py_bounded.png`
- `timeline_py_forced2.png`
- `timeline_speechbrain_sc.png`

### Summary
- `SUMMARY.md` - Comparison table and verdict

## Example Output

```markdown
# Diarization Benchmark (Aligned to Ingest Transcript)

**Video**: 1oKru2X3AvU
**Duration**: 120.00s
**Transcript segments**: 149

| Run | Speakers | Turns | AvgTurn(s) | FirstSplit(s) | Switches/min | %TopSpeaker |
|---|---|---|---|---|---|---|
| py_auto | 2 | 22 | 4.29 | 20.35 | 3.04 | 76.6% |
| py_bounded | 2 | 22 | 4.29 | 20.35 | 3.04 | 76.6% |
| py_forced2 | 2 | 22 | 4.29 | 20.35 | 3.04 | 76.6% |
| speechbrain_sc | 2 | 18 | 5.12 | 17.80 | 2.50 | 78.2% |

**Meaningful difference?** YES - SpeechBrain detects earlier split
```

## Requirements

All dependencies are already in your environment:
- pyannote.audio
- speechbrain
- torch (with CUDA)
- pandas
- matplotlib
- soundfile
- yt-dlp

Optional (auto-installed if missing):
- spectralcluster (for SpeechBrain clustering)

## Notes

- **No changes to requirements.txt** - Uses existing environment
- **Graceful degradation** - If a system fails, others continue
- **CUDA auto-detected** - Uses GPU if available
- **Integrates with your pipeline** - Reuses ingest_youtube.py

## Troubleshooting

### "ingest_youtube.py not found"
Update `bench_from_ingest.py` line 40 with correct path

### "ffmpeg not found"
Install via Scoop or Chocolatey:
```powershell
scoop install ffmpeg
# or
choco install ffmpeg -y
```

### "Database connection failed"
Ensure `.env` has `DATABASE_URL` set

### "SpeechBrain failed"
This is expected if models can't download - pyannote results still work

## Advanced Usage

### Full video (no trimming)
```powershell
python bench_diar\bench_from_ingest.py --source "URL" --seconds 0
```

### Local video file
```powershell
# First ingest locally
python backend\scripts\ingest_youtube.py --source local --from-files "path\to\video.mp4"

# Then benchmark (will use stored audio)
python bench_diar\bench_from_ingest.py --source "VIDEO_ID" --seconds 0
```

## Comparison with diar_bench

This tool (`bench_diar`) differs from the earlier `diar_bench`:
- **Integrates with ingest pipeline** - Uses your existing transcript
- **Aligns to transcript** - Shows per-line speaker labels
- **Database-aware** - Pulls from your PostgreSQL database
- **Production-ready** - Uses same code path as production ingestion

The `diar_bench` tool is standalone and doesn't require database/ingest setup.
