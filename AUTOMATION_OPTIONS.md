# 🤖 Automation Options for Daily Ingestion

## TL;DR - Best Options

| Method | Best For | Complexity | Features |
|--------|----------|------------|----------|
| **Systemd Timer** | Linux servers | Medium | ⭐⭐⭐⭐⭐ Best |
| **GitHub Actions** | Cloud-first | Low | ⭐⭐⭐⭐ Great |
| **Docker + Cron** | Containers | Medium | ⭐⭐⭐⭐ Great |
| **Task Scheduler** | Windows | Low | ⭐⭐⭐ Good |
| **Crontab** | Simple Linux | Very Low | ⭐⭐ Basic |

---

## Option 1: Systemd Timer (⭐ Recommended for Linux)

### Why Better Than Cron

✅ **Better logging**: `journalctl -u drchaffee-ingest -f`  
✅ **Dependency management**: Waits for database/network  
✅ **Automatic retry**: Restarts on failure  
✅ **Resource limits**: Prevents runaway processes  
✅ **Persistent**: Runs on boot if missed  
✅ **Status monitoring**: `systemctl status drchaffee-ingest`

### Setup (One Command)

```bash
cd /path/to/ask-dr-chaffee/backend/deployment
chmod +x setup_systemd.sh
./setup_systemd.sh
```

**That's it!** The script:
1. Updates paths automatically
2. Installs service and timer
3. Enables and starts timer
4. Shows next run time

### Usage

```bash
# View logs (live)
sudo journalctl -u drchaffee-ingest -f

# Check status
sudo systemctl status drchaffee-ingest.timer

# See next run time
sudo systemctl list-timers drchaffee-ingest.timer

# Run manually now
sudo systemctl start drchaffee-ingest

# Disable
sudo systemctl disable drchaffee-ingest.timer
```

### Files Created

- `deployment/drchaffee-ingest.service` - Service definition
- `deployment/drchaffee-ingest.timer` - Timer schedule
- `deployment/setup_systemd.sh` - Installation script

---

## Option 2: GitHub Actions (⭐ Best for Cloud/CI)

### Why This is Great

✅ **No server needed**: Runs on GitHub's infrastructure  
✅ **Free**: 2000 minutes/month on free tier  
✅ **Notifications**: Built-in email/Slack alerts  
✅ **Version controlled**: Schedule in git  
✅ **Secrets management**: Secure credential storage

### Setup

Create `.github/workflows/daily-ingest.yml`:

```yaml
name: Daily Video Ingestion

on:
  schedule:
    # Run at 2 AM UTC daily
    - cron: '0 2 * * *'
  workflow_dispatch:  # Allow manual trigger

jobs:
  ingest:
    runs-on: ubuntu-latest
    timeout-minutes: 480  # 8 hours
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      
      - name: Run ingestion
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          YOUTUBE_CHANNEL_URL: https://www.youtube.com/@anthonychaffeemd
        run: |
          cd backend
          python scripts/ingest_youtube_enhanced_asr.py \
            --channel-url "$YOUTUBE_CHANNEL_URL" \
            --days-back 2 \
            --skip-existing
      
      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: ingestion-logs
          path: backend/logs/
      
      - name: Notify on failure
        if: failure()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Pros/Cons

**Pros**:
- ✅ No server maintenance
- ✅ Free (for reasonable usage)
- ✅ Built-in notifications
- ✅ Easy to modify schedule

**Cons**:
- ❌ Requires database accessible from internet
- ❌ Limited to 6 hours runtime (can extend to 8h)
- ❌ No GPU (CPU only)

**Perfect for**: Production CPU-only setup with cloud database

---

## Option 3: Docker + Cron (⭐ Best for Containers)

### Why This is Great

✅ **Isolated environment**: No dependency conflicts  
✅ **Portable**: Works anywhere Docker runs  
✅ **Easy rollback**: Version with tags  
✅ **Resource limits**: Built-in CPU/memory caps

### Setup

Create `backend/Dockerfile.cron`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create cron job
RUN apt-get update && apt-get install -y cron && \
    echo "0 2 * * * cd /app && python scripts/ingest_youtube_enhanced_asr.py --channel-url https://www.youtube.com/@anthonychaffeemd --days-back 2 --skip-existing >> /var/log/cron.log 2>&1" > /etc/cron.d/drchaffee && \
    chmod 0644 /etc/cron.d/drchaffee && \
    crontab /etc/cron.d/drchaffee

CMD ["cron", "-f"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  drchaffee-cron:
    build:
      context: ./backend
      dockerfile: Dockerfile.cron
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - YOUTUBE_CHANNEL_URL=https://www.youtube.com/@anthonychaffeemd
    volumes:
      - ./backend/logs:/app/logs
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

### Usage

```bash
# Start
docker-compose up -d drchaffee-cron

