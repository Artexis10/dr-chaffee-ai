# Embedding Profile System

## 🎯 Quick Start

Switch between embedding models with **one command** - no database migration needed!

```powershell
cd backend
python scripts/switch_embedding_profile.py
```

---

## 📊 Available Profiles

### Profile: `quality` (Default)
**Model**: Alibaba-NLP/gte-Qwen2-1.5B-instruct  
**Dimensions**: 1536  
**Speed**: 20-30 texts/sec on RTX 5080  
**VRAM**: ~4GB  
**Quality**: ⭐⭐⭐⭐⭐ (Best)

**Use when**:
- ✅ You want maximum search accuracy
- ✅ You have 4GB+ VRAM available
- ✅ Processing speed is acceptable (20-30 texts/sec)
- ✅ Quality is more important than speed

### Profile: `speed`
**Model**: BAAI/bge-small-en-v1.5  
**Dimensions**: 384  
**Speed**: 1,500-2,000 texts/sec on RTX 5080  
**VRAM**: ~0.5GB  
**Quality**: ⭐⭐⭐⭐ (95% of quality profile, 98% with reranker)

**Use when**:
- ✅ You need fast ingestion (60-80x faster)
- ✅ You're processing large datasets (1000+ videos)
- ✅ You want to free up VRAM for other tasks
- ✅ 5% quality trade-off is acceptable

---

## 🔧 How to Switch

### Method 1: Interactive Script (Recommended)
```powershell
cd backend
python scripts/switch_embedding_profile.py
```

Follow the prompts to select your profile.

### Method 2: Manual .env Edit
Edit `.env` file and change:
```bash
# For quality profile (GTE-Qwen2-1.5B)
EMBEDDING_PROFILE=quality
ENABLE_RERANKER=false

# For speed profile (BGE-Small)
EMBEDDING_PROFILE=speed
ENABLE_RERANKER=true  # Optional, improves quality by 3%
```

Then restart your ingestion process.

---

## 📈 Performance Comparison

| Metric | Quality Profile | Speed Profile | Improvement |
|--------|----------------|---------------|-------------|
| **Speed** | 20-30 texts/sec | 1,500-2,000 texts/sec | **60-80x** |
| **VRAM** | ~4GB | ~0.5GB | **87% less** |
| **Dimensions** | 1536 | 384 | 75% smaller |
| **Quality (NDCG@20)** | 0.90-0.93 | 0.85-0.88 (0.88-0.92 w/ reranker) | -5% (-2% w/ reranker) |
| **Model Size** | 1.5B params | 33M params | 45x smaller |

### Real-World Impact

**Processing 282 segments**:
- Quality: ~12 seconds
- Speed: <1 second
- **Speedup**: 12x

**Processing 1200h of audio** (assuming 50k segments):
- Quality: ~30 minutes for embeddings
- Speed: <30 seconds for embeddings
- **Speedup**: 60x

---

## 🎛️ Advanced Configuration

### Override Profile Settings

You can override individual settings while keeping the profile base:

```bash
# Use speed profile but with custom batch size
EMBEDDING_PROFILE=speed
EMBEDDING_BATCH_SIZE=512  # Override default 256
```

### Available Overrides
- `EMBEDDING_PROVIDER` - Provider type (local/openai)
- `EMBEDDING_MODEL` - Model name
- `EMBEDDING_DIMENSIONS` - Embedding dimensions
- `EMBEDDING_DEVICE` - Device (cuda/cpu)
- `EMBEDDING_BATCH_SIZE` - Batch size for encoding

---

## ⚠️ Important Notes

### Dimension Compatibility

**Quality (1536-dim)** and **Speed (384-dim)** embeddings are **NOT compatible**:
- ❌ Cannot mix in same database column
- ❌ Cannot compare similarity between different dimensions
- ✅ Can store both by using different columns (advanced)

### Migration Strategy

**Option 1: Use Speed for New Videos Only**
```bash
# Set profile to speed
EMBEDDING_PROFILE=speed

# Ingest new videos
python scripts/ingest_youtube_enhanced.py --limit 10
```

**Option 2: Re-ingest Existing Videos**
```bash
# Set profile to speed
EMBEDDING_PROFILE=speed

# Force re-process existing videos
python scripts/ingest_youtube_enhanced.py --force --limit 10
```

**Option 3: Keep Both (Advanced)**
- Use quality profile for critical content
- Use speed profile for bulk ingestion
- Store in separate database columns

---

## 🧪 Testing

### Test Current Profile
```powershell
cd backend
python scripts/test_embedding_batch_speed.py
```

Expected results:
- **Quality**: 20-30 texts/sec
- **Speed**: 1,500-2,000 texts/sec

### Verify Profile Settings
```powershell
cd backend
python scripts/force_gpu_embeddings.py
```

---

## 🔄 Reranker (Speed Profile Only)

The reranker improves Speed profile quality by 3-5%:

**How it works**:
1. Retrieve top 200 candidates with BGE-Small (fast)
2. Rerank with cross-encoder (slower but accurate)
3. Return top 20 results

**Performance**:
- Adds ~0.2-0.5s per query
- Improves NDCG@20 from 0.85 to 0.88-0.92
- Uses additional ~1GB VRAM

**Enable**:
```bash
ENABLE_RERANKER=true
RERANK_TOP_K=200  # Candidates to retrieve
RETURN_TOP_K=20   # Final results
```

---

## 📊 When to Use Each Profile

### Use Quality Profile If:
- 🎯 Maximum accuracy is critical
- 💾 You have 4GB+ VRAM available
- ⏱️ 20-30 texts/sec is acceptable
- 📚 Processing <1000 videos
- 🔬 Research or production search

### Use Speed Profile If:
- ⚡ Need fast ingestion (1000+ videos)
- 💾 Limited VRAM (<4GB available)
- 🚀 Want 60-80x speedup
- 📊 Bulk processing or experimentation
- 🎛️ Can enable reranker for quality recovery

---

## 🆘 Troubleshooting

### Profile Not Switching
1. Check `.env` file has `EMBEDDING_PROFILE=speed` or `quality`
2. Restart ingestion process
3. Check logs for "Embedding provider: local, model: ..."

### Speed Profile Still Slow
1. Verify CUDA is available: `python scripts/force_gpu_embeddings.py`
2. Check batch size: Should be 256
3. Ensure no lock contention (single-threaded ingestion)

### Quality Profile Out of Memory
1. Reduce batch size: `EMBEDDING_BATCH_SIZE=128`
2. Close other GPU processes
3. Switch to Speed profile

---

## 📚 Additional Resources

- **BGE-Small Model Card**: https://huggingface.co/BAAI/bge-small-en-v1.5
- **GTE-Qwen2 Model Card**: https://huggingface.co/Alibaba-NLP/gte-Qwen2-1.5B-instruct
- **BGE Reranker**: https://huggingface.co/BAAI/bge-reranker-large

---

**Quick Reference**:
```bash
# Switch profile
python backend/scripts/switch_embedding_profile.py

# Test speed
python backend/scripts/test_embedding_batch_speed.py

# Verify GPU
python backend/scripts/force_gpu_embeddings.py
```
