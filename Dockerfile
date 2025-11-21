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
# Use curl instead of requests to avoid import issues
HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command with SKIP_WARMUP to avoid embedding model download on startup
ENV SKIP_WARMUP=true
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
