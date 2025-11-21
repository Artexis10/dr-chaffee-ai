# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install only essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy production requirements only
COPY backend/requirements-prod.txt /tmp/requirements.txt

# Install Python dependencies with no cache
# Use CPU-only PyTorch to avoid massive CUDA downloads (~3.5GB)
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.1.2 && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Copy the entire backend
COPY backend /app/backend

# Expose port
EXPOSE 8000

# Set working directory for app
WORKDIR /app/backend

# Health check (extended timeouts for model loading on Railway)
# Use /live endpoint which has no dependencies
# start-period=120s gives 2 minutes for app to fully initialize
# timeout=5s is aggressive to catch real failures
# Uses PORT env var (Railway injects this dynamically)
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/live || exit 1

# Start command with SKIP_WARMUP to avoid embedding model download on startup
ENV SKIP_WARMUP=true

# Create startup script that runs migrations then starts the app
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Running database migrations..."\n\
python -m alembic upgrade head\n\
echo "Migrations complete. Starting application..."\n\
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}' > /app/backend/start.sh && \
    chmod +x /app/backend/start.sh

# Use Railway's PORT variable (defaults to 8000 for local dev)
CMD ["/app/backend/start.sh"]
