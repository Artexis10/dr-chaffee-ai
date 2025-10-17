#!/bin/bash
# Run Alembic migrations on production database
# This applies all pending migrations in order

set -e

cd "$(dirname "$0")"

echo "🗄️  Running Alembic migrations..."
echo ""

# Activate virtual environment if it exists and has activate script
if [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if alembic is available
if ! command -v alembic &> /dev/null; then
    echo "⚠️  Alembic not found. Installing..."
    pip3 install alembic psycopg2-binary python-dotenv
    echo ""
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL not set"
    echo ""
    echo "Usage:"
    echo "  DATABASE_URL='postgresql://user:pass@host/db' ./run_migrations.sh"
    echo ""
    echo "Or export it first:"
    echo "  export DATABASE_URL='postgresql://user:pass@host/db'"
    echo "  ./run_migrations.sh"
    exit 1
fi

# Show current migration status
echo "Current migration status:"
alembic current
echo ""

# Show pending migrations
echo "Pending migrations:"
alembic history --verbose | head -20
echo ""

# Run migrations
echo "Applying migrations..."
alembic upgrade head

echo ""
echo "✅ Migrations complete!"
echo ""
echo "Verify with:"
echo "  alembic current"
echo "  psql \"\$DATABASE_URL\" -c \"\\d answer_cache\""
echo ""
