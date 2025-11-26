#!/usr/bin/env bash
# =============================================================================
# Backend API Entrypoint
# =============================================================================
# This script runs Alembic migrations before starting the API server.
# 
# IMPORTANT: Only the API service should run this entrypoint.
# Ingestion/worker services must NOT run Alembic to avoid migration contention.
# =============================================================================

set -e

echo "📦 Running Alembic migrations..."
cd /app

# Run migrations - will use DATABASE_URL from environment
# The migrations/env.py reads DATABASE_URL and configures Alembic accordingly
alembic upgrade head

echo "✅ Migrations complete"

echo "🚀 Starting API server on port ${PORT:-8000}..."
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
