# Optimized CPU-only Docker build for Dr. Chaffee AI
# Slim Python base image for Hetzner deployment
FROM python:3.11-slim

# Install system dependencies (CPU-only, no CUDA)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    git \
    postgresql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip for better wheel support
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /app

# Copy simplified requirements for faster installation
COPY backend/requirements-simple.txt .

# Install dependencies in stages to avoid resolver backtracking
# Stage 1: Core dependencies (fast, pre-built wheels)
RUN pip install --no-cache-dir \
    psycopg2-binary \
    alembic \
    sqlalchemy \
    python-dotenv \
    numpy \
    tqdm

# Stage 2: Web API (fast, pre-built wheels)
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    aiofiles \
    celery \
    redis

# Stage 3: YouTube dependencies (fast, pre-built wheels)
RUN pip install --no-cache-dir \
    youtube-transcript-api \
    yt-dlp \
    yt-dlp-ejs \
    google-api-python-client \
    google-auth-httplib2 \
    google-auth-oauthlib \
    pycryptodome \
    brotli \
    mutagen

# Stage 4: ML/AI with CPU-only PyTorch
RUN pip install --no-cache-dir \
    torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 && \
    pip install --no-cache-dir \
    sentence-transformers \
    transformers

# Stage 5: Audio transcription (critical packages)
RUN pip install --no-cache-dir \
    faster-whisper \
    ctranslate2 \
    pyannote.audio \
    speechbrain \
    soundfile

# Stage 6: Utilities
RUN pip install --no-cache-dir \
    psutil \
    webvtt-py \
    isodate \
    asyncio-throttle \
    apscheduler \
    aiohttp \
    aiohttp-socks \
    beautifulsoup4 \
    lxml

# Stage 7: Development/Testing (optional)
RUN pip install --no-cache-dir \
    black \
    ruff \
    pytest \
    pytest-cov \
    pytest-mock \
    pytest-asyncio \
    pytest-timeout \
    freezegun \
    hypothesis || true

# Copy application code
COPY backend/ .
# Note: .env is not baked into the image.
# Environment variables are provided at runtime by Coolify / the host.
# COPY .env .env

# Create directories for temporary files
RUN mkdir -p /tmp/whisper_cache /tmp/audio_downloads

# Set environment variables
ENV PYTHONPATH=/app
ENV WHISPER_CACHE_DIR=/tmp/whisper_cache
ENV TEMP_AUDIO_DIR=/tmp/audio_downloads
ENV YT_DLP_PATH=yt-dlp
ENV FFMPEG_PATH=ffmpeg

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import yt_dlp; print('OK')" || exit 1

# Run the FastAPI application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
