# Backend API Schema

This document describes all public endpoints exposed by the FastAPI backend.

---

## Core Endpoints

### `GET /`
Root endpoint for basic service check.

**Response:**
```json
{
  "status": "ok",
  "service": "Ask Dr. Chaffee API"
}
```

---

### `GET /health`
Health check endpoint for production monitoring. Checks database and embedding service.

**Response (200 OK):**
```json
{
  "status": "ok",
  "service": "Ask Dr. Chaffee API",
  "timestamp": "2025-11-25T12:00:00.000000",
  "checks": {
    "database": "ok",
    "embeddings": "ok"
  }
}
```

**Response (503 Degraded):**
```json
{
  "status": "degraded",
  "checks": {
    "database": "degraded",
    "embeddings": "ok"
  }
}
```

---

### `GET /stats`
Get database statistics for segments and embeddings.

**Response:**
```json
{
  "total_segments": 514000,
  "total_videos": 1200,
  "segments_with_embeddings": 514000,
  "segments_missing_embeddings": 0,
  "embedding_coverage": "100.0%",
  "embedding_dimensions": 384,
  "timestamp": "2025-11-25T12:00:00.000000"
}
```

---

## Search & Answering

### `POST /search`
Semantic search with optional reranking.

**Request Body:**
```json
{
  "query": "carnivore diet benefits",
  "top_k": 50,
  "min_similarity": 0.5,
  "rerank": true
}
```

**Response:**
```json
{
  "results": [
    {
      "id": 12345,
      "video_id": "abc123",
      "title": "Video Title",
      "text": "Segment text...",
      "url": "https://youtube.com/watch?v=abc123",
      "start_time_seconds": 120.5,
      "end_time_seconds": 145.2,
      "published_at": "2024-06-15T00:00:00",
      "source_type": "youtube",
      "similarity": 0.85
    }
  ],
  "query": "carnivore diet benefits",
  "total_results": 50,
  "embedding_dimensions": 384
}
```

---

### `GET /search`
GET variant for search (frontend compatibility).

**Query Parameters:**
- `q` (required): Search query
- `top_k` (optional, default: 50): Number of results
- `min_similarity` (optional, default: 0.5): Minimum similarity threshold

---

### `POST /answer`
Generate AI-powered answer using RAG with OpenAI.

**Request Body:**
```json
{
  "query": "What does Dr. Chaffee say about autoimmune conditions?",
  "style": "concise",
  "top_k": 50
}
```

**Response:**
```json
{
  "answer": "AI-generated answer text...",
  "sources": [
    {
      "id": 12345,
      "title": "Video Title",
      "url": "https://youtube.com/watch?v=abc123",
      "start_time": 120.5,
      "similarity": 0.85
    }
  ],
  "query": "What does Dr. Chaffee say about autoimmune conditions?",
  "chunks_used": 10,
  "cost_usd": 0.0042
}
```

---

### `POST /answer/chunks`
Get relevant chunks for RAG answer generation.

**Request Body:**
```json
{
  "query": "carnivore diet",
  "top_k": 100,
  "use_semantic": true
}
```

**Response:**
```json
{
  "chunks": [
    {
      "id": 12345,
      "source_id": 100,
      "video_id": "abc123",
      "title": "Video Title",
      "text": "Segment text...",
      "start_time_seconds": 120.5,
      "end_time_seconds": 145.2,
      "published_at": "2024-06-15T00:00:00",
      "source_type": "youtube",
      "similarity": 0.85
    }
  ],
  "total": 100,
  "query": "carnivore diet"
}
```

---

### `POST /answer/cache/lookup`
Look up cached answer by semantic similarity.

**Request Body:**
```json
{
  "query": "carnivore diet benefits",
  "style": "concise",
  "similarity_threshold": 0.92
}
```

**Response (cache hit):**
```json
{
  "cached": {
    "id": 123,
    "query_text": "carnivore diet benefits",
    "answer_md": "Cached answer text...",
    "citations": [...],
    "confidence": 0.85,
    "notes": null,
    "used_chunk_ids": ["abc:120", "def:45"],
    "source_clips": [...],
    "created_at": "2025-11-20T10:00:00",
    "access_count": 5,
    "similarity": 0.95
  }
}
```

