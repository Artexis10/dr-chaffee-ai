#!/bin/bash
# Run Alembic migrations on production database
# This applies all pending migrations in order

set -e

cd "$(dirname "$0")"

echo "🗄️  Running Alembic migrations..."
echo ""

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
