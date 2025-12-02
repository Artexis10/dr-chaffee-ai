# Embedding Architecture

> Last updated: December 2025

This document describes the embedding storage and retrieval architecture for Dr. Chaffee AI.

## Quick Reference

| Component | Status | Description |
|-----------|--------|-------------|
| Legacy Storage | Active | `segments.embedding` column |
| Normalized Storage | Active | `segment_embeddings` table |
| Answer Cache | Optional | `answer_cache` + `answer_cache_embeddings` |
| Dual-Write | Enabled | Writes to both storage types |
| Fallback Read | Enabled | Falls back to legacy if normalized empty |

## Storage Architecture

### Legacy Storage (segments.embedding)

Single vector column on the `segments` table.

```
segments
├── id (PK)
├── source_id (FK → sources)
├── text
├── start_sec, end_sec
├── embedding (VECTOR)  ← Legacy storage
└── ...
```

**Pros:**
- Simple, no JOINs
- Fast queries
- 514k+ embeddings already stored

**Cons:**
- Single model per deployment
- Requires migration to change dimensions

### Normalized Storage (segment_embeddings)

Separate table supporting multiple embedding models per segment.

```
segment_embeddings
├── id (UUID PK)
├── segment_id (FK → segments)
├── model_key (TEXT)      ← e.g., "bge-small-en-v1.5"
├── dimensions (INT)      ← e.g., 384
├── embedding (VECTOR)
├── is_active (BOOL)      ← For model switching
├── created_at
└── UNIQUE(segment_id, model_key)
```

**Pros:**
- Multiple models per segment
- Easy A/B testing
- No migrations for new models
- Model provenance tracking

### Answer Cache (Optional Feature)

Caches AI-generated answers for semantic recall.

```
answer_cache                    answer_cache_embeddings
├── id (PK)                     ├── id (UUID PK)
├── query_text                  ├── answer_cache_id (FK)
├── style                       ├── model_key
├── answer_md                   ├── dimensions
├── citations (JSONB)           ├── embedding (VECTOR)
├── confidence                  ├── is_active
└── ...                         └── UNIQUE(answer_cache_id, model_key)
```

**Feature Flag:** `ANSWER_CACHE_ENABLED` (default: `false`)

When disabled:
- Cache lookups return `null` immediately
- Cache saves are no-ops
- No database queries to answer cache tables

## Configuration

### Single Source of Truth

All embedding configuration flows through `backend/api/embedding_config.py`.

### Priority Order

1. **Environment variables** (highest priority)
   - `EMBEDDING_MODEL_KEY`
   - `EMBEDDING_STORAGE_STRATEGY`
   - `EMBEDDING_DUAL_WRITE`
   - `EMBEDDING_FALLBACK_READ`
   - `ANSWER_CACHE_ENABLED`

2. **Config file** (`backend/config/models/embedding_models.json`)

3. **Hardcoded defaults** (lowest priority)
   - Model: `bge-small-en-v1.5`
   - Dimensions: `384`

### Key Configuration Flags

| Flag | Default | Description |
|------|---------|-------------|
| `storage_strategy` | `normalized` | `"normalized"` or `"legacy"` |
| `use_dual_write` | `true` | Write to both storage types |
| `use_fallback_read` | `true` | Fall back to legacy if normalized empty |
| `answer_cache_enabled` | `false` | Enable answer cache feature |

## Runtime Behavior

### Write Path (Ingestion)

```
segments_database.py::batch_insert_segments()
    │
    ├─► INSERT INTO segments (embedding = ...)  [Always]
    │
    └─► IF use_dual_write:
            INSERT INTO segment_embeddings (...)  [Normalized]
```

### Read Path (Search)

```
semantic_search_with_fallback()
    │
    ├─► IF storage_strategy = "normalized":
    │       Query segment_embeddings
    │       Log: "embedding_read_source: source=segment_embeddings"
    │
    └─► IF no results AND use_fallback_read:
            Query segments.embedding
            Log: "embedding_read_source: source=segments_legacy"
```

### Answer Cache Path

```
/answer/cache/lookup
    │
    ├─► IF NOT is_answer_cache_enabled():
    │       Return {"cached": null}  [Early exit]
    │
    └─► Query answer_cache_embeddings
        Log: "Answer cache HIT/MISS"
```

## Verification

### Run Migrations

```bash
cd backend
py -3.11 -m alembic upgrade head
```

### Run Tests

```bash
# Unit tests (no database required)
py -3.11 -m pytest tests/test_embedding_architecture.py -v -k "not integration"

# Integration tests (requires database)
py -3.11 -m pytest tests/test_embedding_architecture.py -v --run-integration
```

### Check Logs

Look for these log patterns:

```
# Embedding read source
embedding_read_source: source=segment_embeddings model=bge-small-en-v1.5 results=20
embedding_read_source: source=segments_legacy model=bge-small-en-v1.5 results=20

# Answer cache (when enabled)
Answer cache HIT: query='...' similarity=0.95 source=answer_cache_embeddings:bge-small-en-v1.5
Answer cache MISS: query='...'

# Answer cache (when disabled)
Answer cache lookup skipped: ANSWER_CACHE_ENABLED=false
```

## Migration History

| Migration | Description |
|-----------|-------------|
| 009 | Create `answer_cache` table with legacy embedding columns |
| 015 | Fix embedding dimensions |
| 016 | Adaptive embedding index |
| 017 | Drop old segment_embeddings (cleanup) |
| 021 | Create `segment_embeddings` table (normalized) |
| 022 | Create `answer_cache_embeddings` table (normalized) |

## Files

| File | Purpose |
|------|---------|
| `backend/api/embedding_config.py` | Single source of truth for config |
| `backend/config/models/embedding_models.json` | Model catalog and settings |
| `backend/api/main.py` | Search endpoints, answer cache |
| `backend/scripts/common/segments_database.py` | Dual-write logic |
| `backend/scripts/common/embeddings.py` | Embedding generation |
