#!/usr/bin/env python3
"""
Simple embedding service for frontend queries
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
from pathlib import Path
from typing import List

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

class EmbedRequest(BaseModel):
    text: str

class EmbedResponse(BaseModel):
    embedding: List[float]
    dimensions: int

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("EMBEDDING_SERVICE_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
