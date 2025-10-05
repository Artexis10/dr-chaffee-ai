# Deployment Dependencies Guide

Automated dependency management for production deployments.

## The Problem

Missing dependencies cause runtime failures:
- `No module named 'faster_whisper'` → Can't transcribe
- `No module named 'torch'` → Can't run models
- `No module named 'yt_dlp'` → Can't download videos

## The Solution

**Automatic dependency checking and installation** before ingestion starts.

## How It Works

### Automatic (Default)

```bash
# Just run - dependencies auto-install if missing
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 100
```

**What happens:**
1. ✅ Checks all critical dependencies
2. ✅ Auto-installs missing ones
3. ✅ Warns about optional dependencies
4. ✅ Checks GPU availability
5. ✅ Continues with ingestion

### Manual Check

```bash
# Check dependencies without running ingestion
python backend/scripts/common/dependency_checker.py
```

### Check Only (No Install)

```bash
# Just check, don't auto-install
python backend/scripts/common/dependency_checker.py --no-auto-install
```

## Critical Dependencies

These are **required** and will auto-install:

| Package | Version | Purpose |
|---------|---------|---------|
| `faster-whisper` | ≥1.0.2 | Audio transcription |
| `torch` | ≥2.1.0,<2.4.0 | ML models |
| `yt-dlp` | ≥2023.11.16 | YouTube downloads |
| `psycopg2-binary` | ≥2.9.9 | Database |
| `transformers` | 4.33.2 | Embeddings |

## Optional Dependencies

These are **optional** (warns but doesn't fail):

| Package | Version | Purpose |
|---------|---------|---------|
| `whisperx` | ≥3.1.1 | Advanced ASR |
| `pyannote.audio` | ≥3.1.1 | Speaker diarization |
| `librosa` | ≥0.10.1 | Audio processing |

## Production Deployment

### Option 1: Dockerfile (Recommended)

```dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt /app/backend/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application
COPY . /app
WORKDIR /app

# Run ingestion
CMD ["python", "backend/scripts/ingest_youtube.py", "--source", "yt-dlp"]
```

### Option 2: Railway/Render

**railway.json:**
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "pip install -r backend/requirements.txt && python backend/scripts/ingest_youtube.py --source yt-dlp --limit 100",
    "healthcheckPath": "/health"
  }
}
```

### Option 3: Manual Deployment

```bash
# 1. Clone repo
git clone https://github.com/your-repo/ask-dr-chaffee.git
cd ask-dr-chaffee

# 2. Create venv
python -m venv backend/venv
source backend/venv/bin/activate  # Linux/Mac
# or
.\backend\venv\Scripts\Activate.ps1  # Windows

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Run ingestion (auto-checks dependencies)
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 100
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Run Ingestion

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
      
      - name: Run ingestion
        run: |
          python backend/scripts/ingest_youtube.py \
            --source yt-dlp \
            --limit 100 \
            --limit-unprocessed
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          HUGGINGFACE_TOKEN: ${{ secrets.HUGGINGFACE_TOKEN }}
```

## Troubleshooting

### Dependency Check Fails

```bash
# Check what's missing
python backend/scripts/common/dependency_checker.py --no-auto-install

# Install manually
pip install -r backend/requirements.txt
```

### Auto-Install Fails

```bash
# Install manually with verbose output
pip install -v faster-whisper torch yt-dlp psycopg2-binary transformers
```

### GPU Not Detected

```bash
# Check CUDA installation
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# Install CUDA-enabled PyTorch
pip install torch==2.1.0+cu118 --index-url https://download.pytorch.org/whl/cu118
```

## Example Output

### Successful Check

```
2025-10-05 04:59:00 - INFO - Checking dependencies...
2025-10-05 04:59:00 - INFO - Checking critical dependencies...
2025-10-05 04:59:01 - INFO - ✅ All critical dependencies available
2025-10-05 04:59:01 - INFO - Checking optional dependencies...
2025-10-05 04:59:02 - INFO - ⚠️  Optional dependency not installed: librosa>=0.10.1
2025-10-05 04:59:02 - INFO - ✅ GPU available: NVIDIA GeForce RTX 5080
2025-10-05 04:59:02 - INFO - Starting ingestion...
```

### Missing Dependencies (Auto-Fix)

```
2025-10-05 04:59:00 - INFO - Checking dependencies...
2025-10-05 04:59:00 - WARNING - ❌ Missing critical dependency: faster-whisper>=1.0.2
2025-10-05 04:59:00 - WARNING - ⚠️  Found 1 missing critical dependencies
2025-10-05 04:59:00 - INFO - Attempting automatic installation...
2025-10-05 04:59:00 - INFO - Installing faster-whisper>=1.0.2...
2025-10-05 04:59:15 - INFO - ✅ Successfully installed faster-whisper>=1.0.2
2025-10-05 04:59:15 - INFO - ✅ All critical dependencies installed successfully
2025-10-05 04:59:15 - INFO - Starting ingestion...
```

## Environment Variables

For production, set these in your deployment platform:

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/db

# Optional (for advanced features)
HUGGINGFACE_TOKEN=your_token
OPENAI_API_KEY=your_key
YOUTUBE_API_KEY=your_key
```

## Best Practices

### 1. Use requirements.txt

Always install from requirements.txt:
```bash
pip install -r backend/requirements.txt
```

### 2. Pin Versions

requirements.txt has pinned versions for reproducibility:
```
faster-whisper>=1.0.2
torch>=2.1.0,<2.4.0
```

### 3. Use Virtual Environments

```bash
python -m venv backend/venv
source backend/venv/bin/activate
```

### 4. Cache Dependencies

In Docker:
```dockerfile
# Cache pip packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

### 5. Health Checks

```python
# Check dependencies before starting service
if not check_and_install_dependencies():
    sys.exit(1)
```

## Summary

**Automatic dependency management:**
- ✅ Checks dependencies on every run
- ✅ Auto-installs missing critical packages
- ✅ Warns about optional packages
- ✅ Checks GPU availability
- ✅ Works in development and production

**Just run:**
```bash
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 100
```

**Dependencies auto-install if missing!** 🎯
