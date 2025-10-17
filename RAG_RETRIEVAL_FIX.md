# RAG Retrieval Fix - Increased Results from 8 to 100

## Problem Statement

The RAG (Retrieval-Augmented Generation) system was returning only **8 results** for queries like "ketosis explained" instead of the expected **90+ results**, severely limiting the quality and depth of AI summarization.

## Root Cause Analysis

### Issues Identified

1. **`ANSWER_TOPK` reduced from 50 to 30** (line 28 in `answer.ts`)
   - This was the primary limit on chunk retrieval
   - Comment said "reduced for quality" but actually reduced coverage

2. **`maxContext` parameter limited to `ANSWER_TOPK`** (line 674)
   - Even when frontend passed `top_k: 50`, it was capped at 30

3. **Database query hard-limited by `maxContext`** (line 746)
   - SQL `LIMIT` clause used `maxContext`, preventing more results

4. **No fallback mechanism**
   - If `segment_embeddings` table had no data for a model, query returned 0 results
   - No fallback to legacy `segments.embedding` column

5. **Model key mismatch**
   - Query hardcoded `model_key = 'nomic-v1.5'`
   - But database might have different model keys (e.g., `'gte-qwen2-1.5b'`, `'all-minilm-l6-v2'`)

## Changes Implemented

### 1. Frontend API (`/frontend/src/pages/api/answer.ts`)

#### Increased Retrieval Limits
```typescript
// Line 28: Increased from 30 to 100
const ANSWER_TOPK = parseInt(process.env.ANSWER_TOPK || '100');
```

#### Added Dynamic Model Detection
```typescript
// Lines 730-736: Auto-detect model based on embedding dimensions
let modelKey = 'nomic-v1.5';
if (queryEmbedding.length === 384) {
  modelKey = 'all-minilm-l6-v2';
} else if (queryEmbedding.length === 1536) {
  modelKey = 'gte-qwen2-1.5b';
}
```

#### Added Fallback to Legacy Embeddings
```typescript
// Lines 795-820: Fallback if segment_embeddings returns no results
if (chunks.length === 0 && queryEmbedding.length > 0) {
  // Try legacy segments.embedding column
  searchResult = await pool.query(legacyQuery, params);
  chunks = searchResult.rows;
}
```

#### Enhanced Logging
```typescript
// Added comprehensive logging at key points:
console.log(`[Answer API] Query: "${query}", maxContext: ${maxContext}`);
console.log(`[Answer API] Embedding generated: ${queryEmbedding.length} dimensions`);
console.log(`[Answer API] Using model: ${modelKey}`);
console.log(`[Answer API] Initial retrieval: ${chunks.length} chunks`);
console.log(`[Answer API] Final chunks: ${topChunks.length}`);
console.log(`[Answer API] Similarity range: ${min} - ${max}`);
```

#### Fixed Similarity Calculation
```typescript
// Line 752: Changed from distance to similarity (1 - distance)
1 - (se.embedding <=> $1::vector) as similarity
```

### 2. Frontend Client (`/frontend/src/pages/index.tsx`)

#### Increased Client Request Limit
```typescript
// Line 201: Increased from 50 to 100
body: JSON.stringify({
  query: query.trim(),
  style: currentStyle,
  top_k: 100  // Increased for better coverage
})
```

## Expected Improvements

### Before Fix
- **Retrieval**: 8-30 chunks maximum
- **Coverage**: Limited context for summarization
- **Quality**: Shallow answers due to insufficient context
- **Failures**: Silent failures when model key mismatched

### After Fix
- **Retrieval**: Up to 100 chunks
- **Coverage**: 3-10x more context for summarization
- **Quality**: Deeper, more comprehensive answers
- **Robustness**: Automatic fallback to legacy embeddings
- **Debugging**: Comprehensive logging for troubleshooting

## Testing Recommendations

### 1. Test Query: "ketosis explained"
```bash
# Expected: 50-100 results (depending on database content)
curl -X POST http://localhost:3000/api/answer \
  -H "Content-Type: application/json" \
  -d '{"query": "ketosis explained", "style": "detailed", "top_k": 100}'
```

