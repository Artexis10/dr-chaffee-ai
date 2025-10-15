# 🛡️ Render Cron Job Safety Measures

## Overview

Added comprehensive safety measures to protect against Render's 12-hour cron job limit and ensure graceful handling of long-running processes.

---

## ✅ Safety Features Added

### 1. **Timeout Protection** ⏰

**Default**: 10 hours (2 hours before Render's 12h limit)

```python
# Automatically kills job at 10h to prevent Render force-kill at 12h
signal.alarm(max_seconds)
```

**Why 10h instead of 12h?**
- Gives 2-hour buffer for graceful shutdown
- Prevents data corruption from force-kill
- Allows cleanup and notification

### 2. **Progress Monitoring** 📊

**Real-time output streaming**:
- Logs appear immediately (not buffered)
- See progress as it happens
- Detect stalls or hangs

**Periodic progress reports** (every 10 minutes):
```
⏱️  Elapsed: 1:30:00 | Remaining: 8:30:00
```

**90% warning**:
```
⚠️  Approaching timeout limit (90% of max runtime)
```

### 3. **Graceful Shutdown** 🛑

**On timeout**:
1. Sends SIGTERM to child process (graceful)
2. Waits 30 seconds for cleanup
3. Sends SIGKILL if needed (force)
4. Logs helpful message
5. Exits with code 124 (timeout)

**On interrupt** (Ctrl+C):
1. Terminates child process
2. Waits 10 seconds
3. Kills if needed
4. Exits with code 130

### 4. **Configurable Limits** ⚙️

**Command-line arguments**:
```bash
# Default: 2 days back, 10h timeout
python daily_ingest_wrapper.py

# Custom timeout
python daily_ingest_wrapper.py --max-runtime 8h

# More days (careful!)
python daily_ingest_wrapper.py --days-back 7 --max-runtime 10h

# Custom channel
python daily_ingest_wrapper.py --channel-url https://youtube.com/@example
```

### 5. **Smart Validation** ✅

**Prevents mistakes**:
- Warns if timeout > 12h
- Auto-adjusts to 10h for safety
- Validates duration format
- Checks script existence

---

## 📋 Usage Examples

### Render Cron Job Configuration

```bash
# Service: drchaffee-daily-ingest
# Type: Cron Job
# Schedule: 0 2 * * *  (Daily at 2 AM)

# Command:
python scripts/daily_ingest_wrapper.py --days-back 2 --max-runtime 10h
```

### Local Testing

```bash
# Test with short timeout
python daily_ingest_wrapper.py --max-runtime 5m --days-back 1

# Test timeout handling
python daily_ingest_wrapper.py --max-runtime 1m --days-back 7
```

### Production Settings

```bash
# Conservative (recommended)
python daily_ingest_wrapper.py --days-back 2 --max-runtime 10h

# Aggressive (if catching up)
python daily_ingest_wrapper.py --days-back 7 --max-runtime 10h
```

---

## 🎯 Expected Runtimes

### Daily Content (2h audio/day)
```
Processing time: ~1-1.5 hours
Timeout: 10 hours
Safety margin: 6-9x
Status: ✅ Very safe
```

### 7 Days Backlog (14h audio)
```
Processing time: ~8 hours
Timeout: 10 hours
Safety margin: 1.25x
Status: ⚠️  Tight but okay
```

### 14 Days Backlog (28h audio)
```
Processing time: ~16 hours
Timeout: 10 hours
Safety margin: 0.6x
Status: ❌ Will timeout - process locally!
```

---

## 🚨 What Happens on Timeout?

### Automatic Actions

1. **Log Warning**:
   ```
   ⏰ TIMEOUT REACHED - Stopping gracefully
   💡 This job has been running too long.
   💡 Consider processing this content locally and syncing the database.
   ```

2. **Graceful Shutdown**:
   - Sends SIGTERM to ingestion script
   - Waits 30s for cleanup
   - Force kills if needed

3. **Notification** (if configured):
   ```
   Subject: Dr. Chaffee Daily Ingestion - Timeout
   Message: Process exceeded 10h timeout
            Consider local processing.
   ```

4. **Exit Code**: 124 (timeout)

### What You Should Do

**If timeout happens**:
1. Check how much content accumulated
2. Process locally on GPU (faster)
3. Sync database to Render
4. Resume daily cron

**Example**:
```bash
# On your local machine (GPU)
python ingest_youtube_enhanced.py --channel-url URL --days-back 14

# Sync to Render
python sync_to_production.py
```

---

## 📊 Monitoring & Logs

### View Logs on Render

```bash
# Live logs
Render Dashboard → drchaffee-daily-ingest → Logs

# Look for:
⏰ Timeout protection enabled: 36000s (10h)
📊 Monitoring progress...
⏱️  Elapsed: 1:30:00 | Remaining: 8:30:00
⚠️  Approaching timeout limit (90% of max runtime)
✅ Daily ingestion completed successfully
```

### Exit Codes

```
0   = Success
1   = Error
124 = Timeout (exceeded max-runtime)
130 = Interrupted (Ctrl+C)
```

### Log Files

```
backend/logs/daily_ingest.log       - Full log history
Render Dashboard → Logs             - Real-time logs
```

---

## ⚙️ Configuration Options

### Environment Variables

```bash
# In Render dashboard → Environment
YOUTUBE_CHANNEL_URL=https://www.youtube.com/@anthonychaffeemd
NOTIFICATION_WEBHOOK_URL=https://hooks.slack.com/...  # Optional
NOTIFICATION_EMAIL=you@example.com                    # Optional
```

### Command Arguments

```bash
--days-back N         # Days to look back (default: 2)
--max-runtime TIME    # Max runtime (default: 10h)
--channel-url URL     # Override channel URL
```

### Duration Format

```bash
10h          # 10 hours
8h30m        # 8 hours 30 minutes
600m         # 600 minutes (10 hours)
2h15m30s     # 2 hours 15 minutes 30 seconds
```

---

## 🔧 Advanced: Notifications

### Slack Webhook

```bash
# Set in Render environment
NOTIFICATION_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Receives:
✅ Success: "Completed in 1:23:45"
❌ Failure: "Exit code: 1 - Error details..."
⏰ Timeout: "Process exceeded 10h timeout"
```

### Email (Future)

```bash
NOTIFICATION_EMAIL=admin@example.com
# Implement in send_notification() function
```

---

## 📋 Checklist: Render Setup

- [ ] Create cron job service
- [ ] Set schedule: `0 2 * * *`
- [ ] Set command: `python scripts/daily_ingest_wrapper.py --days-back 2 --max-runtime 10h`
- [ ] Add environment variables (API keys, channel URL)
- [ ] Set plan: Starter ($7/month, 512MB RAM)
- [ ] Test with manual trigger
- [ ] Monitor first run
- [ ] Verify logs show timeout protection
- [ ] Check completion time < 2 hours

---

## 🎯 Best Practices

### ✅ Do

- Keep `--days-back` at 2 for daily runs
- Use 10h timeout (2h buffer before Render limit)
- Monitor logs for first few runs
- Process bulk content locally
- Sync database after local processing

### ❌ Don't

- Set timeout > 12h (Render will kill anyway)
- Process 2+ weeks on Render cron
- Ignore timeout warnings
- Skip local processing for bulk work
- Forget to sync database after local processing

---

## 🚀 Quick Reference

### Daily Cron (Render)
```bash
python scripts/daily_ingest_wrapper.py --days-back 2 --max-runtime 10h
```

### Catch-Up (Local GPU)
```bash
python scripts/ingest_youtube_enhanced.py --days-back 14
python scripts/sync_to_production.py
```

### Test Timeout
```bash
python scripts/daily_ingest_wrapper.py --max-runtime 1m --days-back 1
```

### View Help
```bash
python scripts/daily_ingest_wrapper.py --help
```

---

## 📊 Performance Expectations

| Content | CPU Time | GPU Time | Render Safe? |
|---------|----------|----------|--------------|
| 2h/day | 1-1.5h | 2-3 min | ✅ Yes |
| 7 days (14h) | 8h | 15-20 min | ⚠️  Tight |
| 14 days (28h) | 16h | 30-40 min | ❌ No - use GPU |
| 1200h bulk | 700h | 24h | ❌ No - use GPU |

---

## 🎉 Summary

**Safety measures added**:
- ✅ 10-hour timeout protection
- ✅ Real-time progress monitoring
- ✅ Graceful shutdown handling
- ✅ Configurable limits
- ✅ Smart validation
- ✅ Helpful error messages
- ✅ Exit code standards
- ✅ Notification support

**Result**: Your Render cron job is now protected against the 12-hour limit with a 2-hour safety buffer and graceful handling of timeouts.

**Next**: Deploy to Render and monitor first run! 🚀
