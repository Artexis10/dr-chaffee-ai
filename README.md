# Ask Dr. Chaffee

**Ask Dr. Chaffee** is an AI-powered transcript search app for Dr. Anthony Chaffee's content.  
It indexes transcripts from his **YouTube channel** and optional **Zoom recordings**, then makes them searchable with semantic embeddings and full-text queries.  
Instead of digging through hundreds of hours of video, you can jump straight to the exact clip where a topic is discussed.

---

## 🚀 **Quick Start**

### Recommended: Docker (Simplest)

**One-command setup:**
```bash
npm run docker:setup
```

Access at http://localhost:3000

📖 **See [DOCKER_SETUP.md](DOCKER_SETUP.md) for complete Docker guide**

### Alternative: Manual Setup

```bash
npm run setup
npm start
```

📖 **See [QUICKSTART.md](QUICKSTART.md) for manual setup guide**

---

## 🎥 **YouTube Ingestion Setup**

**Critical:** YouTube requires authentication to download videos. Follow this guide:

📖 **See [YOUTUBE_BOT_DETECTION_GUIDE.md](YOUTUBE_BOT_DETECTION_GUIDE.md) for setup**

**Quick setup (recommended):**
```bash
pip install bgutil-ytdlp-pot-provider
cd backend
py -3.11 scripts\ingest_youtube.py --source yt-dlp --limit 100 --newest-first
```

---

## 🔒 **Security: Git Hooks**

**After cloning, run:**
```bash
./scripts/setup-hooks.sh
```

This prevents accidentally committing secrets (API keys, passwords, etc.).

---

## ✨ Features

### 🔍 Enhanced Search Experience
- **Multi-term highlighting** with intelligent query parsing
- **Source filtering** with pills (All | YouTube | Zoom)
- **Year filtering** by publication date
- **Keyboard navigation** (↑↓ arrows, Enter to play, Shift+Enter for YouTube)
- **Loading skeleton states** for better UX
- **Cross-encoder reranking** for improved relevance (toggleable)

### 🎥 Video Integration
- **Embedded YouTube players** grouped by video
- **"Play Here" button** to seek to exact timestamps
- **Copy timestamp links** to clipboard for sharing
- **Segment clustering** merges clips within ±120 seconds
- **Source badges** distinguish YouTube vs Zoom content

### 🔧 Technical Features
- **Semantic & keyword search** with pgvector embeddings
- **Real-time transcript highlighting** of search terms
- **Mobile-responsive design** with optimized layouts
- **Accessibility support** (ARIA labels, focus states, keyboard nav)
- **Analytics events** for user interaction tracking

### 🛠 Developer Experience
- **Seed mode ingestion** (limited to 10 videos for development)
- **Pre-commit hooks** for code quality (Black, Ruff, Prettier, ESLint)
- **Node.js version pinning** with .nvmrc
- **Environment toggles** for features like reranking  

---

## 📂 Project Structure

```
ask-dr-chaffee/
├── frontend/ # Next.js frontend
│ ├── src/
│ │ ├── pages/ # Search page + API endpoint
│ │ └── components/ # UI components
│ ├── package.json
│ └── next.config.js
├── backend/ # Python ingestion pipeline
│ ├── scripts/
│ │ ├── ingest_youtube.py # YouTube transcript ingestion
│ │ ├── ingest_zoom.py # Zoom VTT ingestion
│ │ └── common/ # Shared utilities
│ └── requirements.txt
├── db/
│ └── schema.sql # Postgres + pgvector schema
├── docker-compose.yml # Database setup
├── Makefile # Dev & ingestion commands
├── .env.example # Environment template
└── README.md
```

## 🚀 Quick Start

### **Linux/macOS (with make)**

1. **Clone & Setup**
   ```bash
   git clone <repository-url>
   cd ask-dr-chaffee
   
   # Setup frontend env
   cp frontend/.env.example frontend/.env.local
   # Edit frontend/.env.local with your values
   
   # Setup backend env
   cp backend/.env.example backend/.env
   # Edit backend/.env with your values
   ```

2. **Install Dependencies**
   ```bash
   make install
   # OR manually:
   cd frontend && npm install
   cd ../backend && pip install -r requirements.txt
   ```

