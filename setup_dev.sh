#!/bin/bash
# Quick development environment setup script
# Run with: bash setup_dev.sh

set -e

echo "=========================================="
echo "Dr. Chaffee AI - Dev Environment Setup"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "backend/requirements.txt" ]; then
    echo "❌ Error: Run this from the project root directory"
    echo "   cd ~/Desktop/personal/dr-chaffee-ai"
    exit 1
fi

# Step 1: System dependencies
echo "📦 Step 1: Installing system dependencies..."
echo "   (You'll need to enter your sudo password)"
echo ""
sudo apt-get update -qq
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    postgresql-client \
    build-essential \
    libpq-dev
echo "✓ System dependencies installed"
echo ""

# Step 2: Create virtual environment
echo "🐍 Step 2: Creating virtual environment..."
cd backend
if [ -d ".venv" ]; then
    echo "   Virtual environment already exists, skipping..."
else
    python3 -m venv .venv
    echo "✓ Virtual environment created"
fi
echo ""

# Step 3: Install Python packages
echo "📚 Step 3: Installing Python packages..."
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt
pip install pytest pytest-asyncio
echo "✓ Python packages installed"
echo ""

# Step 4: Setup .env file
echo "⚙️  Step 4: Setting up .env file..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ .env file created"
    echo "   ⚠️  Please edit backend/.env and add your DATABASE_URL"
else
    echo "✓ .env file already exists"
fi
echo ""

# Step 5: Test database connection
echo "🔌 Step 5: Testing database connection..."
DB_URL="postgresql://drchaffee_db_user:R3shsw9dirMQQcnO8hFqO9L0MU8OSV4t@dpg-d3o0evc9c44c73cep47g-a.frankfurt-postgres.render.com/drchaffee_db"
if psql "$DB_URL" -c "SELECT 1" > /dev/null 2>&1; then
    echo "✓ Database connection successful"
    
    # Show database stats
    echo ""
    echo "📊 Database Stats:"
    psql "$DB_URL" -c "SELECT 
        (SELECT COUNT(*) FROM segments) as total_segments,
        (SELECT COUNT(*) FROM segment_embeddings) as total_embeddings,
        (SELECT model_key FROM segment_embeddings LIMIT 1) as model;" -t
else
    echo "⚠️  Database connection failed"
fi
echo ""

# Step 6: Run tests
echo "🧪 Step 6: Running tests..."
cd ..
if python3 tests/api/test_detection_logic.py; then
    echo "✓ All tests passed!"
else
    echo "⚠️  Some tests failed (this is okay for now)"
fi
echo ""

echo "=========================================="
echo "✓✓✓ Setup Complete! ✓✓✓"
echo "=========================================="
echo ""
echo "📝 Next steps:"
echo ""
echo "1. Activate the environment:"
echo "   cd backend && source .venv/bin/activate"
echo ""
echo "2. Run tests:"
echo "   python3 tests/api/test_detection_logic.py"
echo ""
echo "3. Start API locally:"
echo "   cd backend && uvicorn api.main:app --reload --port 8000"
echo ""
echo "4. Manual deploy on Render:"
echo "   https://dashboard.render.com → drchaffee-backend → Manual Deploy"
echo ""
echo "📖 Full guide: See SETUP_DEV_ENV.md"
echo ""
