#!/bin/bash
# Bash script to execute BGE-Small migration
# Runs all 3 phases: add column, backfill, swap & index

set -e

echo "================================================================================"
echo "BGE-SMALL MIGRATION SCRIPT (Unix/Linux)"
echo "================================================================================"
echo ""

# Check if we're in the backend directory
if [ ! -f "alembic.ini" ]; then
    echo "ERROR: alembic.ini not found. Run this script from the backend/ directory."
    exit 1
fi

# Check if .env exists
if [ ! -f "../.env" ]; then
    echo "WARNING: .env file not found in parent directory"
    echo "Using .env.example as reference..."
fi

# Verify DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable not set"
    echo "Please set DATABASE_URL in your .env file or environment"
    exit 1
fi

echo "Step 1: Running Alembic migrations (005 -> 007)"
echo "This will:"
echo "  - Add embedding_384 column (Phase 1)"
echo "  - Backfill embeddings with BGE-Small (Phase 2)"
echo "  - Swap columns and rebuild index (Phase 3)"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled."
    exit 0
fi

echo ""
echo "Running: alembic upgrade head"
alembic upgrade head

echo ""
echo "================================================================================"
echo "MIGRATION COMPLETE!"
echo "================================================================================"
echo ""

echo "Step 2: Running embedding speed benchmark"
echo ""

read -p "Run benchmark? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Running: python scripts/test_embedding_speed.py"
    python scripts/test_embedding_speed.py || echo "WARNING: Benchmark failed or had errors"
fi

echo ""
echo "================================================================================"
echo "ALL DONE!"
echo "================================================================================"
echo ""
echo "Next steps:"
echo "  1. Update application code to use EmbeddingsService"
echo "  2. Test semantic search queries"
echo "  3. Monitor embedding generation performance"
echo ""
echo "To run tests:"
echo "  pytest tests/embeddings/ -v"
echo "  pytest tests/db/ -v"
echo "  pytest tests/migrations/ -v"
echo ""
