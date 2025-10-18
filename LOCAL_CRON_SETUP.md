# Local Scheduled Job Setup (GPU Ingestion)

## Why Local Scheduling?

**Benefits:**
- ✅ **Free:** No cron job costs
- ✅ **Fast:** 50x faster with GPU (5-10 min vs 1-2 hours)
- ✅ **Consistent Quality:** Always use distil-large-v3
- ✅ **More RAM:** Use all your system RAM, not limited to 512MB
- ✅ **Flexible:** Run when you want, process as many videos as needed

**Trade-off:**
- ⚠️ Your computer needs to be on when the job runs
- ⚠️ Requires initial setup

## Option 1: Linux/macOS Cron (Recommended)

### Setup

1. **Create the ingestion script:**
```bash
# Create script directory
mkdir -p ~/bin

# Create the script
cat > ~/bin/ingest-chaffee.sh << 'EOF'
#!/bin/bash
set -e

# Configuration
PROJECT_DIR="/home/hugo-kivi/Desktop/personal/dr-chaffee-ai"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/local-cron-$(date +%Y%m%d-%H%M%S).log"

# Create log directory
mkdir -p "$LOG_DIR"

# Log start
echo "========================================" | tee -a "$LOG_FILE"
echo "Ingestion started at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Change to project directory
cd "$PROJECT_DIR/backend"

# Activate virtual environment
source .venv/bin/activate

# Run ingestion
python3 scripts/ingest_youtube.py \
    --source yt-dlp \
    --days-back 7 \
    --limit-unprocessed \
    --skip-shorts \
    --newest-first \
    2>&1 | tee -a "$LOG_FILE"

# Log completion
echo "========================================" | tee -a "$LOG_FILE"
echo "Ingestion completed at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Keep only last 10 log files
cd "$LOG_DIR"
ls -t local-cron-*.log | tail -n +11 | xargs -r rm

exit 0
EOF

# Make it executable
chmod +x ~/bin/ingest-chaffee.sh
```

2. **Test the script:**
```bash
~/bin/ingest-chaffee.sh
```

3. **Set up cron job:**
```bash
# Open crontab editor
crontab -e

# Add one of these lines (choose your preferred schedule):

# Option A: Daily at 2 AM (same as Render)
0 2 * * * /home/hugo-kivi/bin/ingest-chaffee.sh

# Option B: Every Monday at 8 AM (weekly)
0 8 * * 1 /home/hugo-kivi/bin/ingest-chaffee.sh

# Option C: Every 3 days at 10 PM
0 22 */3 * * /home/hugo-kivi/bin/ingest-chaffee.sh

# Option D: Twice per week (Monday and Thursday at 9 PM)
0 21 * * 1,4 /home/hugo-kivi/bin/ingest-chaffee.sh
```

4. **Verify cron is set up:**
```bash
crontab -l
```

### Cron Schedule Examples

```bash
# Format: minute hour day month weekday command
# minute: 0-59
# hour: 0-23
# day: 1-31
# month: 1-12
# weekday: 0-7 (0 and 7 are Sunday)

# Daily at 2 AM
0 2 * * * /home/hugo-kivi/bin/ingest-chaffee.sh

# Every 12 hours (2 AM and 2 PM)
0 2,14 * * * /home/hugo-kivi/bin/ingest-chaffee.sh

# Every Sunday at midnight
0 0 * * 0 /home/hugo-kivi/bin/ingest-chaffee.sh

# First day of every month at 3 AM
0 3 1 * * /home/hugo-kivi/bin/ingest-chaffee.sh

# Every 6 hours
0 */6 * * * /home/hugo-kivi/bin/ingest-chaffee.sh
```

### View Logs

```bash
# View latest log
ls -t ~/Desktop/personal/dr-chaffee-ai/logs/local-cron-*.log | head -1 | xargs cat

# View last 50 lines of latest log
ls -t ~/Desktop/personal/dr-chaffee-ai/logs/local-cron-*.log | head -1 | xargs tail -50

# Follow live log (if running)
tail -f ~/Desktop/personal/dr-chaffee-ai/logs/local-cron-*.log
```

