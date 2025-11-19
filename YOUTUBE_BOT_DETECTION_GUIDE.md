# YouTube Bot Detection & yt-dlp Authentication Guide

**Last Updated:** November 19, 2025  
**Status:** Critical for ingestion pipeline  
**Severity:** Without proper auth, 100% of downloads will fail with "Sign in to confirm you're not a bot"

---

## Quick Start (Recommended)

### Option 1: PO Token Provider Plugin (EASIEST - NO MANUAL SETUP)

This is the **official yt-dlp solution** for 2024-2025. It automatically generates tokens to bypass bot detection.

**Installation (one-time):**
```bash
pip install bgutil-ytdlp-pot-provider
```

**That's it.** No code changes needed. yt-dlp will auto-detect and use it.

**Verify it works:**
```bash
cd backend
py -3.11 scripts\ingest_youtube.py --source yt-dlp --limit 10 --newest-first
```

If you see downloads starting (not "Sign in to confirm you're not a bot" errors), it's working.

---

## Why This Matters

YouTube has **significantly tightened bot detection** as of late 2024-2025:
- ❌ OAuth login no longer works
- ❌ Simple cookies get rotated/invalidated
- ❌ Guest sessions hit rate limits immediately
- ✅ PO Token Provider is the **official recommended solution**

Without proper authentication, **all 584+ videos will fail to download**.

---

## Option 2: Manual Cookies (If Plugin Fails)

### Why This Is Harder

YouTube rotates cookies frequently on open browser tabs. To export working cookies, you must:
1. Use **incognito/private mode** (prevents rotation)
2. Navigate to a specific URL that doesn't trigger rotation
3. Export immediately before closing the window

### Step-by-Step

**1. Open Firefox/Chrome in Incognito/Private mode**
- Firefox: `Ctrl+Shift+P`
- Chrome: `Ctrl+Shift+N`

**2. Sign in to YouTube**
- Use your account or a throwaway account
- Complete any 2FA if prompted

**3. Navigate to robots.txt (CRITICAL)**
```
https://www.youtube.com/robots.txt
```
This URL doesn't trigger cookie rotation. Keep this tab open.

**4. Export cookies using DevTools**

**Firefox:**
- Press `F12` → `Storage` tab
- Expand `Cookies` → `https://www.youtube.com`
- Right-click → Copy all (or manually note these values):
  - `VISITOR_INFO1_LIVE` (required)
  - `CONSENT` (required)
  - `PREF` (optional)
  - `LOGIN_INFO` (if logged in)
  - `SID`, `HSID`, `SSID`, `APISID`, `SAPISID` (if logged in)

**Chrome:**
- Press `F12` → `Application` tab
- Expand `Cookies` → `https://www.youtube.com`
- Right-click → Copy all (or manually note values)

**5. Create `cookies.txt` in Netscape format**

Create file: `c:\Users\hugoa\Desktop\dr-chaffee-ai\cookies.txt`

```
# Netscape HTTP Cookie File
# This is a generated file!  Do not edit.

.youtube.com	TRUE	/	TRUE	0	VISITOR_INFO1_LIVE	<your_visitor_id_here>
.youtube.com	TRUE	/	TRUE	0	CONSENT	<your_consent_value_here>
.youtube.com	TRUE	/	TRUE	0	PREF	<your_pref_value_here>
```

**Example (DO NOT USE - just for format reference):**
```
.youtube.com	TRUE	/	TRUE	0	VISITOR_INFO1_LIVE	CgtZVkFCQkFBQkFBQQ%3D%3D
.youtube.com	TRUE	/	TRUE	0	CONSENT	YES+cb.20231201-00-p0.en+FX+123
.youtube.com	TRUE	/	TRUE	0	PREF	tz%3DAmerica.New_York
```

**6. Close incognito window immediately**
- Do NOT browse with this session again
- Closing it prevents cookie rotation

**7. Test the cookies**
```bash
cd backend
py -3.11 scripts\ingest_youtube.py --source yt-dlp --limit 10 --newest-first
```

If downloads start (not "Sign in to confirm" errors), cookies are valid.

---

## Option 3: Rate Limiting Only (TEMPORARY - Will Eventually Fail)

