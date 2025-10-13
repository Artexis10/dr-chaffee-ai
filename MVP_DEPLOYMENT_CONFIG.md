# MVP Deployment Configuration Guide

## Critical Environment Variables

### Database
```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

### Embedding Configuration
```bash
# Text embeddings (semantic search)
EMBEDDING_DEVICE=cuda  # Use GPU for 5-10x faster embedding generation
EMBEDDING_MODEL=Alibaba-NLP/gte-Qwen2-1.5B-instruct  # Default model

# Voice embeddings (speaker identification)
SKIP_VOICE_EMBEDDINGS=false  # MUST be false for speaker ID
EMBED_CHAFFEE_ONLY=false  # Store BOTH Chaffee and Guest embeddings for future optimization
```

### Speaker Identification
```bash
# Chaffee voice profile setup (run once)
python backend/scripts/ingest_youtube.py --setup-chaffee <AUDIO_FILES_OR_YOUTUBE_URLS>

# Example:
python backend/scripts/ingest_youtube.py --setup-chaffee \
    https://www.youtube.com/watch?v=VIDEO1 \
    https://www.youtube.com/watch?v=VIDEO2 \
    https://www.youtube.com/watch?v=VIDEO3
```

### Performance Tuning
```bash
# Concurrency (adjust based on hardware)
IO_WORKERS=12  # Parallel downloads
ASR_WORKERS=2  # Parallel transcription (GPU-bound)
DB_WORKERS=12  # Parallel database operations

# Whisper model
WHISPER_MODEL=distil-large-v3  # Fast, accurate
WHISPER_COMPUTE_TYPE=int8_float16  # Quantized for speed
```

## Ingestion Commands

### Process specific video (testing)
```bash
python backend/scripts/ingest_youtube.py \
    --from-url https://www.youtube.com/watch?v=VIDEO_ID \
    --force
```

### Process channel (production)
```bash
python backend/scripts/ingest_youtube.py \
    --channel-url https://www.youtube.com/@anthonychaffeemd \
    --limit 100 \
    --newest-first
```

### Reprocess existing videos
```bash
python backend/scripts/ingest_youtube.py \
    --channel-url https://www.youtube.com/@anthonychaffeemd \
    --force \
    --limit 10
```

## Data Storage Strategy

### Current Configuration (Recommended for MVP)
- **Text embeddings**: Store for ALL segments (Chaffee + Guest)
  - Enables semantic search across all content
  - ~1.5GB per 100 videos (1536-dim embeddings)
  
- **Voice embeddings**: Store for ALL segments (Chaffee + Guest)
  - Enables future speaker identification improvements
  - ~192-dim per segment (much smaller than text)
  - Allows re-identification without re-processing audio

### Why Store Guest Embeddings?
1. **Future optimization**: Can improve speaker detection algorithms without reprocessing
2. **Quality assurance**: Can verify speaker attribution accuracy
3. **Minimal cost**: Voice embeddings are small (192-dim vs 1536-dim text)
4. **No MVP blocker**: Doesn't affect deployment timeline

## Expected Performance Metrics

### RTX 5080 (Target Hardware)
- **Real-Time Factor**: 0.15-0.22 (5-7x faster than real-time)
- **Throughput**: ~50 hours audio per hour
- **GPU Utilization**: 60-90%
- **VRAM Usage**: 6-9GB peak

### Processing Times (10-minute video)
- Download: ~10-15s
- Transcription + Diarization: ~30-40s
- Embedding generation: ~5-10s
- Database insertion: ~1-2s
- **Total**: ~45-60s per video

## Database Schema

### Segments Table
```sql
CREATE TABLE segments (
    id UUID PRIMARY KEY,
    video_id VARCHAR(255) NOT NULL,
    speaker_label VARCHAR(50),  -- 'Chaffee' or 'Guest'
    text TEXT NOT NULL,
    embedding VECTOR(1536),  -- Text embedding for semantic search
    voice_embedding JSONB,  -- Voice embedding for speaker ID (192-dim)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_segments_video_id ON segments(video_id);
CREATE INDEX idx_segments_speaker ON segments(speaker_label);
CREATE INDEX idx_segments_embedding ON segments USING ivfflat (embedding vector_cosine_ops);
```

## Verification Commands

### Check voice embedding coverage
```bash
python check_voice_embeddings.py
```

### Check database stats
```sql
SELECT 
    speaker_label,
    COUNT(*) as total,
    COUNT(embedding) as with_text_emb,
    COUNT(voice_embedding) as with_voice_emb
FROM segments
GROUP BY speaker_label;
```

### Expected output (healthy system)
```
speaker_label | total | with_text_emb | with_voice_emb
--------------+-------+---------------+----------------
Chaffee       |   500 |           500 |            500
Guest         |   200 |           200 |            200
```

## Troubleshooting

### Voice embeddings missing for Guest
- **Symptom**: Guest segments have <100% voice embedding coverage
- **Fix**: Applied in `enhanced_asr.py` - best-match overlap strategy with fallback
- **Verify**: Run `python check_voice_embeddings.py`

### Slow embedding generation
- **Symptom**: <50 texts/sec embedding speed
- **Fix**: Ensure `EMBEDDING_DEVICE=cuda` and GPU is available
- **Verify**: Check logs for "GPU acceleration enabled"

### CUDA OOM errors
- **Symptom**: "CUDA out of memory" during processing
- **Fix**: Reduce batch sizes or use smaller model
- **Workaround**: Process videos sequentially (`ASR_WORKERS=1`)

## Pre-Deployment Checklist

- [ ] Chaffee voice profile created and validated
- [ ] Environment variables configured correctly
- [ ] Database schema created with indexes
- [ ] Test video processed successfully (100% embedding coverage)
- [ ] GPU acceleration verified for embeddings
- [ ] Performance metrics meet targets (RTF < 0.25)
- [ ] Backup strategy in place for database
- [ ] Monitoring configured (GPU usage, processing times)

## Post-Deployment Monitoring

### Key Metrics to Track
1. **Processing success rate**: >95% videos processed without errors
2. **Voice embedding coverage**: 100% for both Chaffee and Guest
3. **Text embedding coverage**: 100% for all segments
4. **Average processing time**: <60s per 10-minute video
5. **GPU utilization**: 60-90% during processing

### Alert Thresholds
- Processing failures >5%
- Voice embedding coverage <95%
- Processing time >120s per 10-minute video
- GPU utilization <50% (underutilized) or >95% (overloaded)

## Future Optimizations (Post-MVP)

1. **Speaker identification improvements**
   - Use stored voice embeddings to retrain/refine speaker detection
   - No need to reprocess audio - just re-run identification on stored embeddings

2. **Embedding model upgrades**
   - Can regenerate text embeddings with better models
   - Voice embeddings remain stable (ECAPA-TDNN is mature)

3. **Multi-speaker conversations**
   - Current system handles 2 speakers (Chaffee + Guest)
   - Can extend to N speakers using stored voice embeddings

## Support

For issues during deployment:
1. Check logs in `backend/logs/`
2. Run verification scripts (`check_voice_embeddings.py`, `check_schema.py`)
3. Verify GPU availability: `nvidia-smi`
4. Check database connectivity: `psql $DATABASE_URL`
