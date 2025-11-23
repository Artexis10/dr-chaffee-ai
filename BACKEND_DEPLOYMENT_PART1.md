# Dr. Chaffee AI - Backend Technical Summary (Part 1/3)

**Last Updated:** November 21, 2025  
**Python Version:** 3.12.7  
**Framework:** FastAPI  
**Database:** PostgreSQL with pgvector  
**Deployment Target:** Coolify + Postgres on Hetzner VPS

---

## 1. PROJECT STRUCTURE

```
backend/
├── api/
│   ├── main.py                    # FastAPI application entry point
│   ├── tuning.py                  # AI tuning endpoints (/api/tuning/*)
│   └── embedding_service.py       # Embedding and search service
├── migrations/                     # Alembic database migrations
│   ├── env.py                     # Alembic environment configuration
│   ├── script.py.mako             # Migration template
│   ├── alembic.ini                # Alembic configuration
│   └── versions/                  # Individual migration files (17 total)
├── config/
│   └── embedding_models.json      # Embedding model configuration
├── scripts/
│   ├── common/                    # Shared utilities
│   ├── ingest_youtube.py          # Main YouTube ingestion pipeline
│   ├── ingest_zoom.py             # Zoom ingestion
│   ├── process_srt_files.py       # SRT file processing
│   ├── backfill_embeddings_parallel.py  # Parallel embedding backfill
│   └── [40+ other utility scripts]
├── requirements.txt               # Python dependencies
├── alembic.ini                    # Alembic configuration
├── .env.example                   # Environment variables template
├── .python-version                # Python version (3.12.7)
└── Dockerfile                     # Docker build configuration
```

**Main Application Entry Point:**
- **File:** `backend/api/main.py`
- **FastAPI App Instance:** `app = FastAPI(...)`
- **Startup Command:** `uvicorn api.main:app --host 0.0.0.0 --port 8000`

**Alembic Location:**
- **Config:** `backend/alembic.ini`
- **Environment:** `backend/migrations/env.py`
- **Versions:** `backend/migrations/versions/` (17 migration files)

---

## 2. FRAMEWORK & RUNTIME

**Framework:** FastAPI 0.104.1  
**Web Server:** Uvicorn 0.24.0  
**Python Version:** 3.12.7 (required - 3.11+ for pre-built wheels)

**Production Startup Command:**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Alternative with Gunicorn:**
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.main:app --bind 0.0.0.0:8000
```

**Docker Startup:**
```dockerfile
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Worker Configuration:**
- **Recommended Workers:** 4 (for 2-4 CPU cores)
- **Formula:** `workers = (2 × cpu_cores) + 1`
- **Note:** FastAPI with async handles concurrency well; worker count less critical than sync frameworks

---

## 3. DEPENDENCIES

### Full Requirements (requirements.txt - 74 lines)

```
# Core dependencies
psycopg2-binary>=2.9.9
alembic>=1.13.0
sqlalchemy>=2.0.07
python-dotenv==1.0.0
numpy==1.26.4
tqdm==4.66.1

# Web API dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.18
aiofiles==23.2.1
celery==5.3.4
redis==5.0.1

# YouTube transcript fetching
youtube-transcript-api==0.6.1
yt-dlp>=2023.11.16

# YouTube Data API
google-api-python-client==2.108.0
google-auth-httplib2==0.1.1
google-auth-oauthlib==1.1.0

# Text processing and embeddings
sentence-transformers>=2.7.0
transformers>=4.47.0

# Enhanced Audio transcription with latest Whisper models
faster-whisper>=1.0.2
ctranslate2>=4.4.0
torch>=2.2.0,<2.9.0
torchaudio>=2.2.0,<2.9.0
psutil>=5.9.0

# Advanced ASR with speaker identification
pyannote.audio>=4.0.0
speechbrain>=0.5.16
soundfile>=0.13.1
webvtt-py>=0.5.1

# Date/time parsing
isodate==0.6.1

# Async/concurrent processing
asyncio-throttle==1.0.2
apscheduler==3.10.4
aiohttp==3.9.1
aiohttp-socks==0.8.4

# Optional development tools
black==23.9.1
ruff==0.0.292
pyyaml>=6.0.3
pre-commit==3.4.00
beautifulsoup4>=4.12.0
lxml>=4.9.0

# Testing dependencies
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.1
pytest-asyncio>=0.21.1
pytest-timeout>=2.1.0
freezegun>=1.2.2
hypothesis>=6.82.0
```