---

## Option 2: Windows Task Scheduler

### Setup

1. **Create the ingestion script:**

Create `C:\Users\YourName\bin\ingest-chaffee.bat`:
```batch
@echo off
setlocal

REM Configuration
set PROJECT_DIR=C:\Users\YourName\Desktop\personal\dr-chaffee-ai
set LOG_DIR=%PROJECT_DIR%\logs
set LOG_FILE=%LOG_DIR%\local-cron-%date:~-4,4%%date:~-10,2%%date:~-7,2%-%time:~0,2%%time:~3,2%%time:~6,2%.log

REM Create log directory
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Log start
echo ======================================== >> "%LOG_FILE%"
echo Ingestion started at %date% %time% >> "%LOG_FILE%"
echo ======================================== >> "%LOG_FILE%"

REM Change to project directory
cd /d "%PROJECT_DIR%\backend"

REM Activate virtual environment and run ingestion
call .venv\Scripts\activate.bat
python scripts\ingest_youtube.py --source yt-dlp --days-back 7 --limit-unprocessed --skip-shorts --newest-first >> "%LOG_FILE%" 2>&1

REM Log completion
echo ======================================== >> "%LOG_FILE%"
echo Ingestion completed at %date% %time% >> "%LOG_FILE%"
echo ======================================== >> "%LOG_FILE%"

endlocal
exit /b 0
```

2. **Create scheduled task:**

Open PowerShell as Administrator:
```powershell
# Create scheduled task
$action = New-ScheduledTaskAction -Execute "C:\Users\YourName\bin\ingest-chaffee.bat"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "DrChaffeeIngestion" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Daily video ingestion for Dr. Chaffee AI"
```

3. **Verify task:**
```powershell
Get-ScheduledTask -TaskName "DrChaffeeIngestion"
```

4. **Test manually:**
```powershell
Start-ScheduledTask -TaskName "DrChaffeeIngestion"
```

### Alternative: Task Scheduler GUI

1. Open Task Scheduler (search in Start menu)
2. Click "Create Basic Task"
3. Name: "Dr Chaffee Ingestion"
4. Trigger: Daily at 2:00 AM
5. Action: Start a program
6. Program: `C:\Users\YourName\bin\ingest-chaffee.bat`
7. Finish

---

## Option 3: macOS launchd

### Setup

1. **Create the ingestion script** (same as Linux above):
```bash
mkdir -p ~/bin
# ... (same script as Linux)
chmod +x ~/bin/ingest-chaffee.sh
```

2. **Create launchd plist:**
```bash
cat > ~/Library/LaunchAgents/com.drchaffee.ingestion.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.drchaffee.ingestion</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YourName/bin/ingest-chaffee.sh</string>
    </array>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>/Users/YourName/Desktop/personal/dr-chaffee-ai/logs/launchd-out.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/YourName/Desktop/personal/dr-chaffee-ai/logs/launchd-err.log</string>
    
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF
```

3. **Load the job:**
```bash
launchctl load ~/Library/LaunchAgents/com.drchaffee.ingestion.plist
```

4. **Verify:**
```bash
launchctl list | grep drchaffee
```

5. **Test manually:**
```bash
launchctl start com.drchaffee.ingestion
```

---

## Option 4: Manual Run (Simplest)

If you don't want automated scheduling, just run manually when needed:

```bash
# Quick command (run from anywhere)
cd ~/Desktop/personal/dr-chaffee-ai/backend && \
source .venv/bin/activate && \
python3 scripts/ingest_youtube.py \
    --source yt-dlp \
    --days-back 7 \
    --limit-unprocessed \
    --skip-shorts \
    --newest-first
```

**When to run:**
- After publishing new videos
- Once per week
- When you notice new content

---

## Recommended Schedule

Based on Dr. Chaffee's publishing frequency:

### If he publishes 2-3 videos per week:
```bash
# Run twice per week (Monday and Thursday)
0 21 * * 1,4 /home/hugo-kivi/bin/ingest-chaffee.sh
```

