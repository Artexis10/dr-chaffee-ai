# Development Environment Setup Guide

## System Requirements
- Ubuntu 24.04 LTS
- Python 3.12
- PostgreSQL client
- Git

## Step 1: Install System Dependencies

Run these commands (you'll need to enter your sudo password):

```bash
# Update package list
sudo apt-get update

# Install required system packages
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    postgresql-client \
    build-essential \
    git \
    curl \
    wget
```

## Step 2: Create Python Virtual Environment

```bash
cd ~/Desktop/personal/dr-chaffee-ai/backend
python3 -m venv .venv
```

## Step 3: Activate Virtual Environment

```bash
source .venv/bin/activate
```

You should see `(.venv)` in your terminal prompt.

## Step 4: Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

# Install testing tools
pip install pytest pytest-asyncio
```

## Step 5: Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env file with your settings
nano .env
```

Add the production database URL:
```
DATABASE_URL=postgresql://drchaffee_db_user:R3shsw9dirMQQcnO8hFqO9L0MU8OSV4t@dpg-d3o0evc9c44c73cep47g-a.frankfurt-postgres.render.com/drchaffee_db
```

## Step 6: Test Database Connection

```bash
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM segments;"
```

## Step 7: Run Tests

```bash
# From backend directory
cd ~/Desktop/personal/dr-chaffee-ai

# Run the detection logic tests
python3 tests/api/test_detection_logic.py
```

## Step 8: Start API Locally (Optional)

```bash
cd backend
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

Then visit: http://localhost:8000/docs

## Quick Reference

### Activate environment:
```bash
cd ~/Desktop/personal/dr-chaffee-ai/backend
source .venv/bin/activate
```

### Deactivate environment:
```bash
deactivate
```

### Run tests:
```bash
python3 tests/api/test_detection_logic.py
```

### Check production database:
```bash
psql "$DATABASE_URL" -c "SELECT model_key, dimensions, COUNT(*) FROM segment_embeddings GROUP BY model_key, dimensions;"
```

## Troubleshooting

### "python3-venv not available"
```bash
sudo apt install python3.12-venv
```

### "psycopg2 installation failed"
```bash
sudo apt-get install libpq-dev python3-dev
pip install psycopg2-binary
```

### "Permission denied" errors
Make sure you're in the virtual environment:
```bash
source backend/.venv/bin/activate
```

### Import errors
Make sure you're running from the correct directory:
```bash
cd ~/Desktop/personal/dr-chaffee-ai
python3 -c "import sys; sys.path.insert(0, 'backend'); from api.main import app; print('✓ Imports work')"
```

## Next Steps

Once setup is complete:

1. ✅ Run tests to verify everything works
2. ✅ Make code changes
3. ✅ Test locally before pushing
4. ✅ Commit and push to GitHub
5. ✅ Manual deploy on Render (until pipeline minutes reset)

## Manual Deploy on Render

Since you're out of pipeline minutes:

1. Go to: https://dashboard.render.com
2. Select: `drchaffee-backend` service
3. Click: **"Manual Deploy"** button
4. Select branch: `main`
5. Click: **"Deploy"**

This bypasses the pipeline and deploys immediately.
