# Embedding Storage Architecture Guide

## Overview

This document explains the two embedding storage approaches in the Ask Dr. Chaffee system and when to use each one.

## Current Implementation: Legacy Storage

### Schema
```sql
segments table:
├── id (primary key)
├── text (varchar)
├── speaker_label (varchar)
├── start_sec (float)
├── end_sec (float)
├── embedding (vector(384))  ← Single model, fixed dimensions
└── ... other columns
```

### Characteristics
- **Single model per deployment** - Currently using BGE-small-en-v1.5 (384 dimensions)
- **Simple queries** - No JOINs needed
- **Fast performance** - Direct column access
- **Current data** - 514,391 embeddings already stored this way

### Query Example
```python
# Legacy storage query
SELECT seg.id, seg.text, 1 - (seg.embedding <=> %s::vector) as similarity
FROM segments seg
WHERE seg.embedding IS NOT NULL
ORDER BY similarity DESC
LIMIT 20
```

### Advantages
✅ Simplicity - Single table, straightforward queries
✅ Performance - No JOINs, direct vector operations
✅ Storage efficient - One embedding per segment
✅ Proven - Works reliably with 514k embeddings

### Disadvantages
❌ No multi-model support - Can't store multiple embeddings per segment
❌ Migration required - Changing dimensions requires ALTER TABLE
❌ No provenance - Can't track which model generated each embedding
❌ No A/B testing - Can't easily compare different models

---

## Alternative: Normalized Storage

### Schema
```sql
segment_embeddings table:
├── id (primary key)
├── segment_id (foreign key → segments.id)
├── model_key (varchar)  ← e.g., 'bge-small-en-v1.5'
├── embedding (vector(N))  ← Flexible dimensions per model
├── created_at (timestamp)
└── updated_at (timestamp)

segments table:
├── id (primary key)
├── text (varchar)
├── speaker_label (varchar)
├── start_sec (float)
├── end_sec (float)
└── ... other columns (NO embedding column)
```

### Characteristics
- **Multiple models per segment** - Store BGE-small, Nomic, OpenAI embeddings simultaneously
- **Flexible dimensions** - Each model can have different vector sizes
- **Model tracking** - Know exactly which model generated each embedding
- **Easy upgrades** - Add new models without migrations

### Query Example
```python
# Normalized storage query
SELECT seg.id, seg.text, 1 - (se.embedding <=> %s::vector(384)) as similarity
FROM segments seg
JOIN segment_embeddings se ON seg.id = se.segment_id
WHERE se.model_key = 'bge-small-en-v1.5'
  AND se.embedding IS NOT NULL
ORDER BY similarity DESC
LIMIT 20
```

### Advantages
✅ Multi-model support - Store multiple embeddings per segment
✅ No migrations - Add new models without ALTER TABLE
✅ A/B testing - Compare models on identical segments
✅ Provenance tracking - Know which model generated each embedding
✅ Flexible dimensions - Different models can have different vector sizes
✅ Easy rollback - Keep old embeddings while testing new models

### Disadvantages
❌ Extra JOIN - Slightly slower queries (typically <5% impact)
❌ More complex - More code to maintain
❌ More storage - Multiple embeddings per segment
❌ Migration cost - Moving 514k embeddings is risky

---

## Decision Matrix

| Scenario | Use Legacy | Use Normalized |
|----------|-----------|-----------------|
| Single embedding model | ✅ | ❌ |
| A/B testing models | ❌ | ✅ |
| Comparing model quality | ❌ | ✅ |
| Switching models frequently | ❌ | ✅ |
| Performance critical | ✅ | ❌ |
| Compliance/audit trail needed | ❌ | ✅ |
| Simple codebase preferred | ✅ | ❌ |
| 514k existing embeddings | ✅ | ❌ (requires migration) |

---

## Migration Path: Legacy → Normalized

If you decide to switch to normalized storage:

