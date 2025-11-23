# Complete Environment Variables Reference

**Dr. Chaffee AI Backend - Production Deployment**

---

## Required Environment Variables

| Name | Used In | Purpose | Required? | Default | Type |
|------|---------|---------|-----------|---------|------|
| `DATABASE_URL` | api/main.py, api/tuning.py, api/embedding_service.py, migrations/env.py, scripts/ingest_youtube.py | PostgreSQL connection string with pgvector extension | ✅ YES | None | URL (postgresql://user:pass@host:5432/db) |
| `ADMIN_API_KEY` | api/main.py (line 94) | Bearer token for admin endpoints (/api/admin/*) | ✅ YES | "admin-secret-key" | String (32+ chars recommended) |
| `TUNING_PASSWORD` | api/tuning.py (line 30) | Password for AI tuning dashboard (/api/tuning/*) | ✅ YES | None | String (32+ chars recommended) |
| `WHISPER_MODEL` | scripts/ingest_youtube.py, scripts/common/enhanced_asr_config.py | Whisper ASR model: distil-large-v3, large-v3, base, tiny | ⚠️ OPTIONAL | distil-large-v3 | String (model name) |
| `WHISPER_DEVICE` | scripts/common/enhanced_asr_config.py | Device for Whisper: cuda (GPU) or cpu | ⚠️ OPTIONAL | cuda | String (cuda/cpu) |
| `WHISPER_COMPUTE` | scripts/common/enhanced_asr_config.py | Quantization: int8_float16 (GPU), int8 (CPU) | ⚠️ OPTIONAL | int8_float16 | String |
| `EMBEDDING_PROVIDER` | api/main.py (line 106), scripts/common/embeddings.py (line 55) | Embedding provider: sentence-transformers, openai, nomic, huggingface | ⚠️ OPTIONAL | sentence-transformers | String |
| `EMBEDDING_MODEL` | api/main.py (line 107), scripts/common/embeddings.py (line 76), api/tuning.py (lines 242-244) | Model name (e.g., BAAI/bge-small-en-v1.5, Alibaba-NLP/gte-Qwen2-1.5B-instruct) | ⚠️ OPTIONAL | BAAI/bge-small-en-v1.5 | String (HuggingFace model ID) |
| `EMBEDDING_DIMENSIONS` | scripts/common/embeddings.py (line 60, 64, 70, 77), migrations/versions/015_fix_embedding_dimensions.py | Vector dimensions: 384 (BGE-Small), 768 (Nomic), 1536 (GTE-Qwen2, OpenAI) | ⚠️ OPTIONAL | 384 | Integer |
| `EMBEDDING_DEVICE` | scripts/common/embeddings.py | Device for embeddings: cuda (GPU) or cpu | ⚠️ OPTIONAL | cuda | String (cuda/cpu) |
| `EMBEDDING_PROFILE` | scripts/common/embeddings.py (line 31) | Profile: quality (GTE-Qwen2-1.5B) or speed (BGE-Small) | ⚠️ OPTIONAL | quality | String (quality/speed) |
| `YOUTUBE_CHANNEL_URL` | scripts/ingest_youtube.py (line 324) | YouTube channel URL to ingest | ⚠️ OPTIONAL | https://www.youtube.com/@anthonychaffeemd | URL |
| `YOUTUBE_API_KEY` | scripts/ingest_youtube.py (line 333), api/tuning.py (line 923) | YouTube Data API key for full video listing | ⚠️ OPTIONAL | None | String (API key from Google Cloud) |
| `OPENAI_API_KEY` | scripts/common/embeddings.py (line 95), api/tuning.py (line 362) | OpenAI API key for embeddings or LLM | ⚠️ OPTIONAL | None | String (sk-proj-...) |
| `NOMIC_API_KEY` | scripts/common/embeddings.py (line 65) | Nomic API key for embeddings (if using nomic provider) | ⚠️ OPTIONAL (required if EMBEDDING_PROVIDER=nomic) | None | String |
| `HUGGINGFACE_API_KEY` | scripts/common/embeddings.py (line 71) | HuggingFace API key (if using huggingface provider) | ⚠️ OPTIONAL (required if EMBEDDING_PROVIDER=huggingface) | None | String |
| `HUGGINGFACE_HUB_TOKEN` | .env.example | HuggingFace token for downloading models | ⚠️ OPTIONAL | None | String (hf_...) |
| `SUMMARIZER_MODEL` | api/tuning.py (line 362) | LLM model for answer generation: gpt-4-turbo, gpt-4, gpt-3.5-turbo | ⚠️ OPTIONAL | gpt-4-turbo | String |
| `SUMMARIZER_TEMPERATURE` | api/tuning.py (line 363) | Temperature for LLM: 0.0-1.0 (0=deterministic, 1=creative) | ⚠️ OPTIONAL | 0.1 | Float |
| `SUMMARIZER_MAX_TOKENS` | api/tuning.py (line 364) | Max tokens for LLM response | ⚠️ OPTIONAL | 2000 | Integer |

---

## Concurrency & Performance Settings

| Name | Used In | Purpose | Required? | Default | Type |
|------|---------|---------|-----------|---------|------|
| `IO_WORKERS` | scripts/ingest_youtube.py (line 304) | Concurrent download workers (GPU: 24, CPU: 4) | ⚠️ OPTIONAL | 24 | Integer |
| `ASR_WORKERS` | scripts/ingest_youtube.py (line 306) | Concurrent Whisper workers (GPU: 8, CPU: 1) | ⚠️ OPTIONAL | 8 | Integer |
| `DB_WORKERS` | scripts/ingest_youtube.py (line 308) | Concurrent embedding/DB workers (GPU: 12, CPU: 4) | ⚠️ OPTIONAL | 12 | Integer |
| `BATCH_SIZE` | scripts/ingest_youtube.py (line 310) | Embedding batch size (GPU: 1024, CPU: 256) | ⚠️ OPTIONAL | 1024 | Integer |
| `WHISPER_PARALLEL_MODELS` | .env.example | Number of parallel Whisper models (1 recommended for RTX 5080) | ⚠️ OPTIONAL | 1 | Integer (1-2) |

---

## Segmentation & Quality Settings

| Name | Used In | Purpose | Required? | Default | Type |
|------|---------|---------|-----------|---------|------|
| `SEGMENT_MIN_CHARS` | .env.example | Minimum characters per segment for RAG | ⚠️ OPTIONAL | 1100 | Integer |
| `SEGMENT_MAX_CHARS` | .env.example | Maximum characters per segment | ⚠️ OPTIONAL | 1400 | Integer |
| `SEGMENT_MAX_GAP_SECONDS` | .env.example | Max gap between sentences to merge (seconds) | ⚠️ OPTIONAL | 5.0 | Float |
| `SEGMENT_MAX_MERGE_DURATION` | .env.example | Maximum duration of merged segment (seconds) | ⚠️ OPTIONAL | 120.0 | Float |
| `SEGMENT_HARD_CAP_CHARS` | .env.example | Absolute maximum segment length | ⚠️ OPTIONAL | 1800 | Integer |
| `SEGMENT_OVERLAP_CHARS` | .env.example | Overlap between segments (220-300 recommended) | ⚠️ OPTIONAL | 250 | Integer |

---

## Speaker Identification Settings

| Name | Used In | Purpose | Required? | Default | Type |
|------|---------|---------|-----------|---------|------|
| `ENABLE_SPEAKER_ID` | .env.example, scripts/common/enhanced_asr_config.py | Enable speaker diarization | ⚠️ OPTIONAL | true | Boolean (true/false) |
| `CHAFFEE_MIN_SIM` | scripts/common/enhanced_asr_config.py (line 187) | Similarity threshold for Dr. Chaffee identification | ⚠️ OPTIONAL | 0.62 | Float (0.0-1.0) |
| `GUEST_MIN_SIM` | scripts/common/enhanced_asr_config.py (line 188) | Similarity threshold for guest identification | ⚠️ OPTIONAL | 0.82 | Float (0.0-1.0) |
| `ATTR_MARGIN` | scripts/common/enhanced_asr_config.py (line 189) | Attribution margin for speaker assignment | ⚠️ OPTIONAL | 0.05 | Float |
| `OVERLAP_BONUS` | scripts/common/enhanced_asr_config.py (line 190) | Bonus for overlapping speaker segments | ⚠️ OPTIONAL | 0.03 | Float |
| `ASSUME_MONOLOGUE` | scripts/common/enhanced_asr_config.py (line 193) | Assume single speaker (3x speedup) | ⚠️ OPTIONAL | true | Boolean |
| `VOICES_DIR` | scripts/common/enhanced_asr_config.py (line 200) | Directory for voice profiles | ⚠️ OPTIONAL | voices | String (path) |
| `MIN_SPEAKER_DURATION` | scripts/common/enhanced_asr_config.py (line 203) | Minimum speaker duration in seconds | ⚠️ OPTIONAL | 3.0 | Float |
| `MIN_DIARIZATION_CONFIDENCE` | scripts/common/enhanced_asr_config.py (line 204) | Minimum diarization confidence | ⚠️ OPTIONAL | 0.5 | Float |

---

## Quality Assurance Settings

| Name | Used In | Purpose | Required? | Default | Type |
|------|---------|---------|-----------|---------|------|
| `QA_LOW_LOGPROB` | scripts/common/enhanced_asr_config.py (line 111) | Low confidence detection threshold (avg_logprob) | ⚠️ OPTIONAL | -0.35 | Float |
| `QA_LOW_COMPRESSION` | scripts/common/enhanced_asr_config.py (line 112) | Low confidence compression ratio threshold | ⚠️ OPTIONAL | 2.4 | Float |
| `QA_TWO_PASS` | scripts/common/enhanced_asr_config.py (line 113) | Enable two-pass retry for low confidence | ⚠️ OPTIONAL | true | Boolean |
| `QA_RETRY_BEAM` | scripts/common/enhanced_asr_config.py (line 114) | Beam size for retry pass | ⚠️ OPTIONAL | 8 | Integer |
| `QA_RETRY_TEMPS` | scripts/common/enhanced_asr_config.py (line 117) | Retry temperatures (comma-separated) | ⚠️ OPTIONAL | 0.0,0.2,0.4,0.6 | String (CSV floats) |

---

## Alignment & Diarization Settings

| Name | Used In | Purpose | Required? | Default | Type |
|------|---------|---------|-----------|---------|------|
| `ALIGN_WORDS` | scripts/common/enhanced_asr_config.py (line 150) | Enable word-level alignment | ⚠️ OPTIONAL | true | Boolean |
| `DIARIZE` | scripts/common/enhanced_asr_config.py (line 151) | Enable speaker diarization | ⚠️ OPTIONAL | false | Boolean |
| `DIARIZE_MODEL` | scripts/common/enhanced_asr_config.py (line 152) | Diarization model | ⚠️ OPTIONAL | pyannote/speaker-diarization-community-1 | String |
| `MIN_SPEAKERS` | scripts/common/enhanced_asr_config.py (line 154) | Minimum number of speakers | ⚠️ OPTIONAL | None | Integer |
| `MAX_SPEAKERS` | scripts/common/enhanced_asr_config.py (line 158) | Maximum number of speakers | ⚠️ OPTIONAL | None | Integer |
| `PYANNOTE_CLUSTERING_THRESHOLD` | .env.example | Clustering threshold for pyannote (lower = more sensitive) | ⚠️ OPTIONAL | 0.3 | Float |

---

## Processing Settings

| Name | Used In | Purpose | Required? | Default | Type |
|------|---------|---------|-----------|---------|------|
| `SKIP_SHORTS` | scripts/ingest_youtube.py (line 314) | Skip YouTube Shorts | ⚠️ OPTIONAL | true | Boolean |
| `NEWEST_FIRST` | scripts/ingest_youtube.py (line 316) | Process newest videos first | ⚠️ OPTIONAL | true | Boolean |
| `MAX_AUDIO_DURATION` | scripts/ingest_youtube.py (line 320) | Maximum audio duration in seconds (0 = unlimited) | ⚠️ OPTIONAL | 3600 | Integer |
| `CLEANUP_AUDIO_AFTER_PROCESSING` | .env.example | Delete audio files after processing | ⚠️ OPTIONAL | false | Boolean |
| `STORE_AUDIO_LOCALLY` | .env.example | Store audio files permanently | ⚠️ OPTIONAL | false | Boolean |
| `UNKNOWN_LABEL` | scripts/common/enhanced_asr_config.py (line 195) | Label for unknown speakers | ⚠️ OPTIONAL | Unknown | String |

---

## API & Search Settings

| Name | Used In | Purpose | Required? | Default | Type |
|------|---------|---------|-----------|---------|------|
| `ANSWER_ENABLED` | .env.example | Enable answer generation endpoint | ⚠️ OPTIONAL | true | Boolean |
| `ANSWER_TOPK` | .env.example, api/tuning.py (line 343) | Number of segments to retrieve for answer | ⚠️ OPTIONAL | 40 | Integer |
| `ANSWER_TTL_HOURS` | .env.example | Cache TTL for answers in hours | ⚠️ OPTIONAL | 336 | Integer |
| `SIMILARITY_THRESHOLD` | api/tuning.py (line 344) | Minimum similarity threshold for search | ⚠️ OPTIONAL | 0.5 | Float (0.0-1.0) |
| `ENABLE_RERANKER` | api/tuning.py (line 345) | Enable reranking for search results | ⚠️ OPTIONAL | false | Boolean |
| `RERANK_TOP_K` | api/tuning.py (line 346) | Number of candidates to rerank | ⚠️ OPTIONAL | 200 | Integer |
| `RETURN_TOP_K` | .env.example | Number of results to return after reranking | ⚠️ OPTIONAL | 20 | Integer |
| `RERANK_BATCH_SIZE` | .env.example | Batch size for reranking | ⚠️ OPTIONAL | 64 | Integer |

---

## Application Settings

| Name | Used In | Purpose | Required? | Default | Type |
|------|---------|---------|-----------|---------|------|
| `APP_PASSWORD` | .env.example | Simple password for frontend protection | ⚠️ OPTIONAL | None | String |
| `SKIP_WARMUP` | api/main.py (line 72) | Skip embedding model warmup on startup | ⚠️ OPTIONAL | false | Boolean |
| `ENABLE_FALLBACK` | scripts/common/enhanced_asr_config.py (line 207) | Enable VRAM safety fallback | ⚠️ OPTIONAL | true | Boolean |
| `BEAM_SIZE` | .env.example | Whisper beam search width (5=GPU, 3=CPU) | ⚠️ OPTIONAL | 5 | Integer |
| `TEMPERATURE` | .env.example | Whisper temperature (0=deterministic) | ⚠️ OPTIONAL | 0.0 | Float |
| `WHISPER_VAD` | .env.example | Enable Whisper VAD (Voice Activity Detection) | ⚠️ OPTIONAL | false | Boolean |

---

## Database Configuration

### DATABASE_URL Format

**PostgreSQL with psycopg2 (REQUIRED):**
```
postgresql://user:password@host:port/database
postgresql://postgres:mypassword@localhost:5432/askdrchaffee
postgresql://postgres:mypassword@db.hetzner.com:5432/askdrchaffee?sslmode=require
```

**Connection Requirements:**
- Driver: `psycopg2-binary` (specified in requirements.txt)
- Extension: `pgvector` (must be installed on PostgreSQL)
- Port: Default 5432
- SSL: Optional but recommended for production (`?sslmode=require`)

**Alembic Configuration:**
- Reads `DATABASE_URL` from `.env` via `migrations/env.py` (line 30)
- Overrides `sqlalchemy.url` in `alembic.ini` at runtime
- Target metadata: `None` (no autogenerate)
- Migration mode: Online (uses connection pool)

---

## Alembic Migration Requirements

**Migration Execution:**
```bash
cd backend
python -m alembic upgrade head
```

**Environment Variables Read by Alembic:**
- `DATABASE_URL` - PostgreSQL connection string
- `EMBEDDING_DIMENSIONS` - Read by migration 015_fix_embedding_dimensions.py to set vector column size

**Key Migration Files:**
- `migrations/env.py` - Loads `.env` from project root (line 11)
- `migrations/versions/015_fix_embedding_dimensions.py` - Reads `EMBEDDING_DIMENSIONS` from env
- `migrations/versions/010_add_cascade_delete.py` - Uses batch processing for large tables

---

## Dynamic Environment Logic

### Embedding Provider Selection

**Profile-based (EMBEDDING_PROFILE):**
```
quality → Alibaba-NLP/gte-Qwen2-1.5B-instruct (1536-dim, slow, best quality)
speed   → BAAI/bge-small-en-v1.5 (384-dim, fast, good quality)
```

**Provider-based (EMBEDDING_PROVIDER):**
```
sentence-transformers → Local models (free, no API calls)
openai               → OpenAI API (requires OPENAI_API_KEY)
nomic                → Nomic API (requires NOMIC_API_KEY)
huggingface          → HuggingFace API (requires HUGGINGFACE_API_KEY)
```

### Whisper Device Selection

**GPU (WHISPER_DEVICE=cuda):**
- Model: distil-large-v3 (recommended)
- Compute: int8_float16 (quantization)
- Workers: 8 (ASR_WORKERS)
- Performance: 26-28 hours audio/hour on RTX 5080

**CPU (WHISPER_DEVICE=cpu):**
- Model: base (smaller, faster)
- Compute: int8 (quantization)
- Workers: 1 (ASR_WORKERS)
- Performance: ~1-2 hours audio/hour

### YouTube Source Selection

**Auto-selection logic (scripts/ingest_youtube.py line 336-338):**
```python
if from_url and source == 'api':
    source = 'yt-dlp'  # Auto-switch to yt-dlp if using --from-url
```

**Priority:**
1. YouTube API (if `YOUTUBE_API_KEY` set) - Fetches ALL videos
2. yt-dlp (default) - Fetches ~585 recent videos
3. Local files (if `--from-folder` specified)

---

## Secrets & Security

### API Keys (Must be kept secret)

| Variable | Service | Exposure Risk | Rotation |
|----------|---------|---------------|----------|
| `ADMIN_API_KEY` | Internal | High (bearer token) | Every 90 days |
| `TUNING_PASSWORD` | Internal | High (plaintext) | Every 90 days |
| `OPENAI_API_KEY` | OpenAI | Critical (billing) | Every 30 days |
| `NOMIC_API_KEY` | Nomic | High (billing) | Every 30 days |
| `YOUTUBE_API_KEY` | Google | Medium (quota) | Every 90 days |
| `HUGGINGFACE_API_KEY` | HuggingFace | Medium (model access) | Every 90 days |
| `HUGGINGFACE_HUB_TOKEN` | HuggingFace | Medium (model access) | Every 90 days |

### Best Practices

- ✅ Store in `.env` file (git-ignored)
- ✅ Use strong random strings (32+ characters)
- ✅ Rotate regularly (every 30-90 days)
- ✅ Never commit `.env` to git
- ✅ Use Coolify's secret management for production
- ✅ Use SSL/TLS for DATABASE_URL in production
- ❌ Never log API keys
- ❌ Never hardcode secrets in code

---

## CORS Configuration

**Current (Development):**
```python
allow_origins=["*"]  # Allows all origins
```

**Production (Hetzner VPS):**
```python
allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
```

**Environment Variable (if implemented):**
```
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

---

## Production Deployment Checklist

### Required Environment Variables (Minimum)

```bash
# Database (CRITICAL)
DATABASE_URL=postgresql://postgres:secure_password@db.hetzner.com:5432/askdrchaffee

# Security (CRITICAL)
ADMIN_API_KEY=your_secure_admin_key_32_chars_minimum
TUNING_PASSWORD=your_secure_tuning_password_32_chars_minimum

# Optional but Recommended
OPENAI_API_KEY=sk-proj-your_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here
HUGGINGFACE_HUB_TOKEN=hf_your_token_here

# Performance (GPU)
WHISPER_DEVICE=cuda
EMBEDDING_DEVICE=cuda
IO_WORKERS=24
ASR_WORKERS=8
DB_WORKERS=12

# Performance (CPU-only)
WHISPER_DEVICE=cpu
EMBEDDING_DEVICE=cpu
IO_WORKERS=4
ASR_WORKERS=1
DB_WORKERS=4
SKIP_WARMUP=true
```

### Verification Commands

```bash
# Test database connection
psql $DATABASE_URL -c "SELECT 1; CREATE EXTENSION IF NOT EXISTS vector;"

# Test API startup
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Test migrations
python -m alembic upgrade head

# Test embeddings
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'
```

---

## Summary

**Total Environment Variables:** 90+

**Required (CRITICAL):** 3
- DATABASE_URL
- ADMIN_API_KEY
- TUNING_PASSWORD

**Highly Recommended:** 7
- OPENAI_API_KEY
- YOUTUBE_API_KEY
- WHISPER_DEVICE
- EMBEDDING_DEVICE
- IO_WORKERS
- ASR_WORKERS
- DB_WORKERS

**Optional (with sensible defaults):** 80+

**All variables are loaded from `.env` file via `python-dotenv` at application startup.**
