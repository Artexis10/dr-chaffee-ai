# Python 3.14 Compatibility Issue - Fix Guide

## Problem

You're using **Python 3.14.0**, which is too new. Most packages don't have pre-built wheels for Python 3.14 yet, causing compilation errors when pip tries to build from source.

## Solution

### Option 1: Use Python 3.11 (Recommended)

1. **Download Python 3.11** from https://www.python.org/downloads/
   - Choose "Windows installer (64-bit)"
   - During installation, **check "Add Python to PATH"**

2. **Create a virtual environment with Python 3.11:**
   ```powershell
   # Navigate to project
   cd c:\Users\hugoa\Desktop\dr-chaffee-ai\backend
   
   # Create virtual environment with Python 3.11
   py -3.11 -m venv venv
   
   # Activate it
   .\venv\Scripts\Activate.ps1
   
   # Verify Python version
   python --version  # Should show 3.11.x
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt --upgrade
   ```

### Option 2: Use Python 3.12

Same as above, but use `py -3.12` instead of `py -3.11`

### Option 3: Stick with Python 3.14 (Advanced)

If you must use Python 3.14, you need to install a C compiler:

1. **Install Visual Studio Build Tools:**
   - Download from: https://visualstudio.microsoft.com/downloads/
   - Select "Desktop development with C++"
   - Install

2. **Then try again:**
   ```powershell
   pip install -r requirements.txt --upgrade
   ```

---

## Recommended Setup (Option 1)

```powershell
# 1. Download and install Python 3.11 from python.org

# 2. Create virtual environment
cd c:\Users\hugoa\Desktop\dr-chaffee-ai\backend
py -3.11 -m venv venv

# 3. Activate
.\venv\Scripts\Activate.ps1

# 4. Upgrade pip
python -m pip install --upgrade pip

# 5. Install dependencies
pip install -r requirements.txt

# 6. Test
python -c "import torch; print(torch.__version__)"
```

---

## Why Python 3.11/3.12?

- ✅ Pre-built wheels available for all packages
- ✅ Stable and well-tested
- ✅ No compilation needed
- ✅ Faster installation
- ✅ Compatible with all dependencies

Python 3.14 is brand new and packages haven't built wheels for it yet.

---

## After Setup

Once you have Python 3.11/3.12 with dependencies installed:

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run tests
python -m pytest tests/

# Start backend
uvicorn api.main:app --reload

# Run ingestion
python scripts/ingest_youtube.py --source yt-dlp --limit 10
```

---

## Troubleshooting

### Still getting build errors?

1. **Clear pip cache:**
   ```powershell
   pip cache purge
   ```

2. **Try installing with no-binary:**
   ```powershell
   pip install -r requirements.txt --no-binary :all:
   ```

3. **Install one package at a time:**
   ```powershell
   pip install psycopg2-binary
   pip install alembic
   # ... etc
   ```

### Virtual environment not activating?

```powershell
# If you get execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try again:
.\venv\Scripts\Activate.ps1
```

---

## Verification

After setup, verify everything works:

```powershell
# Check Python version
python --version  # Should be 3.11.x or 3.12.x

# Check key packages
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "import fastapi; print('FastAPI: OK')"
python -c "import sqlalchemy; print('SQLAlchemy: OK')"

# Run a quick test
python -m pytest tests/ -v --tb=short
```

---

## Next Steps

1. Install Python 3.11 or 3.12
2. Create virtual environment
3. Install dependencies
4. Run tests to verify
5. Deploy to production (Docker uses Python 3.11)

**Estimated time: 10-15 minutes**
