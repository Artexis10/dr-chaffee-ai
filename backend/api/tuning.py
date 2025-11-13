"""
AI Tuning API - Non-developer friendly interface for Dr. Chaffee

Allows real-time tuning of:
- Embedding models (quality vs speed)
- Search parameters
- Reranking settings
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tuning", tags=["tuning"])

# Path to embedding models config
EMBEDDING_MODELS_PATH = Path(__file__).parent.parent / "config" / "embedding_models.json"


class EmbeddingModelInfo(BaseModel):
    """Information about an embedding model"""
    key: str
    provider: str
    model_name: str
    dimensions: int
    cost_per_1k: float
    description: str
    is_active_query: bool = False
    is_active_ingestion: bool = False


class SearchConfig(BaseModel):
    """Search configuration parameters"""
    top_k: int = Field(default=20, ge=1, le=100, description="Number of results to return")
    similarity_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")
    enable_reranker: bool = Field(default=False, description="Enable cross-encoder reranking")
    rerank_top_k: int = Field(default=200, ge=1, le=500, description="Candidates for reranking")


class TuningConfig(BaseModel):
    """Complete tuning configuration"""
    active_query_model: str
    active_ingestion_models: List[str]
    search_config: SearchConfig


class TestSearchRequest(BaseModel):
    """Test search with current config"""
    query: str
    model_key: Optional[str] = None  # Override active model for testing
    top_k: Optional[int] = None


class TestSearchResult(BaseModel):
    """Search result for testing"""
    text: str
    similarity: float
    source_id: int
    youtube_id: str
    start_sec: float
    end_sec: float
    speaker_label: Optional[str] = None


def load_embedding_models() -> Dict[str, Any]:
    """Load embedding models configuration"""
    try:
        with open(EMBEDDING_MODELS_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load embedding models config: {e}")
        raise HTTPException(status_code=500, detail="Failed to load configuration")


def save_embedding_models(config: Dict[str, Any]) -> None:
    """Save embedding models configuration"""
    try:
        with open(EMBEDDING_MODELS_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Embedding models configuration saved")
    except Exception as e:
        logger.error(f"Failed to save embedding models config: {e}")
        raise HTTPException(status_code=500, detail="Failed to save configuration")


@router.get("/models", response_model=List[EmbeddingModelInfo])
async def list_models():
    """
    List all available embedding models with their configurations
    """
    config = load_embedding_models()
    models = config.get("models", {})
    active_query = config.get("active_query_model")
    active_ingestion = config.get("active_ingestion_models", [])
    
    result = []
    for key, model_data in models.items():
        result.append(EmbeddingModelInfo(
            key=key,
            provider=model_data["provider"],
            model_name=model_data["model_name"],
            dimensions=model_data["dimensions"],
            cost_per_1k=model_data["cost_per_1k"],
            description=model_data["description"],
            is_active_query=(key == active_query),
            is_active_ingestion=(key in active_ingestion)
        ))
    
    return result


@router.get("/config", response_model=TuningConfig)
async def get_config():
    """
    Get current tuning configuration
    """
    config = load_embedding_models()
    
    # Get search config from environment
    search_config = SearchConfig(
        top_k=int(os.getenv("ANSWER_TOPK", "20")),
        similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.0")),
        enable_reranker=os.getenv("ENABLE_RERANKER", "false").lower() == "true",
        rerank_top_k=int(os.getenv("RERANK_TOP_K", "200"))
    )
    
    return TuningConfig(
        active_query_model=config.get("active_query_model", "nomic-v1.5"),
        active_ingestion_models=config.get("active_ingestion_models", ["nomic-v1.5"]),
        search_config=search_config
    )


@router.post("/models/query")
async def set_query_model(model_key: str):
    """
    Set the active query model (instant switch if embeddings exist)
    """
    config = load_embedding_models()
    models = config.get("models", {})
    
    if model_key not in models:
        raise HTTPException(status_code=404, detail=f"Model '{model_key}' not found")
    
    config["active_query_model"] = model_key
    save_embedding_models(config)
    
    return {
        "success": True,
        "message": f"Query model switched to '{model_key}'",
        "model": models[model_key]
    }


@router.post("/models/ingestion")
async def set_ingestion_models(model_keys: List[str]):
    """
    Set the active ingestion models (requires re-ingestion to generate embeddings)
    """
    config = load_embedding_models()
    models = config.get("models", {})
    
    # Validate all model keys
    for key in model_keys:
        if key not in models:
            raise HTTPException(status_code=404, detail=f"Model '{key}' not found")
    
    config["active_ingestion_models"] = model_keys
    save_embedding_models(config)
    
    return {
        "success": True,
        "message": f"Ingestion models set to: {', '.join(model_keys)}",
        "note": "Run ingestion to generate embeddings for new models"
    }


@router.post("/search/config")
async def update_search_config(config: SearchConfig):
    """
    Update search configuration parameters
    
    Note: This updates the in-memory config. For persistence, update .env file.
    """
    # Update environment variables (runtime only)
    os.environ["ANSWER_TOPK"] = str(config.top_k)
    os.environ["SIMILARITY_THRESHOLD"] = str(config.similarity_threshold)
    os.environ["ENABLE_RERANKER"] = "true" if config.enable_reranker else "false"
    os.environ["RERANK_TOP_K"] = str(config.rerank_top_k)
    
    return {
        "success": True,
        "message": "Search configuration updated",
        "config": config.dict(),
        "note": "Changes are runtime-only. Update .env file for persistence."
    }


@router.post("/search/test", response_model=List[TestSearchResult])
async def test_search(request: TestSearchRequest):
    """
    Test search with current or specified model
    """
    from ..services.embeddings_service import EmbeddingsService
    import psycopg2
    
    try:
        # Get active model or use override
        config = load_embedding_models()
        model_key = request.model_key or config.get("active_query_model")
        
        # Generate query embedding
        embeddings_service = EmbeddingsService.get_instance()
        query_embedding = embeddings_service.encode_text(request.query)
        
        # Search database
        top_k = request.top_k or int(os.getenv("ANSWER_TOPK", "20"))
        
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        try:
            with conn.cursor() as cur:
                # Use pgvector cosine similarity search with JOIN to get YouTube ID
                cur.execute("""
                    SELECT 
                        s.text,
                        1 - (s.embedding <=> %s::vector) as similarity,
                        s.source_id,
                        src.source_id as youtube_id,
                        s.start_sec,
                        s.end_sec,
                        s.speaker_label
                    FROM segments s
                    JOIN sources src ON s.source_id = src.id
                    WHERE s.embedding IS NOT NULL
                    ORDER BY s.embedding <=> %s::vector
                    LIMIT %s
                """, (query_embedding.tolist(), query_embedding.tolist(), top_k))
                
                results = []
                for row in cur.fetchall():
                    results.append(TestSearchResult(
                        text=row[0],
                        similarity=float(row[1]),
                        source_id=row[2],
                        youtube_id=row[3],
                        start_sec=float(row[4]),
                        end_sec=float(row[5]),
                        speaker_label=row[6]
                    ))
                
                return results
        finally:
            conn.close()
                
    except Exception as e:
        logger.error(f"Test search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """
    Get ingestion and embedding statistics
    """
    import psycopg2
    
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        try:
            with conn.cursor() as cur:
                # Get segment counts
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_segments,
                        COUNT(DISTINCT source_id) as total_videos,
                        COUNT(embedding) as segments_with_embeddings,
                        COUNT(DISTINCT speaker_label) as unique_speakers
                    FROM segments
                """)
                stats = cur.fetchone()
                
                # Get embedding dimension info
                cur.execute("""
                    SELECT vector_dims(embedding) as dimensions
                    FROM segments
                    WHERE embedding IS NOT NULL
                    LIMIT 1
                """)
                dim_row = cur.fetchone()
                dimensions = dim_row[0] if dim_row else None
                
                return {
                    "total_segments": stats[0],
                    "total_videos": stats[1],
                    "segments_with_embeddings": stats[2],
                    "unique_speakers": stats[3],
                    "embedding_dimensions": dimensions,
                    "embedding_coverage": f"{(stats[2] / stats[0] * 100):.1f}%" if stats[0] > 0 else "0%"
                }
        finally:
            conn.close()
                
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