If neither Option 1 nor 2 work, you can try aggressive rate limiting:

**Modify `backend/scripts/common/enhanced_transcript_fetch.py` lines 443-451:**

```python
cmd.extend([
    '-4',  # Force IPv4
    '--retry-sleep', '10',  # Increased from 5
    '--retries', '20',  # Increased from 15
    '--fragment-retries', '20',  # Increased from 15
    '--sleep-requests', '5',  # Increased from 3
    '--min-sleep-interval', '5',  # Increased from 2
    '--max-sleep-interval', '10',  # Increased from 5
    '--socket-timeout', '30',
    '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    '--referer', 'https://www.youtube.com/',
])
```

⚠️ **This will slow ingestion significantly** and may still fail after ~100 videos.

---

## Troubleshooting

### "Sign in to confirm you're not a bot" Error

**Cause:** No valid authentication method  
**Solution:**
1. Try Option 1 (PO Token Plugin) first
2. If that fails, try Option 2 (Manual Cookies)
3. If cookies fail, they're expired - re-export fresh ones

### "Empty audio file" or "partial file" Errors

**Cause:** Authentication succeeded but download is incomplete  
**Solution:** This is handled by the fallback chain in `enhanced_transcript_fetch.py`:
- Tries web client first
- Falls back to android client
- Falls back to default
- Validates file size (rejects < 50 KiB stubs)

### Downloads Start Then Stop

**Cause:** Rate limit hit or session invalidated  
**Solution:**
1. If using cookies: Export fresh cookies (old ones rotated)
2. If using plugin: Wait 1-2 hours for rate limit to reset
3. Add more aggressive rate limiting (Option 3)

---

## How to Set Up for Fresh Project Install

### Quick Setup (Recommended)

```bash
# 1. Install PO Token provider (one-time)
pip install bgutil-ytdlp-pot-provider

# 2. Start ingestion
cd backend
py -3.11 scripts\ingest_youtube.py --source yt-dlp --limit 100 --newest-first
```

### With Manual Cookies

```bash
# 1. Export cookies.txt (see Option 2 above)
# 2. Place in project root: c:\Users\hugoa\Desktop\dr-chaffee-ai\cookies.txt

# 3. Start ingestion
cd backend
py -3.11 scripts\ingest_youtube.py --source yt-dlp --limit 100 --newest-first
```

---

## Key Implementation Details

### Fallback Chain (Already Implemented)

File: `backend/scripts/common/enhanced_transcript_fetch.py` (lines 409-508)

The download method tries three strategies in order:
1. **Web client** (`youtube:player_client=web`) - Most reliable
2. **Android client** (`youtube:player_client=android`) - Fallback
3. **Default** (no client) - Last resort

Each strategy validates file size (rejects < 50 KiB stubs).

### Rate Limiting (Already Configured)

Default settings in `enhanced_transcript_fetch.py`:
- `--sleep-requests 3` - Sleep between requests
- `--retries 15` - Retry failed downloads
- `--min-sleep-interval 2` - Minimum delay
- `--max-sleep-interval 5` - Maximum delay

These can be increased if hitting rate limits (see Option 3).

---

## References

- **yt-dlp Official Wiki:** https://github.com/yt-dlp/yt-dlp/wiki/extractors#youtube
- **PO Token Guide:** https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide
- **Common YouTube Errors:** https://github.com/yt-dlp/yt-dlp/wiki/FAQ#youtube-errors

---

## When to Use This Guide

- ✅ Setting up ingestion for the first time
- ✅ Ingestion fails with "Sign in to confirm you're not a bot"
- ✅ Downloads work briefly then stop
- ✅ Setting up on a new machine
- ✅ Cookies expire and need refreshing

---

## Summary

| Method | Setup Time | Maintenance | Reliability | Recommended |
|--------|-----------|-------------|-------------|-------------|
| PO Token Plugin | 1 min | None | 95%+ | ✅ YES |
| Manual Cookies | 5 min | Re-export every 2-4 weeks | 90%+ | If plugin fails |
| Rate Limiting Only | 0 min | Adjust as needed | 60% | Last resort |

**Recommendation:** Start with PO Token Plugin. If it fails, fall back to manual cookies.
