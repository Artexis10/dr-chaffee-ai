# yt-dlp Auto-Update Feature

Automatic yt-dlp version checking and updating to prevent YouTube download failures.

## The Problem

YouTube frequently changes their player code to break downloaders. This causes errors like:

```
nsig extraction failed: Some formats may be missing
ERROR: Requested format is not available
Only images are available for download
```

## The Solution

The ingestion script now **automatically checks and updates yt-dlp** before processing videos.

## How It Works

### Automatic (Default Behavior)

```bash
# Just run normally - yt-dlp will auto-update if needed
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 100 --limit-unprocessed
```

**What happens:**
1. ✅ Checks yt-dlp version (once per 24 hours)
2. ✅ Updates if new version available
3. ✅ Continues with ingestion
4. ✅ Caches check to avoid spamming pip

### Force Update

```bash
# Force immediate update check (ignore 24h cache)
python backend/scripts/ingest_youtube.py --source yt-dlp --force-ytdlp-update --limit 100
```

### Skip Update

```bash
# Skip update check (use current version)
python backend/scripts/ingest_youtube.py --source yt-dlp --skip-ytdlp-update --limit 100
```

## Using Nightly Build

For the **absolute latest fixes** (bleeding edge):

```bash
# Install nightly build from GitHub
python backend/scripts/ingest_youtube.py --source yt-dlp --use-ytdlp-nightly --limit 100
```

**Nightly build:**
- ✅ Latest bug fixes (not yet in stable)
- ✅ Newest YouTube signature handling
- ⚠️  May have new bugs
- ⚠️  Not as well tested

### Manual Nightly Install

```powershell
# Install nightly build manually
.\backend\venv\Scripts\python.exe -m pip install --upgrade --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.tar.gz

# Or use the updater script directly
python backend/scripts/common/ytdlp_updater.py --nightly
```

## Command-Line Options

| Flag | Description |
|------|-------------|
| *(none)* | Auto-check once per 24h, update if needed |
| `--skip-ytdlp-update` | Skip version check entirely |
| `--force-ytdlp-update` | Force update check (ignore cache) |
| `--use-ytdlp-nightly` | Install nightly build from GitHub |

## Update Cache

The updater caches version checks to avoid spamming pip:

```
.cache/ytdlp_version_check.json
```

Contains:
- Last check timestamp
- Current version

**Cache expires:** 24 hours

## Standalone Updater

You can also use the updater standalone:

```bash
# Check and update
python backend/scripts/common/ytdlp_updater.py

# Force update
python backend/scripts/common/ytdlp_updater.py --force

# Install nightly
python backend/scripts/common/ytdlp_updater.py --nightly
```

## When to Use Nightly

Use nightly build when:
- ✅ Getting "nsig extraction failed" errors
- ✅ Stable version not working
- ✅ YouTube just changed something
- ✅ Need bleeding-edge fixes

Use stable version when:
- ✅ Everything working fine
- ✅ Want maximum stability
- ✅ Production environment

## Troubleshooting

### Still Getting Errors After Update

```bash
# Try nightly build
python backend/scripts/ingest_youtube.py --source yt-dlp --use-ytdlp-nightly
```

### Update Failed

```bash
# Manual update
.\backend\venv\Scripts\python.exe -m pip install --upgrade yt-dlp

# Or nightly
.\backend\venv\Scripts\python.exe -m pip install --upgrade --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.tar.gz
```

### Check Current Version

```bash
.\backend\venv\Scripts\python.exe -m yt_dlp --version
```

## Examples

### Daily Ingestion (Auto-Update)

```bash
# Runs daily, auto-updates yt-dlp if needed
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 50 --limit-unprocessed
```

### Emergency Fix (Nightly)

```bash
# YouTube broke downloads, need immediate fix
python backend/scripts/ingest_youtube.py --source yt-dlp --use-ytdlp-nightly --limit 10
```

### Production (Skip Updates)

```bash
# Production environment, don't auto-update
python backend/scripts/ingest_youtube.py --source yt-dlp --skip-ytdlp-update --limit 100
```

## How the Auto-Update Works

1. **Check if needed:** Only checks once per 24 hours (cached)
2. **Get current version:** Runs `yt-dlp --version`
3. **Check for updates:** Queries pip for outdated packages
4. **Update if needed:** Runs `pip install --upgrade yt-dlp`
5. **Cache result:** Saves timestamp to avoid re-checking

## Benefits

✅ **No more manual updates** - Happens automatically  
✅ **Prevents download failures** - Always up-to-date  
✅ **Smart caching** - Doesn't spam pip every run  
✅ **Flexible** - Can skip, force, or use nightly  
✅ **Transparent** - Logs what it's doing  

## Summary

**Default behavior:** Auto-updates yt-dlp once per day if needed.

**Most common usage:**
```bash
# Just works - no manual updates needed
python backend/scripts/ingest_youtube.py --source yt-dlp --limit 100 --limit-unprocessed
```

**Emergency fix:**
```bash
# Use nightly if stable version broken
python backend/scripts/ingest_youtube.py --source yt-dlp --use-ytdlp-nightly
```

**No more "nsig extraction failed" errors!** 🎯