### Step 1: Create Normalized Table
```sql
CREATE TABLE segment_embeddings (
    id BIGSERIAL PRIMARY KEY,
    segment_id BIGINT NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
    model_key VARCHAR(255) NOT NULL,
    embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(segment_id, model_key),
    INDEX idx_model_key (model_key),
    INDEX idx_embedding (embedding vector_cosine_ops)
);
```

### Step 2: Backfill Existing Embeddings
```sql
INSERT INTO segment_embeddings (segment_id, model_key, embedding, created_at)
SELECT id, 'bge-small-en-v1.5', embedding, created_at
FROM segments
WHERE embedding IS NOT NULL
ON CONFLICT (segment_id, model_key) DO NOTHING;
```

### Step 3: Verify Data
```sql
SELECT COUNT(*) FROM segment_embeddings;  -- Should be 514,391
SELECT COUNT(*) FROM segments WHERE embedding IS NOT NULL;  -- Should match
```

### Step 4: Update Application Code
- Change `get_available_embedding_models()` to query `segment_embeddings`
- Update search queries to use normalized path
- Test thoroughly with production data

### Step 5: Gradual Rollout
- Deploy with both paths active (current code already supports this)
- Monitor performance and correctness
- Keep legacy column as fallback
- Drop legacy column only after full validation

### Step 6: Cleanup (Optional)
```sql
ALTER TABLE segments DROP COLUMN embedding;
```

---

## Current Code Implementation

### Detection Logic
File: `backend/api/main.py`, function `get_available_embedding_models()`

```python
# Returns storage_type flag to distinguish between:
# - "normalized": Data in segment_embeddings table
# - "legacy": Data in segments.embedding column

model = {
    "model_key": model_key,
    "dimensions": dimensions,
    "count": result['count'],
    "storage_type": "legacy"  # or "normalized"
}
```

### Query Paths
File: `backend/api/main.py`, function `semantic_search()`

**Legacy Path** (lines 468-494):
```python
if not use_normalized:
    search_query = """
        SELECT ... FROM segments seg
        WHERE seg.embedding IS NOT NULL
        ORDER BY similarity DESC
    """
```

**Normalized Path** (lines 437-466):
```python
if use_normalized:
    search_query = """
        SELECT ... FROM segments seg
        JOIN segment_embeddings se ON seg.id = se.segment_id
        WHERE se.model_key = %s
        ORDER BY similarity DESC
    """
```

---

## Recommendations

### Short Term (Current)
✅ **Keep legacy storage** - Works perfectly, no migration risk
✅ **Keep normalized code path** - Reference implementation for future
✅ **Monitor performance** - Single model is fast enough

### Medium Term (If Needed)
- If you want to A/B test models: Implement normalized storage
- If you want to switch models: Keep both embeddings during transition
- If you need compliance: Add provenance tracking via normalized storage

### Long Term
- Consider normalized storage if multi-model becomes standard
- Plan migration carefully with staging environment
- Keep legacy as fallback during transition

---

## Performance Comparison

### Query Latency
- **Legacy:** ~50-100ms for 514k segments (no JOIN)
- **Normalized:** ~55-110ms for 514k segments (with JOIN)
- **Impact:** <10% slower, negligible for user experience

### Storage Size
- **Legacy:** ~200MB for 514k × 384-dim vectors
- **Normalized (1 model):** ~210MB (same + metadata)
- **Normalized (3 models):** ~600MB (3× embeddings)

### Query Complexity
- **Legacy:** 1 table, simple WHERE clause
- **Normalized:** 2 tables, JOIN, model_key filter

---

## References

- **Current Implementation:** `backend/api/main.py`
- **Database Schema:** `db/schema.sql`
- **Migrations:** `backend/migrations/`
- **Tests:** `tests/api/test_answer_endpoint.py`

---

## Decision Log

**Nov 20, 2025:** Decided to keep legacy storage for now. Normalized path remains in code as reference implementation for future multi-model support if needed.
