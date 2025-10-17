#!/usr/bin/env python3
"""
Embedding and semantic search service for frontend queries
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
from pathlib import Path
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend scripts to path
backend_path = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(backend_path))

from common.embeddings import EmbeddingGenerator

app = FastAPI(title="Embedding Service")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize embedding generator (lazy load)
_embedding_generator = None

def get_embedding_generator():
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        os.getenv('DATABASE_URL'),
        cursor_factory=RealDictCursor
    )

# Request/Response models
class EmbedRequest(BaseModel):
    text: str

class EmbedResponse(BaseModel):
    embedding: List[float]
    dimensions: int

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 50
    min_similarity: Optional[float] = 0.5
    rerank: Optional[bool] = True

class SearchResult(BaseModel):
    id: int
    video_id: str
    title: str
    text: str
    start_time_seconds: float
    end_time_seconds: float
    published_at: str
    source_type: str
    similarity: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str
    total_results: int
    embedding_dimensions: int

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "embedding"}

@app.post("/embed", response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    """Generate embedding for a single text query"""
    try:
        generator = get_embedding_generator()
        embeddings = generator.generate_embeddings([request.text])
        
        if not embeddings or len(embeddings) == 0:
            raise HTTPException(status_code=500, detail="Failed to generate embedding")
        
        embedding = embeddings[0]
        
        return EmbedResponse(
            embedding=embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
            dimensions=len(embedding)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

@app.post("/search", response_model=SearchResponse)
async def semantic_search(request: SearchRequest):
    """
    Semantic search with optional reranking
    
    1. Generate query embedding
    2. Search database using vector similarity
    3. Optionally rerank results for better quality
    """
    try:
        # Generate query embedding
        generator = get_embedding_generator()
        embeddings = generator.generate_embeddings([request.query])
        
        if not embeddings or len(embeddings) == 0:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        
        query_embedding = embeddings[0]
        embedding_dim = len(query_embedding)
        
        # Determine which embedding column to use based on dimensions
        embedding_column = 'embedding' if embedding_dim == 1536 else 'embedding'
        
        # Connect to database
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Semantic search query
        # Filter for Chaffee-only segments and use vector similarity
        search_query = f"""
            SELECT 
                seg.id,
                seg.video_id,
                s.title,
                seg.text,
                seg.start_sec as start_time_seconds,
                seg.end_sec as end_time_seconds,
                s.published_at,
                s.source_type,
                1 - (seg.{embedding_column} <=> %s::vector) as similarity
            FROM segments seg
            JOIN sources s ON seg.video_id = s.source_id
            WHERE seg.speaker_label = 'Chaffee'
              AND seg.{embedding_column} IS NOT NULL
              AND 1 - (seg.{embedding_column} <=> %s::vector) >= %s
            ORDER BY similarity DESC
            LIMIT %s
        """
        
        # Convert embedding to list for JSON serialization
        embedding_list = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding
        
        cur.execute(search_query, [
            str(embedding_list),
            str(embedding_list),
            request.min_similarity,
            request.top_k
        ])
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        # Optional: Simple reranking based on text relevance
        if request.rerank and len(results) > 0:
            # Extract query keywords
            query_lower = request.query.lower()
            query_words = set(query_lower.split())
            
            # Add text relevance score
            for result in results:
                text_lower = result['text'].lower()
                # Count keyword matches
                keyword_matches = sum(1 for word in query_words if word in text_lower)
                # Boost similarity based on keyword presence
                keyword_boost = min(0.1, keyword_matches * 0.02)  # Max 10% boost
                result['similarity'] = min(1.0, result['similarity'] + keyword_boost)
            
            # Re-sort by adjusted similarity
            results = sorted(results, key=lambda x: x['similarity'], reverse=True)
        
        # Convert to response format
        search_results = [
            SearchResult(
                id=r['id'],
                video_id=r['video_id'],
                title=r['title'],
                text=r['text'],
                start_time_seconds=float(r['start_time_seconds']),
                end_time_seconds=float(r['end_time_seconds']),
                published_at=r['published_at'].isoformat() if r['published_at'] else '',
                source_type=r['source_type'],
                similarity=float(r['similarity'])
            )
            for r in results
        ]
        
        return SearchResponse(
            results=search_results,
            query=request.query,
            total_results=len(search_results),
            embedding_dimensions=embedding_dim
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("EMBEDDING_SERVICE_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
