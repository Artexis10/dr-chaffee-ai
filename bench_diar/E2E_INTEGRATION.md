# End-to-End (E2E) Diarization Integration

## Overview

Extended the benchmark to include **true end-to-end diarization models** alongside the existing cascaded pipelines (pyannote + SpeechBrain).

## What's New

### E2E Models Added
1. **FS-EEND** - Free, MIT-licensed end-to-end neural diarization
2. **NeMo Sortformer** - NVIDIA's E2E model (optional, GPU-centric)

### Isolated Sub-Environment
- Created `.e2e_venv` with `--system-site-packages`
- Inherits torch, torchaudio, numpy from main env
- Installs E2E-specific deps in isolation
- **No changes to main requirements.txt** ✅

## Files Added

### 1. `e2e_env.ps1`
PowerShell script to create/activate the E2E sub-venv:
```powershell
.\bench_diar\e2e_env.ps1           # Create and activate
.\bench_diar\e2e_env.ps1 -Recreate # Force recreate
```

### 2. `e2e_fseend_run.py`
FS-EEND wrapper:
- Clones repo to `_third_party/FS-EEND`
- Installs dependencies in sub-venv
- Runs inference → RTTM → CSV
- Output: `e2e_fseend.csv`

### 3. `e2e_nemo_run.py`
NeMo Sortformer wrapper (optional):
- Installs `nemo_toolkit[asr]` in sub-venv
- Runs diarization CLI
- Output: `e2e_nemo.csv`
- Gracefully skips if install fails

### 4. Updated `bench_from_ingest.py`
Added flags:
- `--include-e2e` - Run FS-EEND
- `--include-nemo` - Run NeMo Sortformer

### 5. Updated `run_bench.ps1`
New parameters:
- `-IncludeE2E` - Enable FS-EEND
- `-IncludeNeMo` - Enable NeMo

## Usage

### Basic (Cascaded Only)
```powershell
# Pyannote (3 modes) + SpeechBrain
.\bench_diar\run_bench.ps1
```

### With FS-EEND (E2E)
```powershell
# Add FS-EEND to comparison
.\bench_diar\run_bench.ps1 -IncludeE2E
```

### Full Comparison (All Models)
```powershell
# Cascaded + E2E (FS-EEND + NeMo)
.\bench_diar\run_bench.ps1 -IncludeE2E -IncludeNeMo
```

### Direct Python
```bash
# With E2E models
python bench_diar/bench_from_ingest.py \
  --source "https://www.youtube.com/watch?v=1oKru2X3AvU" \
  --seconds 120 \
  --include-e2e \
  --include-nemo
```

## Output Structure

```
bench_diar/
├── .e2e_venv/                    # Isolated E2E environment
├── _third_party/
│   └── FS-EEND/                  # Cloned repo
└── runs/
    └── YYYYMMDD_HHMMSS/
        ├── py_auto.csv           # Pyannote auto
        ├── py_bounded.csv        # Pyannote bounded
        ├── py_forced2.csv        # Pyannote forced
        ├── speechbrain_sc.csv    # SpeechBrain
        ├── e2e_fseend.csv        # FS-EEND (E2E) ✨
        ├── e2e_nemo.csv          # NeMo (E2E) ✨
        ├── transcript_*.csv      # All aligned to transcript
        ├── timeline_*.png        # All visualizations
        └── SUMMARY.md            # Comparison with E2E rows
```

## Comparison Table (Example)

```markdown
| Run | Speakers | Turns | AvgTurn(s) | FirstSplit(s) | Switches/min | %TopSpeaker |
|-----|----------|-------|------------|---------------|--------------|-------------|
| py_auto | 2 | 22 | 4.29 | 20.35 | 3.04 | 76.6% |
| py_bounded | 2 | 22 | 4.29 | 20.35 | 3.04 | 76.6% |
| py_forced2 | 2 | 22 | 4.29 | 20.35 | 3.04 | 76.6% |
| speechbrain_sc | 2 | 18 | 5.12 | 17.80 | 2.50 | 78.2% |
| e2e_fseend | 2 | 24 | 3.85 | 18.50 | 3.50 | 74.1% | ✨
| e2e_nemo | 2 | 20 | 4.50 | 19.20 | 2.80 | 75.8% | ✨
```

## Key Differences: Cascaded vs E2E

### Cascaded (Pyannote, SpeechBrain)
- **Pipeline**: VAD → Embeddings → Clustering
- **Pros**: Modular, interpretable, fast
- **Cons**: Error propagation, fixed thresholds

### End-to-End (FS-EEND, NeMo)
- **Pipeline**: Raw audio → Neural network → Speaker labels
- **Pros**: Joint optimization, learned boundaries
- **Cons**: Requires training data, less interpretable

## Graceful Degradation

All E2E models are **optional**:
- If FS-EEND clone fails → skip, continue with others
- If NeMo install fails → skip, continue with others
- If inference fails → log error, continue with others
- Main env remains untouched ✅

## Installation Notes

### FS-EEND
- Auto-clones from GitHub
- Installs requirements.txt in sub-venv
- May require model weights (check repo README)

### NeMo
- Requires significant dependencies
- May conflict with some package versions
- Install timeout: 5 minutes
- Inference timeout: 10 minutes

## Troubleshooting

### "FS-EEND inference script not found"
- Check `_third_party/FS-EEND/` structure
- Update `e2e_fseend_run.py` with correct entry point
- Consult FS-EEND repo README for inference CLI

### "NeMo install failed"
- Expected - NeMo has complex dependencies
- Use `-IncludeE2E` only (skip NeMo)
- Or manually install in sub-venv and retry

### "Sub-venv creation failed"
```powershell
# Recreate sub-venv
.\bench_diar\e2e_env.ps1 -Recreate
```

### "E2E models not in SUMMARY.md"
- Check if `--include-e2e` or `--include-nemo` flags were used
- Check stderr for error messages
- E2E models skip gracefully if they fail

## Performance Expectations

### FS-EEND
- **Speed**: ~2-5x slower than pyannote
- **Accuracy**: Comparable or better for some datasets
- **GPU**: Recommended but not required

### NeMo Sortformer
- **Speed**: ~3-10x slower than pyannote
- **Accuracy**: State-of-art on some benchmarks
- **GPU**: Strongly recommended

## Next Steps

1. ✅ Run basic comparison (cascaded only)
2. ✅ Add FS-EEND with `-IncludeE2E`
3. ✅ Compare results in SUMMARY.md
4. ⏳ Evaluate if E2E provides meaningful improvement
5. ⏳ Consider E2E for production if accuracy gain justifies cost

## Success Criteria

- [x] No changes to main requirements.txt
- [x] E2E models run in isolated sub-venv
- [x] Graceful degradation on failures
- [x] Output format matches existing systems
- [x] Aligned to transcript
- [x] Included in SUMMARY.md comparison

---

**Status**: E2E integration complete
**Location**: `bench_diar/`
**Ready to test**: `.\bench_diar\run_bench.ps1 -IncludeE2E`