3. **Start Database**
   ```bash
   make db-up
   # Database will be available at localhost:5432
   ```

4. **Ingest Content (Development Mode)**
   ```bash
   make seed-youtube  # First 10 videos using API
   # OR for Enhanced ASR with speaker identification:
   # make seed-youtube-enhanced-asr
   # OR for full ingestion:
   # make backfill-youtube
   ```

5. **Start Frontend**
   ```bash
   make dev-frontend
   # OR: cd frontend && npm run dev
   # Available at http://localhost:3001
   ```

### **Windows 11 (PowerShell)**

1. **Clone & Setup**
   ```powershell
   git clone <repository-url>
   Set-Location ask-dr-chaffee
   
   # Setup frontend env
   copy frontend\.env.example frontend\.env.local
   # Edit frontend\.env.local with your values
   
   # Setup backend env
   copy backend\.env.example backend\.env
   # Edit backend\.env with your values
   ```

2. **Install Dependencies**
   ```powershell
   # Frontend
   Set-Location frontend
   npm install
   
   # Backend
   Set-Location ..\backend
   pip install -r requirements.txt
   Set-Location ..
   ```

3. **Start Database**
   ```powershell
   docker-compose up -d
   # Database will be available at localhost:5432
   ```

4. **Ingest Content (Development Mode)**
   ```powershell
   Set-Location backend
   python scripts/ingest_youtube_enhanced.py --source api --limit 10 --newest-first --skip-shorts
   # OR for Enhanced ASR with speaker identification:
   # python scripts/ingest_youtube_enhanced_asr.py --source api --limit 10 --enable-speaker-id
   ```

5. **Start Frontend**
   ```powershell
   Set-Location ..\frontend
   npm run dev
   # Available at http://localhost:3001
   ```

## 📋 Requirements

- **OS**: Windows 11 (or macOS/Linux)
- **Docker**: Docker Desktop for PostgreSQL
- **Python**: 3.8+ with pip
- **Node.js**: 20.x (see .nvmrc)
- **Git**: For pre-commit hooks (optional)

## 🏗 Architecture

### Frontend (Next.js)
- **Search Interface**: React components with TypeScript
- **Video Players**: Embedded YouTube iframes with seek controls
- **Filtering**: Source and year filters with URL state management
- **Accessibility**: ARIA labels, keyboard navigation, focus management

### Backend (Python)
- **Enhanced Ingestion Pipeline**: Tiered transcript fetching with cost optimization
- **Transcript Sources**: youtube-transcript-api → yt-dlp subtitles → Whisper fallback
- **Provenance Tracking**: Source quality ranking (owner > yt_caption > yt_dlp > whisper)
- **Cost Control**: Selective Whisper processing with duration limits and proxy support
- **Reranking**: Cross-encoder model for relevance improvement
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2

### Database (PostgreSQL + pgvector)
- **Sources Table**: Video metadata with provenance and access level tracking
- **Chunks Table**: Transcript segments with timestamps and embeddings
- **Provenance System**: Track transcript source quality for search ranking
- **Vector Search**: Semantic similarity with pgvector extension
- **Text Search**: Full-text search with PostgreSQL's built-in capabilities

## 🎯 Usage Guide

### Enhanced Transcript Pipeline Strategy

The ingestion system uses a **tiered transcript fetching approach** to minimize costs while maximizing reliability:

**Pipeline Order (Automatic Fallback Chain):**
1. **youtube-transcript-api** → Fast, free, official captions
2. **yt-dlp subtitle extraction** → Downloaded .vtt files with proxy support  
3. **Whisper transcription** → Audio-to-text as last resort (cost-controlled)

**Provenance Tracking & Search Ranking:**
- **owner**: Manual uploads by channel owner (highest priority)
- **yt_caption**: Official YouTube captions (high priority)
- **yt_dlp**: Downloaded subtitles via yt-dlp (medium priority)  
- **whisper**: AI-generated transcripts (lowest priority)

Search results are automatically ranked by relevance → provenance → recency → timestamp.

### Video Discovery Methods

**YouTube Data API Method (Default)**
- ✅ Rich metadata (view counts, exact timestamps)
- ✅ Faster bulk operations with ETag caching
- ✅ Official Google API with rate limiting
- ✅ Date filtering and content filtering
- ❌ Requires API key setup
- ❌ API quota limitations (10K units/day)

