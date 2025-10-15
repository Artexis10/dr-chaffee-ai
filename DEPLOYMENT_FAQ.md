# 🤔 Deployment FAQ

## Q: Did you make a guide document for production deployment?

**Yes! Multiple guides**:

### 1. **DEPLOYMENT_SUMMARY.md** ⭐ START HERE
- Quick reference for deployment
- Step-by-step timeline
- Command cheat sheet
- Pre-deployment checklist

### 2. **PRODUCTION_READY_CHECKLIST.md**
- Detailed pre-deployment checklist
- Fixes for common issues
- Performance expectations
- Emergency recovery

### 3. **HYBRID_DEPLOYMENT_WORKFLOW.md**
- Complete workflow: Local GPU + Production CPU
- Database sync procedures
- Daily cron setup
- Monitoring guide

### 4. **SYNC_GUIDE.md**
- Automated database sync
- Usage examples
- Troubleshooting
- Security best practices

### 5. **AUTOMATION_OPTIONS.md**
- Comparison of automation methods
- Systemd vs crontab vs GitHub Actions
- Setup instructions for each

### 6. **QUALITY_ANALYSIS.md**
- Model quality comparison
- Why BGE-Small ≠ GTE-Qwen2
- Dimension mismatch explanation
- Performance trade-offs

### 7. **backend/deployment/README.md**
- Systemd timer specific guide
- Daily usage commands
- Troubleshooting

---

## Q: Why the random delay? `RandomizedDelaySec=1800`

**Great question!** There are several good reasons:

### 1. **Avoid Thundering Herd Problem**

If you have multiple services all starting at exactly 2:00 AM:
- Database gets hit by all services simultaneously
- Network bandwidth saturated
- Server CPU spikes to 100%
- Everything slows down

**With random delay (0-30 min)**:
- Services start between 2:00 AM - 2:30 AM
- Load is distributed
- System stays responsive

### 2. **Avoid External API Rate Limits**

Your script calls:
- YouTube API (for video metadata)
- OpenAI API (for answer generation)
- Hugging Face (model downloads)

If many users run similar scripts at exactly 2:00 AM:
- API providers see spike
- Rate limits kick in
- Your requests fail

**Random delay spreads the load**.

### 3. **Better for Shared Infrastructure**

If your production server hosts multiple applications:
- All cron jobs at 2:00 AM = resource contention
- Random delays = smoother operation
- Better overall system performance

### 4. **Persistent Timer Benefit**

The `Persistent=true` setting means:
- If server was off at 2:00 AM, run on next boot
- Random delay prevents boot storm
- Multiple missed timers don't all fire at once

### Example Scenario

**Without random delay**:
```
2:00:00 AM - Dr. Chaffee ingestion starts
2:00:00 AM - Database backup starts
2:00:00 AM - Log rotation starts
2:00:00 AM - Email sending starts
→ Server CPU: 100%, everything slow
```

**With random delay**:
```
2:00:00 AM - Dr. Chaffee ingestion starts
2:08:23 AM - Database backup starts
2:15:47 AM - Log rotation starts
2:22:11 AM - Email sending starts
→ Server CPU: 60-70%, smooth operation
```

---

## Q: Can I remove the random delay?

**Yes, but not recommended**. If you want exact 2:00 AM:

```ini
[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true
# RandomizedDelaySec=1800  # Comment out or remove
```

**When to remove**:
- ✅ You're the only service on the server
- ✅ You need exact timing (e.g., sync with external system)
- ✅ You've tested and confirmed no resource contention

**When to keep** (recommended):
- ✅ Shared server with other services
- ✅ Multiple cron jobs around same time
- ✅ Calling external APIs
- ✅ General best practice

---

## Q: How do I change the schedule?

### Run at 3 AM instead of 2 AM

Edit `/etc/systemd/system/drchaffee-ingest.timer`:

```ini
[Timer]
OnCalendar=*-*-* 03:00:00  # Changed from 02:00:00
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart drchaffee-ingest.timer
```

### Run twice daily (2 AM and 2 PM)

```ini
[Timer]
OnCalendar=*-*-* 02:00:00
OnCalendar=*-*-* 14:00:00
```

### Run every 6 hours

```ini
[Timer]
OnCalendar=*-*-* 00,06,12,18:00:00
```

### Run on weekdays only

```ini
[Timer]
OnCalendar=Mon,Tue,Wed,Thu,Fri *-*-* 02:00:00
```

---

## Q: How do I monitor the timer?

### Check next run time
```bash
sudo systemctl list-timers drchaffee-ingest.timer
```

Output:
```
NEXT                         LEFT     LAST PASSED UNIT
Wed 2025-10-16 02:15:23 UTC  3h 45min n/a  n/a    drchaffee-ingest.timer
```

### Check timer status
```bash
sudo systemctl status drchaffee-ingest.timer
```

