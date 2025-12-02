# Embedding Architecture

> Last updated: December 2025

This document describes the embedding storage and retrieval architecture for Dr. Chaffee AI.

## Quick Reference

| Component | Status | Description |
|-----------|--------|-------------|
| Legacy Storage | Active | `segments.embedding` column |
| Normalized Storage | Active | `segment_embeddings_384` table (table-per-dimension) |
| Answer Cache | Optional | `answer_cache` + `answer_cache_embeddings_384` |
| Dual-Write | Enabled | Writes to both storage types |
| Fallback Read | Enabled | Falls back to legacy if normalized empty |

## Table-Per-Dimension Architecture

Each embedding dimension gets its own table with a fixed-dimension VECTOR column
and optimized IVFFlat index. This design ensures:

- **IVFFlat compatibility**: Indexes require fixed-dimension columns
- **No dimension mismatch errors**: Each table only stores vectors of one size
- **Clean model separation**: Easy to add/remove models without affecting others
- **Optimal index performance**: Each table has its own tuned index

### Tables by Dimension

| Dimension | Segment Table | Answer Cache Table | Status |
|-----------|---------------|-------------------|--------|
| 384 | `segment_embeddings_384` | `answer_cache_embeddings_384` | ✅ Created via migration |
| 768 | `segment_embeddings_768` | `answer_cache_embeddings_768` | Created on-demand |
| 1024 | `segment_embeddings_1024` | `answer_cache_embeddings_1024` | Created on-demand |
| 1536 | `segment_embeddings_1536` | `answer_cache_embeddings_1536` | Created on-demand |
| 3072 | `segment_embeddings_3072` | `answer_cache_embeddings_3072` | Created on-demand |

### Compatibility Views

For backward compatibility, views are created that point to the active tables:
- `segment_embeddings` → `segment_embeddings_384`
- `answer_cache_embeddings` → `answer_cache_embeddings_384`

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

### Normalized Storage (segment_embeddings_384)

Table-per-dimension architecture for multi-model support.

```
segment_embeddings_384
├── id (BIGSERIAL PK)
├── segment_id (FK → segments)
├── model_key (TEXT)      ← e.g., "bge-small-en-v1.5"
├── embedding VECTOR(384) ← Fixed dimension for IVFFlat
├── created_at
└── UNIQUE(segment_id, model_key)
```

**IVFFlat Index:** `idx_segment_embeddings_384_ivfflat`
- Required for ANN search performance with 500k+ rows
- Uses `vector_cosine_ops` for cosine similarity
- Lists parameter calculated as `sqrt(row_count)`

**Pros:**
- Multiple models per segment
- Easy A/B testing
- Clean dimension separation
- Model provenance tracking

### Answer Cache (Optional Feature)

Caches AI-generated answers for semantic recall.

```
answer_cache                    answer_cache_embeddings_384
├── id (PK)                     ├── id (BIGSERIAL PK)
├── query_text                  ├── answer_cache_id (FK)
├── style                       ├── model_key
├── answer_md                   ├── embedding VECTOR(384)
├── citations (JSONB)           ├── created_at
├── confidence                  └── UNIQUE(answer_cache_id, model_key)
└── ...
```

**IVFFlat Index:** `idx_answer_cache_embeddings_384_ivfflat`

**Feature Flag:** `ANSWER_CACHE_ENABLED` (default: `false`)

**Precedence (highest to lowest):**
1. `ANSWER_CACHE_ENABLED` environment variable
2. `"answer_cache_enabled"` in `embedding_models.json`
3. Default: `false`

When disabled:
- Cache lookups return `{"cached": null}` immediately
- Cache saves return `{"success": true, "skipped": true}`
- No database queries to answer cache tables
- No embedding generation for cache operations

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

## Storage Initialization

### Environment Behavior

| Environment | Missing Table Behavior |
|-------------|----------------------|
| **Production** (`ENV=prod`) | Hard error - tables must exist via migration |
| **Development** (`ENV=dev`) | Auto-create if `AUTO_CREATE_EMBEDDING_TABLES=true` |

### Manual Table Initialization

To manually create tables for a new model dimension:

```python
from backend.scripts.embedding_storage import (
    create_segment_embedding_table,
    create_answer_cache_embedding_table,
    create_ivfflat_index,
)

# Example: Create 768-dim tables for Nomic
conn = get_db_connection()
create_segment_embedding_table(conn, 'segment_embeddings_768', 768)
create_ivfflat_index(conn, 'segment_embeddings_768', 768)
create_answer_cache_embedding_table(conn, 'answer_cache_embeddings_768', 768)
create_ivfflat_index(conn, 'answer_cache_embeddings_768', 768)
```

### Paid Model Warning

Models marked with `"paid": true` in `embedding_models.json` require explicit
confirmation for backfills to prevent unexpected API costs. Backfills are
**never automatic** - they must be triggered manually.

## Migration History

| Migration | Description |
|-----------|-------------|
| 009 | Create `answer_cache` table with legacy embedding columns |
| 015 | Fix embedding dimensions |
| 016 | Adaptive embedding index |
| 017 | Drop old segment_embeddings (cleanup) |
| 021 | Create `segment_embeddings_384` table + IVFFlat index |
| 022 | Create `answer_cache_embeddings_384` table + IVFFlat index |

## Files

| File | Purpose |
|------|---------|
| `backend/api/embedding_config.py` | Single source of truth for config |
| `backend/config/models/embedding_models.json` | Model catalog with table mappings |
| `backend/scripts/embedding_storage.py` | Table creation and initialization |
| `backend/api/main.py` | Search endpoints, answer cache |
| `backend/scripts/common/segments_database.py` | Dual-write logic |
| `backend/scripts/common/embeddings.py` | Embedding generation |
