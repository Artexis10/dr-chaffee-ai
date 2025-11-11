# Troubleshooting Guide

Common issues and solutions for Dr. Chaffee AI setup.

## Setup Issues

### "Python not found"

**Solution:**
```powershell
winget install Python.Python.3.12
```

Restart PowerShell after installation.

---

### "Node not found"

**Solution:**
```powershell
winget install OpenJS.NodeJS
```

Restart PowerShell after installation.

---

### "Docker not running"

**Symptoms:**
- Error: "cannot connect to Docker daemon"
- Error: "pipe/dockerDesktopLinuxEngine not found"

**Solution:**
1. Start Docker Desktop manually
2. Wait for it to fully start (whale icon in system tray)
3. Run: `docker-compose up -d`

---

### Numpy compilation errors

**Symptoms:**
- Error: "Unknown compiler(s): [['cl'], ['gcc']...]"
- Error: "Microsoft Visual Studio not found"

**Solution:**
The setup script uses a simplified requirements file that avoids compilation. If you still see this:

```powershell
backend\venv\Scripts\python.exe -m pip install numpy --only-binary=numpy
```

---

### "Permission denied" errors

**Solution:**
Run PowerShell as Administrator:
```powershell
powershell -ExecutionPolicy Bypass -File setup-windows.ps1
```

---

## Runtime Issues

### Database connection errors

**Symptoms:**
- "could not connect to server"
- "connection refused"

**Solution:**
```powershell
# Check if Docker is running
docker ps

# If not, start it
docker-compose up -d

# Wait 10 seconds for database to be ready
Start-Sleep -Seconds 10
```

---

### Frontend won't start

**Symptoms:**
- Port 3000 already in use
- Module not found errors

**Solution:**
```powershell
# Kill any process on port 3000
Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess | Stop-Process -Force

# Reinstall dependencies
cd frontend
Remove-Item node_modules -Recurse -Force
npm install
npm run dev
```

---

### Ingestion fails immediately

**Symptoms:**
- "YouTube API key not set"
- "Invalid API key"

**Solution:**
1. Get API key: https://console.cloud.google.com/apis/credentials
2. Edit `.env`:
   ```env
   YOUTUBE_API_KEY=your_actual_key_here
   ```
3. Restart ingestion

---

### "Module not found" errors

**Symptoms:**
- ImportError: No module named 'fastapi'
- ModuleNotFoundError

**Solution:**
```powershell
# Reinstall backend dependencies
backend\venv\Scripts\python.exe -m pip install -r backend\requirements-simple.txt
```

---

## Performance Issues

### Ingestion is very slow

**Expected:** 2-5 minutes per video with full pipeline

**Solutions:**
1. Use API-only mode (faster):
   ```powershell
   backend\venv\Scripts\python.exe backend\scripts\ingest_youtube.py --source api --limit 10
   ```

2. Skip Whisper transcription:
   ```powershell
   backend\venv\Scripts\python.exe backend\scripts\ingest_youtube.py --no-whisper
   ```

3. Increase concurrency (if you have good CPU/GPU):
   ```env
   # In .env
   ASR_WORKERS=8
   IO_WORKERS=24
   ```

---

### High memory usage

**Solution:**
Reduce batch size in `.env`:
```env
BATCH_SIZE=512  # Default is 1024
ASR_WORKERS=4   # Default is 8
```

---

### Database growing too large

**Solution:**
```powershell
# Vacuum database
docker exec -it askdrchaffee-db psql -U postgres -d askdrchaffee -c "VACUUM FULL;"

# Or reset completely (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

---

## Docker Issues

### "Port already in use"

**Symptoms:**
- Error: "port 5432 is already allocated"

**Solution:**
```powershell
# Find process using port 5432
Get-NetTCPConnection -LocalPort 5432

# Stop it
Stop-Process -Id <PID> -Force

# Or change port in docker-compose.yml
```

---

### Docker containers won't start

**Solution:**
```powershell
# Stop everything
docker-compose down

# Remove volumes
docker-compose down -v

# Restart
docker-compose up -d
```

---

## API Key Issues

### YouTube API quota exceeded

**Symptoms:**
- Error: "quotaExceeded"
- 403 Forbidden errors

**Solution:**
1. Wait 24 hours for quota reset
2. Use yt-dlp fallback (no API key needed):
   ```powershell
   backend\venv\Scripts\python.exe backend\scripts\ingest_youtube.py --source yt-dlp
   ```

---

### OpenAI API errors

**Symptoms:**
- Answer mode not working
- "Invalid API key"

**Solution:**
1. Get API key: https://platform.openai.com/api-keys
2. Add to `.env`:
   ```env
   OPENAI_API_KEY=sk-...
   ANSWER_ENABLED=true
   ```

---

## Clean Reinstall

If nothing works, start fresh:

```powershell
# 1. Stop everything
.\stop.ps1
docker-compose down -v

# 2. Delete virtual environment
Remove-Item backend\venv -Recurse -Force

# 3. Delete node_modules
Remove-Item frontend\node_modules -Recurse -Force

# 4. Run setup again
powershell -ExecutionPolicy Bypass -File setup-windows.ps1
```

---

## Still Having Issues?

1. Check the logs:
   ```powershell
   # Docker logs
   docker-compose logs

   # Frontend logs
   # (visible in the terminal where npm run dev is running)
   ```

2. Check GitHub Issues: [github.com/your-repo/issues](https://github.com)

3. Create a new issue with:
   - Error message
   - Steps to reproduce
   - Your environment (Windows version, Python version, Node version)