**Response (cache miss):**
```json
{
  "cached": null
}
```

---

### `POST /answer/cache/save`
Save answer to cache with embedding for semantic lookup.

**Request Body:**
```json
{
  "query": "carnivore diet benefits",
  "style": "concise",
  "answer_md": "Answer text...",
  "citations": [...],
  "confidence": 0.85,
  "notes": null,
  "used_chunk_ids": ["abc:120"],
  "source_clips": [...],
  "ttl_hours": 336
}
```

**Response:**
```json
{
  "success": true,
  "cache_id": 123
}
```

---

## Embeddings

### `POST /embed`
Generate embedding for a text.

**Request Body:**
```json
{
  "text": "carnivore diet"
}
```

**Response:**
```json
{
  "embedding": [0.123, -0.456, ...],
  "dimensions": 384,
  "text": "carnivore diet"
}
```

---

### `GET /embeddings/models`
List available embedding models in the database.

**Response:**
```json
{
  "models": [
    {
      "model_key": "bge-small-en-v1.5",
      "dimensions": 384,
      "count": 514000
    }
  ]
}
```

---

### `GET /embeddings/active`
Get the currently active embedding model.

**Response:**
```json
{
  "active_model": "bge-small-en-v1.5"
}
```

---

## Ingestion (Admin)

All ingestion endpoints require admin authentication via Bearer token.

### `POST /api/upload/youtube-takeout`
Upload and process Google Takeout ZIP with YouTube captions.

**Headers:**
- `Authorization: Bearer <ADMIN_API_KEY>`

**Request:** Multipart form with ZIP file

**Response:**
```json
{
  "job_id": "uuid",
  "message": "Upload started",
  "status": "pending"
}
```

---

### `POST /api/upload/zoom-transcripts`
Upload and process Zoom transcript files (VTT, SRT, TXT).

**Headers:**
- `Authorization: Bearer <ADMIN_API_KEY>`

**Request:** Multipart form with transcript files

---

### `POST /api/upload/manual-transcripts`
Upload and process manual transcript files.

**Headers:**
- `Authorization: Bearer <ADMIN_API_KEY>`

---

### `POST /api/sync/new-videos`
Manually trigger sync of new YouTube videos.

**Headers:**
- `Authorization: Bearer <ADMIN_API_KEY>`

**Query Parameters:**
- `limit` (optional, default: 10): Max videos to sync
- `use_proxy` (optional, default: true): Use proxy for downloads

---

## Jobs

### `GET /api/jobs`
List all processing jobs (requires admin auth).

**Headers:**
- `Authorization: Bearer <ADMIN_API_KEY>`

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "uuid",
      "status": "completed",
      "source_type": "youtube_takeout",
      "total_files": 100,
      "processed_files": 100,
      "failed_files": 0,
      "created_at": "2025-11-25T10:00:00",
      "completed_at": "2025-11-25T11:00:00"
    }
  ]
}
```

---

### `GET /api/jobs/{job_id}`
Get status of a specific job (no auth required).

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "total_files": 100,
  "processed_files": 45,
  "failed_files": 2,
  "current_file": "video_123.srt",
  "errors": ["Error message 1"]
}
```

---

## Tuning

Custom instructions and AI tuning endpoints are available under `/api/tuning/`.
See `backend/api/tuning.py` for full documentation.

### Key Endpoints:
- `GET /api/tuning/instructions` - List all instruction sets
- `GET /api/tuning/instructions/active` - Get active instruction set
- `POST /api/tuning/instructions` - Create new instruction set
- `PUT /api/tuning/instructions/{id}` - Update instruction set
- `POST /api/tuning/instructions/{id}/activate` - Activate instruction set
- `POST /api/tuning/instructions/preview` - Preview merged prompt
- `GET /api/tuning/instructions/{id}/history` - Get version history
- `POST /api/tuning/instructions/{id}/rollback/{version}` - Rollback to version

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (invalid/missing auth token)
- `404` - Not Found
- `500` - Internal Server Error
- `503` - Service Unavailable (database/embedding service down)
