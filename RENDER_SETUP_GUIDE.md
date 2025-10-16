# 🚀 Render Setup Guide - Complete Configuration

## 📋 Services Overview

You should have **4 services** on Render:
1. ✅ **dr-chaffee-frontend** (Node) - Web app
2. ✅ **drchaffee-backend** (Python) - API utilities
3. ✅ **drchaffee-daily-ingest** (Python Cron) - Daily ingestion
4. ✅ **drchaffee-db** (PostgreSQL) - Database

---

## 1️⃣ Frontend Service (dr-chaffee-frontend)

### Build Settings
```
Name: dr-chaffee-frontend
Environment: Node
Region: Frankfurt (or your preferred region)
Branch: main
Root Directory: frontend

Build Command: npm install && npm run build
Start Command: npm start
```

### Environment Variables (8 total)
```
DATABASE_URL=<link from database>
NODE_ENV=production
OPENAI_API_KEY=sk-proj-your_actual_key
SUMMARIZER_MODEL=gpt-3.5-turbo
ANSWER_TOPK=50
ANSWER_STYLE_DEFAULT=concise
EMBEDDING_SERVICE_URL=https://drchaffee-backend.onrender.com
APP_PASSWORD=your_password
```

### Plan
- **Starter ($7/month)** - Recommended for production

---

## 2️⃣ Backend Service (drchaffee-backend)

### Build Settings
```
Name: drchaffee-backend
Environment: Python 3
Region: Frankfurt
Branch: main
Root Directory: (leave empty)

Build Command: pip install -r backend/requirements-render.txt
Start Command: uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT
```

### Environment Variables (2-4 total)
```
DATABASE_URL=<link from database>
HUGGINGFACE_HUB_TOKEN=hf_your_token_here
EMBEDDING_PROFILE=quality
EMBEDDING_DEVICE=cpu
```

### Plan
- **Starter ($7/month)**

---

## 3️⃣ Cron Job Service (drchaffee-daily-ingest) ⚠️ IMPORTANT

### Build Settings
```
Name: drchaffee-daily-ingest
Environment: Python 3
Region: Frankfurt
Branch: main
Root Directory: (leave empty)

Build Command: pip install -r backend/requirements-cron.txt

Start Command: python backend/scripts/bootstrap_voice_profile.py && python backend/scripts/scheduled_ingestion.py
```

**⚠️ CRITICAL:** The start command runs bootstrap FIRST, then ingestion!

### Schedule
```
0 2 * * *
```
(Runs daily at 2 AM UTC)

### Environment Variables (18 total)
```
DATABASE_URL=<link from database>
YOUTUBE_CHANNEL_URL=https://www.youtube.com/@anthonychaffeemd
HUGGINGFACE_HUB_TOKEN=hf_your_token_here
WHISPER_MODEL=base
WHISPER_COMPUTE_TYPE=int8
WHISPER_DEVICE=cpu
ENABLE_SPEAKER_ID=true
ASSUME_MONOLOGUE=true
CHAFFEE_MIN_SIM=0.62
VOICES_DIR=voices
EMBEDDING_PROFILE=quality
EMBEDDING_DEVICE=cpu
SKIP_SHORTS=true
NEWEST_FIRST=true
CLEANUP_AUDIO_AFTER_PROCESSING=true
IO_WORKERS=4
ASR_WORKERS=1
DB_WORKERS=4
```

**⚠️ IMPORTANT:** `VOICES_DIR=voices` (NOT `/etc/secrets`)

### Plan
- **Free** - Cron jobs are free!

---

## 4️⃣ Database (drchaffee-db)

### Settings
```
Name: drchaffee-db
Database Name: askdrchaffee
Region: Frankfurt
PostgreSQL Version: 17
```

### Plan
- **Starter ($7/month)**

---

## 🎯 Bootstrap Voice Profile - How It Works

### First Run (~15 minutes)
1. ✅ Bootstrap script checks if `voices/chaffee.json` exists
2. ❌ Not found → Downloads 10 seed videos
3. ✅ Extracts voice embeddings from each video
4. ✅ Builds comprehensive voice profile
5. ✅ Saves to `voices/chaffee.json`
6. ✅ Proceeds with normal ingestion