### If he publishes daily:
```bash
# Run daily at 2 AM
0 2 * * * /home/hugo-kivi/bin/ingest-chaffee.sh
```

### If he publishes irregularly:
```bash
# Run weekly on Sunday night
0 22 * * 0 /home/hugo-kivi/bin/ingest-chaffee.sh
```

---

## Monitoring & Maintenance

### Check if cron is running:
```bash
# Linux/macOS
ps aux | grep ingest-chaffee

# Check cron logs (Linux)
grep CRON /var/log/syslog | grep ingest-chaffee

# Check cron logs (macOS)
log show --predicate 'process == "cron"' --last 1d
```

### View ingestion logs:
```bash
# Latest log
ls -t logs/local-cron-*.log | head -1 | xargs cat

# All logs from last 7 days
find logs -name "local-cron-*.log" -mtime -7 -exec cat {} \;

# Count successful runs
grep "Ingestion completed" logs/local-cron-*.log | wc -l
```

### Troubleshooting

**Issue: Cron job doesn't run**
```bash
# Check cron service is running
systemctl status cron  # Linux
# or
sudo launchctl list | grep cron  # macOS

# Check crontab is set
crontab -l

# Check script permissions
ls -l ~/bin/ingest-chaffee.sh

# Test script manually
~/bin/ingest-chaffee.sh
```

**Issue: Script fails**
```bash
# Check logs
tail -50 logs/local-cron-*.log

# Common issues:
# 1. Virtual environment not activated
# 2. Wrong project path
# 3. Missing environment variables
# 4. Database connection issues
```

**Issue: GPU not detected**
```bash
# Check CUDA is available
python3 -c "import torch; print(torch.cuda.is_available())"

# Check GPU usage during ingestion
watch -n 1 nvidia-smi
```

---

## Disable Render Cron

Once your local cron is working, disable the Render cron:

### Option A: Via Render Dashboard
1. Go to your cron job in Render dashboard
2. Click "Suspend" or "Delete"

### Option B: Via SSH (if you have access)
```bash
# SSH into Render
ssh user@your-render-instance

# Disable systemd timer
sudo systemctl disable drchaffee-ingest.timer
sudo systemctl stop drchaffee-ingest.timer

# Verify it's stopped
sudo systemctl status drchaffee-ingest.timer
```

---

## Cost Comparison

| Method | Cost | Speed | Quality | Automation |
|--------|------|-------|---------|------------|
| **Render Starter** | $0.32/mo | 🐌 Slow | ⚠️ Mixed | ✅ Auto |
| **Render Pro** | $3.55/mo | 🐌 Slow | ✅ High | ✅ Auto |
| **Local Cron (GPU)** | $0 | 🚀 Fast | ✅ High | ✅ Auto* |
| **Manual (GPU)** | $0 | 🚀 Fast | ✅ High | ❌ Manual |

*Requires computer to be on

---

## My Recommendation

**Use Linux/macOS cron with weekly schedule:**

```bash
# Run every Sunday at 10 PM
0 22 * * 0 /home/hugo-kivi/bin/ingest-chaffee.sh
```

**Why:**
- ✅ Free
- ✅ Fast (5-10 minutes on GPU)
- ✅ Consistent quality (distil-large-v3)
- ✅ Automated
- ✅ Flexible (easy to change schedule)

**Setup time:** 5 minutes

**Maintenance:** None (just keep your computer on at scheduled time)

---

## Quick Start

```bash
# 1. Create script
mkdir -p ~/bin
curl -o ~/bin/ingest-chaffee.sh https://your-repo/ingest-chaffee.sh
chmod +x ~/bin/ingest-chaffee.sh

# 2. Test it
~/bin/ingest-chaffee.sh

# 3. Set up cron (weekly on Sunday at 10 PM)
(crontab -l 2>/dev/null; echo "0 22 * * 0 $HOME/bin/ingest-chaffee.sh") | crontab -

# 4. Verify
crontab -l

# Done! ✅
```

Your ingestion will now run automatically every Sunday at 10 PM using your GPU.