**yt-dlp Method (Fallback)**
- ✅ No API key required
- ✅ Works with any YouTube channel
- ✅ Robust scraping approach
- ✅ Proxy support for IP blocking
- ❌ Slower metadata collection
- ❌ Limited to public data

### Content Filtering

By default, the ingestion pipeline filters out certain types of content:

- **Live Streams**: Currently streaming videos are skipped
- **Upcoming Streams**: Scheduled but not yet live videos are skipped
- **Members-Only Content**: Videos restricted to channel members are skipped
- **Shorts**: Videos shorter than 120 seconds are skipped (with `--skip-shorts` flag)

You can include these content types with the following flags:

- `--include-live`: Include live streams
- `--include-upcoming`: Include upcoming streams
- `--include-members-only`: Include members-only content
- `--no-skip-shorts`: Include short videos

### Cost-Controlled Whisper Processing

The system implements **intelligent cost control** for Whisper transcription:

**Two-Phase Processing:**
1. **Normal Mode**: Processes videos with existing captions via youtube-transcript-api or yt-dlp
2. **Whisper Mode**: Separate `--whisper` flag processes videos marked `needs_whisper`

**Cost Control Features:**
- **Duration Limits**: Skip videos longer than `MAX_AUDIO_DURATION` (default: 1 hour)
- **Selective Processing**: Only transcribe videos without any captions
- **Proxy Support**: Use `YTDLP_PROXY` to bypass IP blocking for audio downloads
- **Batch Limits**: Control Whisper processing with `--whisper-limit` parameter

**Enhanced Audio Processing:**
- **Automatic preprocessing**: Convert to 16kHz mono WAV for optimal performance
- **VAD filtering**: Voice Activity Detection with 700ms silence threshold
- **Model selection**: Configurable model size (`small.en`, `medium.en`, etc.)
- **Cleanup**: Automatic temporary file removal after processing

**Quality & Tracking:**
- **Provenance tags**: All Whisper content marked with `whisper` provenance
- **Metadata storage**: Audio processing flags and model versions tracked
- **Error handling**: Robust error recovery with retry logic

### Search Features
- **Basic Search**: Type any query to find relevant transcript segments
- **Multi-term Queries**: Search for multiple terms, all highlighted in results
- **Filters**: Use source pills (All/YouTube/Zoom) and year dropdown
- **Keyboard Shortcuts**:
  - `↑/↓` arrows: Navigate between results
  - `Enter`: Play in embedded player
  - `Shift+Enter`: Open in YouTube

### Answer Mode
- **AI-Generated Answers**: Get concise answers based ONLY on Dr. Chaffee's recorded statements
- **Inline Citations**: Every sentence includes clickable citation chips linking to specific timestamps
- **Confidence Scoring**: Answers show confidence levels (High/Medium/Low) based on source quality and agreement
- **Smart Caching**: Answers are cached for 14 days with refresh capability
- **Source Transparency**: Expandable source list shows all referenced clips with timestamps

### Video Controls
- **"Play Here" Button**: Seeks embedded player to exact timestamp
- **"Copy Link" Button**: Copies timestamped YouTube URL to clipboard
- **"Watch on YouTube" Link**: Opens video in new tab

## ⚙️ Configuration

### Environment Files Structure

This monorepo uses **separate environment files** for frontend and backend:

```
dr-chaffee-ai/
├── .env.example              # Docker Compose & tooling only (NOT for apps)
├── frontend/
│   ├── .env.example          # Full frontend variable documentation
│   └── .env.local            # Your local frontend config (gitignored)
└── backend/
    ├── .env.example          # Full backend variable documentation
    └── .env                   # Your local backend config (gitignored)
```

### Frontend Setup (Next.js)

```bash
cd frontend
cp .env.example .env.local
# Edit .env.local with your values
```

**Key frontend variables:**
```bash
BACKEND_API_URL=http://localhost:8001   # Backend API URL
DATABASE_URL=postgresql://...            # PostgreSQL connection
OPENAI_API_KEY=sk-proj-...              # For answer generation
APP_PASSWORD=                            # Optional auth password
```

