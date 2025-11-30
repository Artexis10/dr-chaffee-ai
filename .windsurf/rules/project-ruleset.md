---
trigger: glob
globs: dr-chaffee-ai/**
---

# dr-chaffee-ai — Windsurf Project Ruleset

**Project:** Ask Dr. Chaffee (Semantic Search & RAG System)  
**Stack:** FastAPI + PostgreSQL (pgvector) + Whisper + Local Embeddings + Next.js  
**Purpose:** Ingest, embed, and semantically search Dr. Chaffee’s YouTube content; generate LLM-backed answers with citation.

These rules apply only inside the `dr-chaffee-ai` repository.

---

# A. Architecture Rules

## Protected Architecture (DO NOT MODIFY)
- 3-tier system: Next.js → FastAPI → PostgreSQL (pgvector)
- Ingestion pipeline: YouTube → Whisper → Speaker ID → Embeddings → DB
- Search pipeline: Query → Local embeddings → pgvector → optional reranker
- Answer pipeline: RAG → OpenAI summarization → Cache (14-day TTL by default)

## Protected Components
- Database schema: `db/schema.sql` (modify only via Alembic migrations)
- Embedding dimensions (via `EMBEDDING_PROFILE` and `EMBEDDING_DIMENSIONS`)
- Speaker ID system & voice profiles
- Dockerfile & `docker-compose.dev.yml`
- Core embedding system: `backend/scripts/common/embeddings.py`
- Enhanced ASR pipeline: `backend/scripts/common/enhanced_asr.py`
- Segment DB layer: `backend/scripts/common/segments_database.py`

## Extensible Components
- New API endpoints in `backend/api/`
- New frontend pages/components in `frontend/src`
- New ingestion/maintenance scripts in `backend/scripts/`
- Experimental modules under `backend/scripts/experimental/`

---

# B. File & Directory Rules

## Protected
- `backend/requirements.txt`
- `backend/scripts/common/embeddings.py`
- `backend/scripts/common/enhanced_asr.py`
- `backend/scripts/common/segments_database.py`
- `backend/scripts/common/enhanced_transcript_fetch.py`
- `backend/migrations/env.py`
- `shared/prompts/chaffee_persona.md`
- `.env.example`
- `Dockerfile`, `docker-compose.dev.yml`
- Root `.gitignore`
- `backend/alembic.ini`

## Modify with Caution
- `backend/scripts/ingest_youtube.py`  
  - Allowed: adjust concurrency, add CLI flags, logging, safety checks  
  - Forbidden: remove fallback chains, break GPU metrics, change core queue/worker model
- `backend/api/main.py`  
  - Allowed: add endpoints, CORS tuning, health checks  
  - Forbidden: breaking DB lifecycle, removing embedding warmup
- `backend/api/tuning.py`
- `Makefile`
- Root `package.json`

## Freely Modifiable
- Experimental scripts under `backend/scripts/experimental/`
- New frontend components/pages under `frontend/src/components` and `frontend/src/pages`
- New backend routes/modules under `backend/api` (non-core)
- Test scripts and utilities
- Markdown docs
- All frontend styling changes should follow the design guide located at: frontend/docs/ui-style.md
- Do not introduce new colors, radii, or theme variables; reuse existing tokens unless explicitly requested

Follow the Dr Chaffee UI Theme Guardrails; don’t introduce new color schemes or card styles, just reuse the existing ones (frontend/docs/ui-theme-guidelines.md).

---

# C. Embeddings & LLM Rules

## Local Embeddings (MANDATORY)
- Embeddings must be generated with **local models** (e.g. BGE-small, GTE-Qwen2) via `sentence-transformers`.
- **Forbidden:** OpenAI embeddings in any ingestion or search pipeline.
- Embedding dimensions are controlled via `EMBEDDING_PROFILE`/`EMBEDDING_DIMENSIONS`.
- **Never** change embedding dimension without:
  - a dedicated Alembic migration, and
  - a full backfill of existing embeddings.
- Always use batched embedding calls (typical range: 256–2048 texts per batch, depending on GPU VRAM and stability).

## LLM Usage
Allowed:
- Answer generation for `/api/answer` using OpenAI models.
- Domain-specific summarization scripts.
- Persona-aware RAG generation that uses the baseline persona + stored custom instructions.

Forbidden:
- Using OpenAI for embeddings.
- Using OpenAI for transcription (Whisper is primary).
- Bypassing the answer cache logic for normal user traffic.

---

# D. Database Rules

## pgvector
- Use cosine distance operators (`vector_cosine_ops`) for similarity.
- Use indexed search (e.g. `ivfflat` index tuned for current scale).
- Do not switch to L2 metrics.

## Tables (Conceptual)
- `sources` — video/recording metadata (mostly append-only).
- `segments` — transcript segments + embeddings + speaker labels.
- `api_cache` — YouTube / external API response cache.
- `answer_cache` — LLM answer cache with expiry.
- `custom_instructions` — stored user tuning for the assistant.

Forbidden:
- Storing audio blobs in the DB (use filesystem / object storage outside Postgres).
- Storing secrets or API keys in DB.
- Hardcoding embedding dimension or model names in SQL.

## Migrations
- Always use Alembic (`backend/migrations/versions/`).
- Never manually edit `db/schema.sql` directly.
- Never delete or rewrite old migrations; add new ones.
- Test `upgrade` and `downgrade` paths.
- For large data updates: use batched operations (e.g. 5k–10k rows per batch).

---

# E. Performance Rules (RTX 5080-Optimised)

The system is tuned for a **high-end RTX 5080 GPU**. Windsurf must preserve and respect this.

## Ingestion / ASR Performance

- Primary GPU: **RTX 5080**
- Whisper model family: large-quality model (e.g. `distil-large-v3` or equivalent).
- Precision: quantized / mixed precision (`int8` / `float16`) where configured.

### Worker/Concurrency Guidelines (Starting Point)
These are tuned for a single RTX 5080 and may be adjusted, but not casually:

- **IO / download workers:** ~24  
  - Handles YouTube/remote fetch.  
  - OK to tune within a reasonable range (e.g. 16–32) based on real-world performance and network constraints.
- **ASR workers:** ~8  
  - GPU-bound; increasing beyond this can *reduce* performance if it causes kernel contention.  
  - Typical safe range: 6–12, but do not change without monitoring GPU utilization.
- **DB / embedding workers:** ~12  
  - Handles embedding generation + DB writes.  
  - Adjust only if DB becomes bottlenecked or underutilised.

### Whisper GPU Rules (Critical)
- `WHISPER_PARALLEL_MODELS` (or equivalent parallelism setting) must remain **1** unless you intentionally retune.  
  - Running multiple full models in parallel on the same RTX 5080 usually causes massive contention and slowdowns.
- Do not disable batching for ASR if batching is implemented.
- If you add new optimizations, they must:
  - keep GPU utilization in the **80–90% SM usage** window under steady ingestion load, and  
  - not starve other components (DB, embeddings, etc.).

### Embeddings Throughput
- Use batched embedding generation (256–2048 texts per batch, tuned for VRAM).
- Keep embedding queues fed so the GPU is not idle.
- If GPU utilization drops below ~70% during heavy ingestion:
  - consider increasing ASR workers or embedding batch sizes,  
  - but do not change model or precision without explicit intent.

### Forbidden Performance “Optimizations”
These commonly make things worse on an RTX 5080 and are **not allowed** without explicit, documented intent:

- Increasing Whisper parallel models beyond 1 “for more throughput” without measurement.
- Disabling embedding or ASR batching to “simplify code.”
- Removing or bypassing fallback chains in the ingestion pipeline.
- Fetching all segments into Python and filtering there instead of using SQL and indexes.
- Dropping or not using pgvector indexes.

If you introduce a new performance strategy, you must:
- explain the rationale,
- describe expected impact on GPU load, latency, and throughput,
- avoid regressing resilience (fallback chains, error handling).

---

# F. Security Rules

- All secrets in `.env` (never in code, never in repo).
- Do not log secrets, passwords, or full connection strings.
- Always sanitize user input; use parameterized SQL.
- Validate file uploads (types, size caps) if/when enabled.
- No execution of user-supplied code/commands.

PII:
- This system primarily processes public YouTube content; do not add PII handling or user accounts without new security rules.

---

# G. Assistant Behaviour Rules (Project-Specific)

## DO NOT
- Create new files unless explicitly requested.
- Rename, move, or delete modules without instruction.
- Rewrite entire modules “for cleanup.”
- Relax or delete tests to make code pass.
- Change embedding model, dimensionality, or storage format without migration + documented plan.
- Change Whisper model or ASR strategy without explicit intent.
- Modify Dockerfile/compose/env templates unless asked.
- Invent new env vars, paths, or configuration knobs.

## DO
- Follow existing structure and naming.
- Use Python type hints consistently.
- Add or update tests when adding new features.
- Update docs or comments when changing APIs, behaviour, or important internals.
- Keep diffs minimal and well-scoped.

---

# H. Development Workflow Expectations

## Migrations
- Use `alembic revision` + `alembic upgrade/downgrade`.
- Never edit old migration files for “cleanup.”
- Handle large tables using batched operations.

## Dependencies
- Python and JS dependencies are pinned; update carefully.
- Justify any new dependency.
- Prefer using existing libraries already in the project.

## Docker
- Dev: `docker-compose.dev.yml` with GPU (RTX 5080) support.
- Prod: CPU-optimized Dockerfile for servers (e.g., Hetzner).
- Do not change base images or GPU setup without a clear need.

## Testing
- Use `pytest` for tests (`tests/unit`, `tests/integration`, etc.).
- Add regression tests for bugs.
- Do not delete or weaken tests to “fix” failures.

---

# Summary

**Protected:** schema, embeddings pipeline, ASR, persona prompt, core ingestion logic, Docker/compose, env templates.  
**Caution:** main API, ingestion concurrency, performance tuning, pgvector logic.  
**Free:** new endpoints, components, scripts, and tests that respect the architecture.

Windsurf must treat this project as a performance-sensitive, GPU-aware RAG backend with strict architectural and safety constraints.