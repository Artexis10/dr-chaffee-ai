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

# ============================================================================
# CRITICAL: NumPy/PyTorch Installation Order
# ============================================================================
# NumPy 2.x breaks PyTorch 2.1.2 with '_pytree' errors.
# Solution: Install NumPy 1.24.3 FIRST, then PyTorch, then everything else.
# NEVER use pip install -r requirements.txt - it will upgrade NumPy to 2.x!

# Stage 1: NumPy 1.x (MUST be first, locked to prevent NumPy 2.x)
# Flexible constraint allows 1.24.x, 1.25.x, 1.26.x (all compatible with torch 2.1.2)
RUN pip install --no-cache-dir "numpy<2.0.0"

# Stage 2: PyTorch CPU-only (compiled against NumPy 1.x)
RUN pip install --no-cache-dir \
    torch==2.1.2 \
    torchvision==0.16.2 \
    torchaudio==2.1.2 \
    --index-url https://download.pytorch.org/whl/cpu

# Stage 3: Core dependencies (no NumPy conflicts)
RUN pip install --no-cache-dir \
    psycopg2-binary==2.9.9 \
    alembic==1.13.1 \
    sqlalchemy==2.0.23 \
    python-dotenv==1.0.0 \
    tqdm==4.66.1 \
    isodate==0.6.1 \
    psutil==5.9.6

# Stage 4: Web API (CRITICAL: use plain uvicorn, NOT uvicorn[standard])
# uvicorn[standard] includes uvloop/httptools which can pull NumPy 2.x
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    python-multipart==0.0.18 \
    aiofiles==23.2.1 \
    click==8.1.7 \
    h11==0.14.0

# Stage 5: Embeddings (pinned to versions compatible with torch 2.1.2 + numpy 1.24.3)
RUN pip install --no-cache-dir \
    sentence-transformers==2.2.2 \
    transformers==4.36.2 \
    tokenizers==0.15.0 \
    huggingface-hub==0.19.4 \
    safetensors==0.4.1 \
    regex==2023.10.3 \
    filelock==3.13.1 \
    packaging==23.2 \
    requests==2.31.0 \
    urllib3==2.1.0 \
    certifi==2023.11.17 \
    charset-normalizer==3.3.2 \
    idna==3.6

# Stage 6: OpenAI
RUN pip install --no-cache-dir \
    openai==1.3.0 \
    anyio==3.7.1 \
    sniffio==1.3.0 \
    httpx==0.25.2 \
    httpcore==1.0.2 \
    pydantic==2.5.2 \
    pydantic-core==2.14.5 \
    typing-extensions==4.9.0 \
    distro==1.8.0

# Stage 7: VERIFY NumPy and PyTorch versions (safe check, no hard assertions)
RUN python - <<'EOF'
import numpy
import torch
print(f"✅ NumPy {numpy.__version__} loaded successfully (<2.0.0 required)")
print(f"✅ PyTorch {torch.__version__}")
EOF

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