### View logs
```bash
# Live logs
sudo journalctl -u drchaffee-ingest -f

# Last 100 lines
sudo journalctl -u drchaffee-ingest -n 100

# Since yesterday
sudo journalctl -u drchaffee-ingest --since yesterday

# Specific date
sudo journalctl -u drchaffee-ingest --since "2025-10-15"
```

---

## Q: What if the job fails?

### Automatic Retry

The service is configured to retry on failure:

```ini
[Service]
Restart=on-failure
RestartSec=300  # Wait 5 minutes before retry
```

### Manual Retry

```bash
# Run immediately
sudo systemctl start drchaffee-ingest

# Watch logs
sudo journalctl -u drchaffee-ingest -f
```

### Check Failure Reason

```bash
# View last run status
sudo systemctl status drchaffee-ingest

# View error logs
sudo journalctl -u drchaffee-ingest -p err
```

---

## Q: How do I disable the timer temporarily?

### Stop timer (won't run until re-enabled)
```bash
sudo systemctl stop drchaffee-ingest.timer
```

### Disable timer (won't start on boot)
```bash
sudo systemctl disable drchaffee-ingest.timer
```

### Re-enable
```bash
sudo systemctl enable drchaffee-ingest.timer
sudo systemctl start drchaffee-ingest.timer
```

---

## Q: Can I test without waiting for 2 AM?

**Yes! Run manually**:

```bash
# Run the service immediately
sudo systemctl start drchaffee-ingest

# Watch logs in real-time
sudo journalctl -u drchaffee-ingest -f
```

This runs the exact same code that the timer would run.

---

## Q: What's the difference between service and timer?

### Service (`drchaffee-ingest.service`)
- **What**: Defines the actual job (run ingestion script)
- **When**: Runs when triggered (by timer or manually)
- **Like**: A function definition

### Timer (`drchaffee-ingest.timer`)
- **What**: Defines the schedule (daily at 2 AM)
- **When**: Always running, triggers service at scheduled time
- **Like**: A cron job

**Analogy**:
- Service = "How to bake a cake"
- Timer = "Bake a cake every day at 2 AM"

---

## Q: How much disk space do I need?

### Models (one-time download)
- Whisper base: ~150 MB
- GTE-Qwen2-1.5B: ~3 GB
- SpeechBrain ECAPA: ~100 MB
- **Total**: ~3.5 GB

### Database (grows over time)
- 1000 videos (~800h): ~5-10 GB
- 5000 videos (~4000h): ~25-50 GB
- Depends on: segment count, embedding dimensions

### Logs
- ~100 MB per month (with daily ingestion)
- Rotate logs monthly to save space

### Temporary Files
- Audio downloads: Cleaned up after processing
- Peak usage: ~2 GB during processing

**Recommended**: 50-100 GB free space

---

## Q: What if I run out of memory?

### Reduce Batch Sizes

Edit `.env`:
```bash
EMBEDDING_BATCH_SIZE=8  # Down from 16
VOICE_ENROLLMENT_BATCH_SIZE=2  # Down from 4
```

### Limit Resource Usage

Edit service file:
```ini
[Service]
MemoryMax=4G  # Down from 8G
CPUQuota=200%  # Down from 400%
```

### Process Fewer Videos

```bash
# Process only last 1 day instead of 2
--days-back 1
```

---

## Q: Can I run this on Windows?

**Yes, but use Task Scheduler instead of systemd**.

See `AUTOMATION_OPTIONS.md` for Windows setup guide.

---

## Q: How do I update the code?

### On Production Server

```bash
# Pull latest code
cd /path/to/ask-dr-chaffee
git pull

# Restart service (if running)
sudo systemctl restart drchaffee-ingest

# Or wait for next scheduled run
```

### Update Dependencies

```bash
cd backend
pip install -r requirements.txt --upgrade
```

---

## Q: Where are the logs stored?

### Systemd Logs (Recommended)
```bash
# View with journalctl
sudo journalctl -u drchaffee-ingest

# Stored in: /var/log/journal/
```

### Application Logs
```bash
# Defined in service file
StandardOutput=append:/path/to/backend/logs/ingest.log
StandardError=append:/path/to/backend/logs/ingest-error.log
```

### Rotate Logs

Systemd automatically rotates journal logs. For application logs:

```bash
# Install logrotate config
sudo nano /etc/logrotate.d/drchaffee

# Add:
/path/to/backend/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

---

## 🎯 Quick Reference

### Most Common Commands

```bash
# Check next run
sudo systemctl list-timers drchaffee-ingest.timer

# View logs
sudo journalctl -u drchaffee-ingest -f

# Run now
sudo systemctl start drchaffee-ingest

# Check status
sudo systemctl status drchaffee-ingest.timer
```

### Files to Know

- `/etc/systemd/system/drchaffee-ingest.service` - Job definition
- `/etc/systemd/system/drchaffee-ingest.timer` - Schedule
- `/path/to/backend/.env` - Configuration
- `/path/to/backend/logs/` - Application logs
