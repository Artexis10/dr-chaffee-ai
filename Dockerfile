# Production CPU-only Docker build for Dr. Chaffee AI Backend API
# Optimized for Hetzner + Coolify deployment
# Excludes: GPU dependencies, ASR, diarization, ingestion pipeline
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

# Copy production requirements (CPU-only, no ASR/diarization)
COPY backend/requirements-production.txt .

# Install dependencies in stages to avoid resolver backtracking
# Stage 1: Core dependencies
RUN pip install --no-cache-dir \
    psycopg2-binary \
    alembic \
    sqlalchemy \
    python-dotenv \
    numpy \
    tqdm \
    isodate \
    psutil

# Stage 2: Web API
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    aiofiles

# Stage 3: CPU-only PyTorch + Embeddings (CRITICAL: CPU wheels only)
RUN pip install --no-cache-dir \
    torch==2.1.2 \
    torchvision==0.16.2 \
    torchaudio==2.1.2 \
    --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir \
    sentence-transformers \
    transformers \
    openai

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

# Health check - Query /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1

# Expose port 8000 (Coolify will map 80/443 -> 8000 via reverse proxy)
EXPOSE 8000

# Run the FastAPI application
# Coolify sets PORT env var, but we default to 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