### Backend Setup (FastAPI)

```bash
cd backend
cp .env.example .env
# Edit .env with your values
```

**Key backend variables:**
```bash
DATABASE_URL=postgresql://...            # PostgreSQL connection
YOUTUBE_API_KEY=...                      # YouTube Data API v3
HUGGINGFACE_HUB_TOKEN=...               # For model downloads
OPENAI_API_KEY=sk-proj-...              # For answer generation
```

### Production (Coolify)

In production, set environment variables directly in Coolify:
- **Frontend app**: Set `BACKEND_API_URL`, `DATABASE_URL`, `OPENAI_API_KEY`, etc.
- **Backend app**: Set `DATABASE_URL`, `YOUTUBE_API_KEY`, `HUGGINGFACE_HUB_TOKEN`, etc.

See `frontend/.env.example` and `backend/.env.example` for complete variable lists.

### Available Commands

#### **Linux/macOS (make)**
```bash
# Development
make help                 # Show all available commands
make setup               # Initial project setup
make dev-frontend        # Start Next.js dev server

# Database
make db-up              # Start PostgreSQL
make db-down            # Stop PostgreSQL  
make db-reset           # Reset database (deletes data)

# Enhanced Transcript Pipeline (API + Tiered Fetching)
make ingest-youtube         # Full ingestion with new transcript pipeline
make seed-youtube          # Development mode (10 videos)
make sync-youtube          # Sync recent videos with date filtering
make whisper-missing       # Process videos marked for Whisper transcription
make fetch-subs            # Batch subtitle extraction via yt-dlp
make ingest-youtube-fallback # Use yt-dlp fallback for video discovery

# Enhanced ASR with Speaker Identification
make seed-youtube-enhanced-asr    # Development mode with Enhanced ASR (10 videos)
make ingest-youtube-enhanced-asr  # Full ingestion with Enhanced ASR and speaker ID
make sync-youtube-enhanced-asr    # Sync recent videos with Enhanced ASR

# Video Discovery
make list-youtube          # Dump channel videos to JSON
make list-youtube-api      # List videos using API

# Production Backfill Operations (Resumable)
make backfill-youtube         # Full channel backfill using API (default)
make backfill-youtube-fallback # Full channel backfill with yt-dlp fallback
make sync-youtube            # Incremental sync of recent videos

# Monitoring & Status
make ingest-status           # Show status breakdown and statistics  
make ingest-errors          # Display recent errors with details
make ingest-queue           # Check pending queue size

# Testing & Validation
make test-ingestion        # Dry run (no database writes)
make validate-transcripts  # Test transcript fetching
make ingestion-stats       # Show processing statistics

# Legacy
make ingest-zoom           # Zoom recordings ingestion

# Development Tools
pre-commit install      # Set up code quality hooks
nvm use                # Use Node.js version from .nvmrc
```

#### **Windows 11 (PowerShell)**

> **Note**: For easier use, load the PowerShell functions with `. .\scripts.ps1` and use the commands below.