# View logs
docker-compose logs -f drchaffee-cron

# Stop
docker-compose down
```

---

## Option 4: Windows Task Scheduler (⭐ Best for Windows)

### Why This Works

✅ **Native Windows**: No extra tools needed  
✅ **GUI**: Easy to configure  
✅ **Reliable**: Built into Windows  
✅ **Notifications**: Can send emails

### Setup (PowerShell Script)

Create `backend/deployment/setup_windows_task.ps1`:

```powershell
# Setup Windows Task Scheduler for daily ingestion

$TaskName = "DrChaffee-DailyIngest"
$ScriptPath = "C:\Users\hugoa\Desktop\ask-dr-chaffee\backend\scripts\daily_ingest_wrapper.py"
$PythonPath = (Get-Command python).Source
$LogPath = "C:\Users\hugoa\Desktop\ask-dr-chaffee\backend\logs\task_scheduler.log"

# Create task action
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument $ScriptPath -WorkingDirectory "C:\Users\hugoa\Desktop\ask-dr-chaffee\backend"

# Create trigger (daily at 2 AM)
$Trigger = New-ScheduledTaskTrigger -Daily -At 2am

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 8)

# Register task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Daily ingestion of Dr. Chaffee videos" `
    -User $env:USERNAME

Write-Host "✅ Task scheduled successfully!"
Write-Host "Task Name: $TaskName"
Write-Host "Next Run: " (Get-ScheduledTask -TaskName $TaskName).NextRunTime
```

### Usage

```powershell
# Setup
cd C:\Users\hugoa\Desktop\ask-dr-chaffee\backend\deployment
.\setup_windows_task.ps1

# View in GUI
taskschd.msc

# Run manually
Start-ScheduledTask -TaskName "DrChaffee-DailyIngest"

# Check status
Get-ScheduledTask -TaskName "DrChaffee-DailyIngest"

# Remove
Unregister-ScheduledTask -TaskName "DrChaffee-DailyIngest"
```

---

## Option 5: Simple Crontab (Basic)

### When to Use

✅ Quick and dirty  
✅ Simple Linux server  
✅ No fancy features needed

### Setup

```bash
crontab -e

# Add this line:
0 2 * * * cd /path/to/ask-dr-chaffee/backend && python scripts/ingest_youtube_enhanced_asr.py --channel-url "https://www.youtube.com/@anthonychaffeemd" --days-back 2 --skip-existing >> logs/cron.log 2>&1
```

### Pros/Cons

**Pros**:
- ✅ Simple
- ✅ Works everywhere

**Cons**:
- ❌ Poor logging
- ❌ No error handling
- ❌ No notifications
- ❌ No resource limits

---

## Option 6: Python Scheduler (APScheduler)

### Why This is Interesting

✅ **Pure Python**: No system dependencies  
✅ **Flexible**: Easy to customize  
✅ **Integrated**: Runs with your app

### Setup

Create `backend/scripts/scheduler.py`:

```python
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import subprocess
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_ingestion():
    """Run daily ingestion"""
    logger.info("Starting daily ingestion...")
    
    result = subprocess.run([
        sys.executable,
        "scripts/ingest_youtube_enhanced_asr.py",
        "--channel-url", "https://www.youtube.com/@anthonychaffeemd",
        "--days-back", "2",
        "--skip-existing"
    ])
    
    if result.returncode == 0:
        logger.info("✅ Ingestion completed successfully")
    else:
        logger.error(f"❌ Ingestion failed with code {result.returncode}")

