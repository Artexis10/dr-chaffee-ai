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

cd /app

echo "=============================================="
echo "� Dr. Chaffee AI Backend Startup"
echo "=============================================="
echo ""

# Verify DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL environment variable is not set!"
    echo "   Alembic migrations require DATABASE_URL to connect to PostgreSQL."
    echo "   Please set DATABASE_URL in your environment or docker-compose."
    exit 1
fi

echo "�📦 Running Alembic migrations (alembic upgrade head)..."
echo "   Database: ${DATABASE_URL%%@*}@****"  # Log URL without password

# Run migrations - will use DATABASE_URL from environment
# The migrations/env.py reads DATABASE_URL and configures Alembic accordingly
if alembic upgrade head; then
    echo "✅ Alembic migrations completed successfully"
else
    echo "❌ ERROR: Alembic migrations failed!"
    echo "   Check the database connection and migration files."
    exit 1
fi

echo ""
echo "🚀 Starting API server on port ${PORT:-8000}..."
echo "=============================================="
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