### System-Level Dependencies (Ubuntu/Debian)

```bash
apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    ffmpeg \
    wget \
    curl \
    git \
    postgresql-client \
    build-essential \
    libcudnn9-dev-cuda-13 \
    nodejs \
    npm
```

### GPU Support (Optional)

For NVIDIA GPU acceleration:
```bash
# PyTorch with CUDA 12.1 support (matches NVIDIA CUDA 13.0 runtime)
pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu121
```

### CPU-Only Production

For Hetzner VPS without GPU:
```bash
# Use CPU-only PyTorch (smaller, faster install)
pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu
```

---

## 4. DATABASE DETAILS

### Database Engine
- **Type:** PostgreSQL 13+
- **Extensions:** pgvector (for vector embeddings)
- **Connection:** psycopg2-binary

### Connection Configuration

**Environment Variable:**
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/askdrchaffee
```

**Format:**
```
postgresql://[user]:[password]@[host]:[port]/[database]
```

**Example for Hetzner VPS:**
```
DATABASE_URL=postgresql://postgres:your_secure_password@db.example.com:5432/askdrchaffee
```

### Database Connection Code

```python
# From backend/api/main.py
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        os.getenv('DATABASE_URL'),
        cursor_factory=RealDictCursor
    )
```

### SQLAlchemy Configuration

**Not directly used in main.py** - The project uses raw psycopg2 for queries.  
**Alembic uses SQLAlchemy** for migrations only.

### Database Models Location

**Models are defined in:**
- `backend/scripts/common/transcript_common.py` - TranscriptSegment model
- `backend/migrations/versions/*.py` - Schema definitions via Alembic

### Key Tables

1. **sources** - YouTube videos/sources
   - `id` (UUID primary key)
   - `source_id` (TEXT, unique)
   - `title`, `description`, `url`
   - `source_type` (youtube, zoom, manual, etc.)
   - `created_at`, `updated_at`

2. **segments** - Transcript segments
   - `seg_id` (UUID primary key)
   - `source_id` (FK to sources)
   - `speaker` (TEXT)
   - `text` (TEXT)
   - `start_time`, `end_time` (FLOAT)
   - `embedding` (vector(384) or vector(1536) depending on model)
   - `created_at`, `updated_at`

3. **custom_instructions** - AI tuning instructions
   - `id` (UUID primary key)
   - `name`, `description`, `instructions` (TEXT)
   - `is_active` (BOOLEAN)
   - `created_at`, `updated_at`

4. **custom_instructions_history** - Version control
   - `id` (UUID primary key)
   - `instruction_id` (FK)
   - `version_number`, `instructions` (TEXT)
   - `created_at`

5. **answer_cache** - Cached LLM responses
   - `id` (UUID primary key)
   - `query_hash` (TEXT, unique)
   - `query` (TEXT)
   - `answer` (TEXT)
   - `model`, `created_at`, `expires_at`

### Vector Embedding Dimensions

**Current Configuration:**
- **Model:** BGE-Small-en-v1.5 (sentence-transformers)
- **Dimensions:** 384
- **Database Column:** `segments.embedding vector(384)`
- **Index Type:** ivfflat (for fast similarity search)

**To Change Embedding Model:**
1. Update `.env`:
   ```
   EMBEDDING_PROVIDER=sentence-transformers
   EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
   EMBEDDING_DIMENSIONS=384
   ```
2. Run migration:
   ```bash
   python -m alembic upgrade head
   ```
3. Backfill embeddings:
   ```bash
   python scripts/backfill_embeddings_parallel.py
   ```

---

## 5. ALEMBIC MIGRATIONS

### Configuration

**File:** `backend/alembic.ini`
```ini
[alembic]
script_location = migrations
sqlalchemy.url = driver://user:pass@localhost/dbname  # Overridden by env.py
```

**Environment Setup:** `backend/migrations/env.py`
```python
from dotenv import load_dotenv

# Load environment variables from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Override sqlalchemy.url from .env
database_url = os.getenv('DATABASE_URL')
if database_url:
    config.set_main_option('sqlalchemy.url', database_url)
```

### Migration Files (17 total)

1. **001_initial_schema.py** - Creates sources, segments, speaker_profiles tables
2. **002_fix_duplicates_and_speaker_labels.py** - Adds unique constraints
3. **003_update_embedding_dimensions.py** - Reads EMBEDDING_DIMENSIONS from .env
4. **004_add_video_type_classification.py** - Adds video_type column
5. **008_add_missing_segment_columns.py** - Adds missing columns
6. **009_create_answer_cache_table.py** - Creates answer caching table
7. **010_add_cascade_delete.py** - Adds cascade delete with batch processing
8. **011_remove_duplicate_video_id.py** - Removes duplicate video_id column
9. **012_custom_instructions.py** - Creates custom instructions tables
10. **015_fix_embedding_dimensions.py** - Dynamic dimension adjustment
11. **016_adaptive_embedding_index.py** - Optimizes vector index
12. **017_drop_segment_embeddings.py** - Cleanup

### Autogenerate Status

**Autogenerate:** NOT USED
- Reason: Complex custom migrations with batch processing
- Approach: Manual migration files with custom logic

### Running Migrations

**Apply all pending migrations:**
```bash
cd backend
python -m alembic upgrade head
```

**Apply specific migration:**
```bash
python -m alembic upgrade 012_custom_instructions
```

**Rollback one migration:**
```bash
python -m alembic downgrade -1
```

**Check current version:**
```bash
python -m alembic current
```

**View migration history:**
```bash
python -m alembic history
```

### Custom Migration Code Example

From `010_add_cascade_delete.py` (batch processing for large tables):
```python
def upgrade():
    # Batch processing to avoid timeout on managed PostgreSQL
    connection = op.get_bind()
    
    # Count total rows
    result = connection.execute(text("SELECT COUNT(*) FROM segments WHERE source_id IS NULL"))
    total_rows = result.scalar()
    
    # Process in 10,000 row batches
    batch_size = 10000
    for offset in range(0, total_rows, batch_size):
        connection.execute(text("""
            UPDATE segments SET source_id = (
                SELECT id FROM sources WHERE sources.source_id = segments.video_id
            )
            WHERE source_id IS NULL
            LIMIT :limit
        """), {"limit": batch_size})
```

---

## 6. ENVIRONMENT VARIABLES

### Required Variables

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/askdrchaffee
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=askdrchaffee

# YouTube Configuration
YOUTUBE_CHANNEL_URL=https://www.youtube.com/@anthonychaffeemd
YOUTUBE_API_KEY=your_api_key_here  # Optional, for full video listing

# Whisper ASR Configuration
WHISPER_MODEL=distil-large-v3
WHISPER_COMPUTE=int8_float16
WHISPER_VAD=false
BEAM_SIZE=5
TEMPERATURE=0.0
MAX_AUDIO_DURATION=3600
WHISPER_DEVICE=cuda  # or 'cpu' for production

# Concurrency Settings
IO_WORKERS=24
ASR_WORKERS=8
DB_WORKERS=12
BATCH_SIZE=1024

# Embedding Configuration
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSIONS=384
EMBEDDING_DEVICE=cuda

# Speaker Identification
ENABLE_SPEAKER_ID=true
CHAFFEE_MIN_SIM=0.62
GUEST_MIN_SIM=0.82

# API Security
ADMIN_API_KEY=your_admin_key_here
TUNING_PASSWORD=your_tuning_password_here

# Optional: OpenAI
OPENAI_API_KEY=your_openai_key_here
SUMMARIZER_MODEL=gpt-3.5-turbo

# Optional: HuggingFace
HUGGINGFACE_HUB_TOKEN=your_token_here
```

### Optional Variables

```bash
# Answer Mode
ANSWER_ENABLED=true
ANSWER_TOPK=40
ANSWER_TTL_HOURS=336

# Processing
SKIP_SHORTS=true
NEWEST_FIRST=true
CLEANUP_AUDIO_AFTER_PROCESSING=false

# Reranking
ENABLE_RERANKER=false
RERANK_TOP_K=200
RETURN_TOP_K=20

# App Password (frontend protection)
APP_PASSWORD=  # Leave empty to disable

# Performance
SKIP_WARMUP=false  # Set to 'true' on low-memory environments
```

### Environment Files

- **Development:** `.env` (git-ignored, create from `.env.example`)
- **Production:** `.env.production` (for GPU)
- **Production CPU:** `.env.production.cpu` (for CPU-only)

### Loading Environment Variables

```python
from dotenv import load_dotenv
import os

load_dotenv()  # Loads from .env in current directory
database_url = os.getenv('DATABASE_URL')
```

---

## 7. BACKGROUND WORKERS & SCHEDULED JOBS

### Celery Configuration

**Broker:** Redis (optional, for distributed tasks)
```python
# From requirements.txt
celery==5.3.4
redis==5.0.1
```

**Current Usage:**
- Background job tracking in `main.py`
- Job status stored in-memory dictionary: `processing_jobs: Dict[str, Dict[str, Any]]`

### Scheduled Jobs

**APScheduler Integration:**
```python
# From requirements.txt
apscheduler==3.10.4
```

**Available Scripts:**
- `backend/scripts/scheduled_ingestion.py` - Daily ingestion
- `backend/scripts/daily_ingest_wrapper.py` - Wrapper for scheduled runs
- `backend/scripts/monitor_ingestion.py` - Monitor pipeline status

**To Schedule Daily Ingestion:**
```bash
# Run in background
nohup python backend/scripts/daily_ingest_wrapper.py > ingestion.log 2>&1 &

# Or use cron (Linux/Mac)
0 2 * * * cd /path/to/backend && python scripts/daily_ingest_wrapper.py
```

### Background Tasks

**FastAPI Background Tasks:**
```python
from fastapi import BackgroundTasks

@app.post("/api/ingest/youtube")
async def ingest_youtube(background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(sync_youtube_videos, job_id, limit=100)
    return {"job_id": job_id}
```

---

## 8. SPECIAL FEATURES

### Static Files

**None configured** - Frontend served separately (Next.js at port 3000)

### File Uploads

**Endpoint:** `POST /api/upload`
- Accepts ZIP files with SRT/VTT transcripts
- Processes and stores in database
- Returns job status

### Logging

**Configuration:**
```python
import logging
logger = logging.getLogger(__name__)

# Logs to stdout (captured by Docker/systemd)
logger.info("Message")
logger.warning("Warning")
logger.error("Error")
```

### CORS Configuration

**Current Setup (main.py):**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**For Production (Hetzner VPS):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://www.yourdomain.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Authentication & Security

**API Key Authentication:**
```python
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin-secret-key")

@app.get("/api/admin/status")
async def get_status(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
```

**Tuning Dashboard Password:**
```python
TUNING_PASSWORD = os.getenv('TUNING_PASSWORD')

@router.post("/auth")
async def authenticate(request: PasswordRequest):
    if request.password != TUNING_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid password")
```

### Health Check

**Docker Health Check:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import yt_dlp; print('OK')" || exit 1
```

---

**Continue to BACKEND_DEPLOYMENT_PART2.md for API endpoints, deployment checklist, and production optimization.**