### Subsequent Runs (~5-10 minutes)
1. ✅ Bootstrap script checks if `voices/chaffee.json` exists
2. ✅ Found → Skips bootstrap
3. ✅ Proceeds directly to ingestion

### Seed Videos Used
The bootstrap uses 10 pure Chaffee monologue videos:
- High-quality audio
- No guests/interruptions
- Diverse speaking styles
- Total: ~3.5 hours of audio
- Result: ~10,000 voice embeddings

---

## 🔧 Setup Steps

### Step 1: Push Code to GitHub
```bash
git push origin main
```

### Step 2: Update Cron Job in Render

1. Go to **Render Dashboard** → **drchaffee-daily-ingest**
2. Click **Settings** tab
3. Update **Start Command**:
   ```bash
   python backend/scripts/bootstrap_voice_profile.py && python backend/scripts/scheduled_ingestion.py
   ```
4. Click **Environment** tab
5. Delete ALL existing environment variables
6. Add the 18 variables from above
7. **Make sure** `VOICES_DIR=voices` (NOT `/etc/secrets`)
8. Click **Manual Deploy** → **Deploy latest commit**

### Step 3: Monitor First Run

1. Go to **Logs** tab
2. Watch for bootstrap messages:
   ```
   INFO: Voice Profile Bootstrap
   INFO: ⚠️  Voice profile not found - building from seed videos...
   INFO: This will take ~15-20 minutes on first run
   INFO: [1/10] Processing: https://www.youtube.com/watch?v=...
   INFO: ✅ [1/10] Successfully enrolled: ...
   ...
   INFO: ✅ Bootstrap complete! Profile ready for ingestion
   ```

### Step 4: Verify Profile Built

After first run completes, check logs for:
```
INFO: ✅ Successfully created profile 'Chaffee' with 10000 embeddings
INFO:    Centroid dimensions: 192
INFO:    Audio sources: 10
INFO:    Total duration: 12864.4s
```

### Step 5: Test Normal Ingestion

Next scheduled run (or manual trigger) should show:
```
INFO: ✅ Voice profile already exists - skipping bootstrap
INFO: Starting ingestion...
```

---

## 🆘 Troubleshooting

### Bootstrap fails with "No embeddings extracted"
- **Cause:** yt-dlp download failed
- **Fix:** Check `HUGGINGFACE_HUB_TOKEN` is set correctly

### Bootstrap takes too long (>30 min)
- **Cause:** Slow CPU on free tier
- **Fix:** This is normal for first run, be patient

### "Profile not found" on every run
- **Cause:** `VOICES_DIR` pointing to wrong location
- **Fix:** Set `VOICES_DIR=voices` (not `/etc/secrets`)

### Ingestion fails with "Unknown speaker"
- **Cause:** Profile not built or corrupted
- **Fix:** Delete `voices/chaffee.json` and re-run bootstrap

---

## 💰 Total Monthly Cost

```
Frontend (Starter):        $7/month
Backend (Starter):         $7/month
Cron Job (Free):           $0/month
Database (Starter):        $7/month
─────────────────────────────────
Total:                    $21/month
```

---

## ✅ Checklist

- [ ] Code pushed to GitHub
- [ ] Frontend deployed with 8 env vars
- [ ] Backend deployed with 2-4 env vars
- [ ] Cron job updated with new start command
- [ ] Cron job has 18 env vars (including `VOICES_DIR=voices`)
- [ ] Manual deploy triggered on cron job
- [ ] First run completed successfully (~15 min)
- [ ] Voice profile built (check logs)
- [ ] Second run skips bootstrap (check logs)
- [ ] Custom domain configured (optional)

---

## 🎉 Success Criteria

After setup, you should see:
- ✅ Frontend accessible at `https://dr-chaffee-frontend.onrender.com`
- ✅ Backend API responding at `https://drchaffee-backend.onrender.com/health`
- ✅ Cron job runs daily at 2 AM UTC
- ✅ New videos automatically transcribed and added
- ✅ Speaker identification working (Chaffee vs Unknown)
- ✅ Search and answer features working on frontend

---

**Need help? Check the logs in Render dashboard!** 🚀
