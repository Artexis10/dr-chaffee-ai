# Systemd Timer Deployment Guide

## Quick Start (On Production Linux Server)

```bash
# 1. Copy deployment files to production server
scp -r deployment user@production-server:/path/to/ask-dr-chaffee/backend/

# 2. SSH into production server
ssh user@production-server

# 3. Run setup script
cd /path/to/ask-dr-chaffee/backend/deployment
chmod +x setup_systemd.sh
./setup_systemd.sh
```

**That's it!** The timer is now running.

**Note:** The cron job now uses `ingest_youtube.py` instead of the deprecated `ingest_youtube_enhanced_asr.py`.

**⚠️ Render Starter Plan:** The systemd service is configured for Render's Starter plan (512MB RAM, shared CPU). It processes a maximum of 2 videos per run to avoid OOM kills and timeouts. For bulk processing, use a local machine with GPU.

**Required Environment Variables:**
- `DATABASE_URL` - PostgreSQL connection
- `NOMIC_API_KEY` - For embeddings (free: 10M tokens/month)
- `YOUTUBE_CHANNEL_URL` - Channel to ingest from

---

## What Gets Installed

### Files
- `/etc/systemd/system/drchaffee-ingest.service` - Service definition
- `/etc/systemd/system/drchaffee-ingest.timer` - Timer schedule (daily 2 AM)

### Schedule
- Runs daily at 2 AM
- Random delay 0-30 minutes (avoid exact 2 AM load)
- Persistent (runs on boot if missed)

---

## Daily Usage

### View Logs (Live)
```bash
sudo journalctl -u drchaffee-ingest -f
```

### Check Status
```bash
sudo systemctl status drchaffee-ingest.timer
```

### See Next Run Time
```bash
sudo systemctl list-timers drchaffee-ingest.timer
```

### Run Manually Now
```bash
sudo systemctl start drchaffee-ingest
```

### Test the Command Directly
```bash
# Test the ingestion command without systemd (Render Starter optimized)
cd /path/to/ask-dr-chaffee/backend
python3 scripts/ingest_youtube.py \
    --source yt-dlp \
    --days-back 2 \
    --limit 2 \
    --limit-unprocessed \
    --skip-shorts \
    --newest-first \
    --io-concurrency 2 \
    --asr-concurrency 1 \
    --db-concurrency 2 \
    --embedding-batch-size 32 \
    --dry-run  # Remove for actual run
```

### Disable Timer
```bash
sudo systemctl disable drchaffee-ingest.timer
sudo systemctl stop drchaffee-ingest.timer
```

---

## Troubleshooting

### Check Service Status
```bash
sudo systemctl status drchaffee-ingest
```

### View Recent Logs
```bash
sudo journalctl -u drchaffee-ingest -n 100
```

### View Logs Since Yesterday
```bash
sudo journalctl -u drchaffee-ingest --since yesterday
```

### Test Service Manually
```bash
sudo systemctl start drchaffee-ingest
sudo journalctl -u drchaffee-ingest -f
```

### Reload After Config Changes
```bash
sudo systemctl daemon-reload
sudo systemctl restart drchaffee-ingest.timer
```

---

## Configuration

### Change Schedule

Edit `/etc/systemd/system/drchaffee-ingest.timer`:

```ini
[Timer]
# Run at 3 AM instead of 2 AM
OnCalendar=*-*-* 03:00:00
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart drchaffee-ingest.timer
```

### Change Resource Limits

Edit `/etc/systemd/system/drchaffee-ingest.service`:

```ini
[Service]
# Increase memory limit
MemoryMax=16G

# Increase CPU quota
CPUQuota=800%
```

Then reload:
```bash
sudo systemctl daemon-reload
```

---

## Monitoring

### Check Last Run Status
```bash
systemctl status drchaffee-ingest
```

### View All Timer Runs
```bash
journalctl -u drchaffee-ingest --since "1 week ago"
```

### Get Run Statistics
```bash
systemctl show drchaffee-ingest.timer
```

---

## Uninstall

```bash
sudo systemctl disable drchaffee-ingest.timer
sudo systemctl stop drchaffee-ingest.timer
sudo rm /etc/systemd/system/drchaffee-ingest.service
sudo rm /etc/systemd/system/drchaffee-ingest.timer
sudo systemctl daemon-reload
```