### 2. Check Logs
Look for these log lines:
```
[Answer API] Query: "ketosis explained", maxContext: 100
[Answer API] Embedding generated: 768 dimensions
[Answer API] Using model: nomic-v1.5
[Answer API] Initial retrieval: 87 chunks
[Answer API] Final chunks: 87
[Answer API] Similarity range: 0.823 - 0.412
```

### 3. Verify Database Content
```sql
-- Check which models have embeddings
SELECT model_key, COUNT(*) as count, AVG(array_length(embedding::text::float[], 1)) as avg_dims
FROM segment_embeddings
WHERE embedding IS NOT NULL
GROUP BY model_key;

-- Check legacy embeddings
SELECT COUNT(*) as legacy_count
FROM segments
WHERE embedding IS NOT NULL AND speaker_label = 'Chaffee';
```

### 4. Test Different Queries
- **Broad topics**: "carnivore diet benefits" (should return 80-100 results)
- **Specific topics**: "oxalates in spinach" (might return 20-40 results)
- **Rare topics**: "quantum mechanics" (should return 0-5 results)

## Potential Issues & Mitigations

### Issue 1: Database Doesn't Have segment_embeddings Table
**Symptom**: Still getting 0-8 results
**Solution**: Check if migration was applied
```sql
SELECT EXISTS (
  SELECT 1 FROM information_schema.tables 
  WHERE table_name = 'segment_embeddings'
);
```
**Mitigation**: Fallback to `segments.embedding` column (already implemented)

### Issue 2: Model Key Mismatch
**Symptom**: 0 results from segment_embeddings, but legacy query works
**Solution**: Check available models
```sql
SELECT DISTINCT model_key FROM segment_embeddings;
```
**Mitigation**: Auto-detection based on dimensions (already implemented)

### Issue 3: Embedding Service Down
**Symptom**: `queryEmbedding.length === 0`
**Solution**: Check embedding service logs
**Mitigation**: Falls back to text search (already implemented)

### Issue 4: Performance Degradation
**Symptom**: Queries take >5 seconds
**Solution**: Check if pgvector indexes exist
```sql
-- Check indexes
SELECT indexname, tablename FROM pg_indexes 
WHERE tablename IN ('segments', 'segment_embeddings');
```
**Mitigation**: Create indexes if missing (see migrations)

## Environment Variables

You can now control retrieval limits via environment variables:

```bash
# Backend (.env or deployment config)
ANSWER_TOPK=100  # Default: 100 (was 30)

# Frontend can override per-request
# Pass top_k in request body
```

## Monitoring

### Key Metrics to Track
1. **Average chunks retrieved**: Should be 50-100 for common queries
2. **Cache hit rate**: Should increase with more consistent results
3. **Answer quality**: User feedback on answer depth
4. **Query latency**: Should remain <5s for detailed answers

### Log Analysis
```bash
# Count retrieval sizes
grep "Initial retrieval" logs.txt | awk '{print $NF}' | sort -n | uniq -c

# Check similarity ranges
grep "Similarity range" logs.txt

# Find queries with low retrieval
grep "Initial retrieval: [0-9] chunks" logs.txt
```

## Rollback Plan

If issues arise, you can quickly rollback by:

1. **Reduce ANSWER_TOPK back to 30**:
   ```typescript
   const ANSWER_TOPK = parseInt(process.env.ANSWER_TOPK || '30');
   ```

2. **Set environment variable**:
   ```bash
   ANSWER_TOPK=30
   ```

3. **Revert frontend top_k**:
   ```typescript
   top_k: 50  // or 30
   ```

## Next Steps

1. **Monitor production logs** for 24-48 hours
2. **Collect user feedback** on answer quality
3. **Optimize similarity thresholds** if needed
4. **Consider implementing clustering** if results are too redundant
5. **Add A/B testing** to compare 30 vs 100 chunk retrieval

## Related Files

- `/frontend/src/pages/api/answer.ts` - Main answer API endpoint
- `/frontend/src/pages/index.tsx` - Frontend client
- `/backend/api/main.py` - Backend RAG service
- `/db/migrations/` - Database schema migrations
- `/backend/migrations/dynamic_embeddings_proper.sql` - segment_embeddings table

## References

- Original issue: "only 8 results instead of 90 for ketosis explained"
- Related: `callSummarizer` function quality depends on chunk count
- See: `ANSWER_ENDPOINT_SETUP.md` for API documentation