if __name__ == '__main__':
    scheduler = BlockingScheduler()
    
    # Run daily at 2 AM
    scheduler.add_job(
        run_ingestion,
        CronTrigger(hour=2, minute=0),
        id='daily_ingest',
        name='Daily video ingestion'
    )
    
    logger.info("Scheduler started. Press Ctrl+C to exit.")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
```

### Usage

```bash
# Run as background service
nohup python scripts/scheduler.py > logs/scheduler.log 2>&1 &

# Or with systemd
# Create service file that runs scheduler.py
```

---

## 🎯 Recommendation by Environment

### Production Linux Server
**Use: Systemd Timer** (Option 1)
- Most robust
- Best logging
- Native to Linux
- Easy monitoring

### Cloud/Serverless
**Use: GitHub Actions** (Option 2)
- No server needed
- Free tier sufficient
- Built-in notifications

### Docker/Kubernetes
**Use: Docker + Cron** (Option 3)
- Isolated environment
- Easy to deploy
- Portable

### Windows Server
**Use: Task Scheduler** (Option 4)
- Native to Windows
- GUI available
- Reliable

### Quick & Simple
**Use: Crontab** (Option 5)
- Fastest setup
- Good enough for basic needs

---

## 📊 Feature Comparison

| Feature | Systemd | GitHub Actions | Docker | Task Scheduler | Crontab |
|---------|---------|----------------|--------|----------------|---------|
| **Logging** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| **Error Handling** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| **Notifications** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ |
| **Resource Limits** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| **Ease of Setup** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Monitoring** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ |

---

## ✅ My Recommendation

### For Your Use Case (Linux Production Server)

**Use Systemd Timer** (Option 1):

```bash
# One-time setup
cd /path/to/ask-dr-chaffee/backend/deployment
chmod +x setup_systemd.sh
./setup_systemd.sh
```

**Why**:
1. ✅ Best logging (`journalctl -u drchaffee-ingest -f`)
2. ✅ Automatic retry on failure
3. ✅ Resource limits (prevent runaway CPU)
4. ✅ Dependency management (waits for database)
5. ✅ Easy monitoring (`systemctl status`)
6. ✅ Native to Linux (no extra dependencies)

**Better than crontab because**:
- Structured logging (not just a text file)
- Automatic retry (cron doesn't retry)
- Resource limits (cron can't limit CPU/memory)
- Status monitoring (cron has no status)
- Dependency management (cron runs blindly)

---

## 🚀 Quick Start

### For Linux (Recommended)

```bash
cd /path/to/ask-dr-chaffee/backend/deployment
chmod +x setup_systemd.sh
./setup_systemd.sh

# Done! Check status:
sudo systemctl status drchaffee-ingest.timer
```

### For Windows

```powershell
cd C:\Users\hugoa\Desktop\ask-dr-chaffee\backend\deployment
.\setup_windows_task.ps1

# Done! Check in Task Scheduler GUI
```

### For "Just Make It Work"

```bash
# Add to crontab
crontab -e

# Add line:
0 2 * * * cd /path/to/backend && python scripts/daily_ingest_wrapper.py >> logs/cron.log 2>&1
```

---

## 📝 Summary

**Yes, there are better ways than `crontab -e`!**

**Best option**: Systemd Timer (Linux) or Task Scheduler (Windows)
- Better logging
- Error handling
- Notifications
- Resource limits
- Easier monitoring

**Setup time**: 2 minutes with provided scripts

**You're right to ask** - crontab is old-school. Modern alternatives are much better! 🎉