```powershell
# Setup
copy .env.example .env                          # Create environment file
Set-Location frontend; npm install; Set-Location ..\backend; pip install -r requirements.txt; Set-Location ..

# Database
docker-compose up -d                           # Start PostgreSQL
docker-compose down                            # Stop PostgreSQL
docker-compose down -v; docker-compose up -d  # Reset database

# Using scripts.ps1 (recommended)
. .\scripts.ps1                               # Load all functions
Start-Database                                # Start PostgreSQL
Start-YouTubeSeed                             # Ingest 10 videos
Get-IngestionStatus                           # Check status

# Batch Processing (Production Scale)
Start-BatchIngestion -BatchSize 50 -BatchDelay 60 -Concurrency 4 -SkipShorts  # Process in batches
Resume-BatchIngestion                         # Resume interrupted batch
Get-BatchStatus                               # Check batch progress

# Monitoring & Optimization
Get-IngestionMetrics                          # Show detailed metrics
Get-ApiQuota                                  # Check API quota usage
Get-MonitoringReport                          # Generate full report
Optimize-Database                             # Run all optimizations
Vacuum-Database                               # Reclaim storage space
Reindex-Database                              # Rebuild indexes

# Testing
Test-LargeBatch                               # Test with 20 videos
Test-FullBatch                                # Test with 100 videos

# Manual Commands (without scripts.ps1)
# Ingestion (Enhanced Pipeline - API Default)
Set-Location backend
python scripts/ingest_youtube_enhanced.py --source api --concurrency 4 --newest-first --skip-shorts   # Full channel
python scripts/ingest_youtube_enhanced.py --source api --limit 10 --newest-first --skip-shorts         # Development mode
python scripts/ingest_youtube_enhanced.py --source api --since-published 2024-01-01                    # Date filtering
python scripts/ingest_youtube_enhanced.py --include-live --include-upcoming                           # Include live/upcoming streams
python scripts/ingest_youtube_enhanced.py --source yt-dlp --concurrency 4 --newest-first              # yt-dlp fallback

# Enhanced ASR with Speaker Identification
python scripts/ingest_youtube_enhanced_asr.py --source api --limit 10 --enable-speaker-id              # Development with speaker ID
python scripts/ingest_youtube_enhanced_asr.py --source api --enable-speaker-id --concurrency 4         # Full ingestion with speaker ID
python scripts/ingest_youtube_enhanced_asr.py --source local --from-files ./audio --enable-speaker-id  # Local files with speaker ID
python scripts/ingest_youtube_enhanced_asr.py --source api --enable-speaker-id --chaffee-min-sim 0.60  # Custom similarity threshold

# Testing & Validation  
python scripts/ingest_youtube_enhanced.py --source yt-dlp --limit 5 --dry-run                         # Dry run
python scripts/common/transcript_fetch.py dQw4w9WgXcQ                                                 # Test transcript
python scripts/common/database_upsert.py --stats                                                      # Show statistics

# Frontend Development
Set-Location ..\frontend; npm run dev         # Start Next.js dev server

# Video Discovery
python scripts/common/list_videos_yt_dlp.py "https://www.youtube.com/@anthonychaffeemd" --output data/videos.json
python scripts/common/list_videos_api.py "https://www.youtube.com/@anthonychaffeemd" --limit 50
```

## 🔍 Search Tips

- **Exact Phrases**: Use quotes for exact matches: `"carnivore diet"`
- **Multiple Topics**: Search for related terms: `thyroid autoimmune inflammation`
- **Filter by Source**: Use source pills to focus on YouTube or Zoom content
- **Filter by Year**: Use year dropdown to find recent or historical content
- **Copy Links**: Use "Copy Link" to share specific moments with others

### Answer Mode Usage
- **Direct Questions**: Ask specific questions like "What does Dr. Chaffee say about seed oils?"
- **Medical Topics**: Query about specific health conditions or dietary advice
- **Citation Navigation**: Click citation chips like [clip 12:15] to jump to exact video moments
- **Source Verification**: Expand "See sources" to review all referenced clips
- **Cache Refresh**: Add `?refresh=1` to URL to bypass cache and get updated answers
- **Confidence Levels**: 
  - **High (80%+)**: Strong consensus across multiple recent clips
  - **Medium (60-79%)**: Good evidence with some gaps or conflicts
  - **Low (<60%)**: Limited or conflicting evidence

## 🔧 Advanced Usage

### CLI Examples

#### Basic Enhanced Pipeline
```bash
# Basic ingestion with API (default)
python backend/scripts/ingest_youtube_enhanced.py --source api --limit 50 --skip-shorts

# Date-filtered ingestion
python backend/scripts/ingest_youtube_enhanced.py --since-published 2024-01-01

# Content filtering options (live streams, upcoming streams, and members-only are skipped by default)
python backend/scripts/ingest_youtube_enhanced.py --include-live --include-upcoming --include-members-only

# Use yt-dlp fallback
python backend/scripts/ingest_youtube_enhanced.py --source yt-dlp --limit 50

# Process from pre-dumped JSON (yt-dlp only)
python backend/scripts/ingest_youtube_enhanced.py --source yt-dlp --from-json backend/data/videos.json

# Force Whisper transcription with larger model
python backend/scripts/ingest_youtube_enhanced.py --force-whisper --whisper-model medium.en

# Dry run to preview processing
python backend/scripts/ingest_youtube_enhanced.py --dry-run --limit 10
```

#### Enhanced ASR with Speaker Identification
```bash
# Basic Enhanced ASR ingestion
python backend/scripts/ingest_youtube_enhanced_asr.py --source api --limit 10 --enable-speaker-id

# Production Enhanced ASR processing
python backend/scripts/ingest_youtube_enhanced_asr.py --source api --enable-speaker-id --concurrency 4

# Enhanced ASR with custom speaker threshold
python backend/scripts/ingest_youtube_enhanced_asr.py --source api --enable-speaker-id --chaffee-min-sim 0.60

# Enhanced ASR with local files
python backend/scripts/ingest_youtube_enhanced_asr.py --source local --from-files ./audio_files --enable-speaker-id

# Enhanced ASR with HuggingFace diarization
python backend/scripts/ingest_youtube_enhanced_asr.py --source api --enable-speaker-id --use-advanced-diarization

# Enhanced ASR dry run
python backend/scripts/ingest_youtube_enhanced_asr.py --source api --limit 5 --enable-speaker-id --dry-run
```

#### Voice Enrollment for Speaker Identification
```bash
# Enroll Dr. Chaffee's voice profile
python backend/scripts/asr_cli.py enroll --name Chaffee --audio voice_samples/*.wav --min-duration 60

# Enroll from YouTube URLs
python backend/scripts/asr_cli.py enroll --name Chaffee --url "https://www.youtube.com/watch?v=VIDEO_ID"

# Test speaker identification
python backend/scripts/asr_cli.py transcribe test_audio.wav --enable-speaker-id --format json
```

### Windows: Install FFmpeg
This project requires FFmpeg for audio extraction and Whisper transcription.

On Windows 11, the simplest way is with **winget** (built-in):

```powershell
winget install Gyan.FFmpeg
```

### Windows: Using PowerShell Script

For easier management on Windows 11, use the included PowerShell script:

```powershell
# Load all functions
. .\scripts.ps1

# Show all available commands
Show-Help

# Common workflow
Start-Database                # Start PostgreSQL
Start-BatchIngestion          # Process videos in batches
Get-BatchStatus               # Monitor progress
Get-IngestionMetrics         # View detailed metrics
```

### Pipeline Stages
1. **Video Discovery**: List all videos from channel
2. **Transcript Fetching**: Try YouTube captions → fallback to Whisper
3. **Text Processing**: Chunk into ~45-second segments
4. **Embedding Generation**: Create 384-dimensional vectors
5. **Database Storage**: Upsert sources and chunks
6. **State Tracking**: Monitor progress with ingest_state table

### Error Recovery
- **Automatic Retries**: Failed videos retry up to 3 times
- **Resume Capability**: Restart ingestion without losing progress
- **Status Tracking**: Monitor pipeline with `make ingestion-stats` or `Get-IngestionStatus` (Windows)
- **Selective Processing**: Skip completed videos automatically
- **Batch Checkpointing**: Resume from last checkpoint with `make batch-resume` or `Resume-BatchIngestion` (Windows)

## 📚 Additional Documentation

- **[Backend Organization](BACKEND_ORGANIZATION.md)** - Cleaned-up backend structure and guidelines
- **[yt-dlp Usage Guide](YTDLP_USAGE.md)** - Comprehensive yt-dlp configuration and troubleshooting
- **[Enhanced ASR README](ENHANCED_ASR_README.md)** - Speaker identification and voice enrollment
- **[Production Deployment](PRODUCTION_DEPLOYMENT.md)** - Production deployment strategies
- **[Proxy Solutions](PROXY_SOLUTIONS_ANALYSIS.md)** - Proxy configuration for YouTube access

## ⚠️ Important Notes

- **Educational Content**: All content is for educational purposes only
- **Medical Disclaimer**: Always consult healthcare providers for medical advice
- **Official Channel**: Visit [Dr. Chaffee's YouTube](https://www.youtube.com/@anthonychaffeemd) for latest content
- **API Quotas**: YouTube Data API has daily quotas - monitor usage
- **Storage Requirements**: ~1GB per 1000 videos (including embeddings)
- **Processing Time**: Allow 2-5 minutes per video for full pipeline
- **Enhanced ASR Requirements**: GPU recommended for optimal speaker identification performance
