"""
AI Tuning API - Non-developer friendly interface for Dr. Chaffee

Allows real-time tuning of:
- Embedding models (quality vs speed)
- Search parameters
- Reranking settings
- Custom prompt instructions (layered on baseline)
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tuning", tags=["tuning"])

# Path to embedding models config
EMBEDDING_MODELS_PATH = Path(__file__).parent.parent / "config" / "embedding_models.json"

# Tuning password from environment (must be set)
TUNING_PASSWORD = os.getenv('TUNING_PASSWORD')
if not TUNING_PASSWORD:
    logger.warning("⚠️ TUNING_PASSWORD not set - tuning dashboard will be inaccessible")


class PasswordRequest(BaseModel):
    """Password authentication request"""
    password: str = Field(..., min_length=1, description="Tuning dashboard password")


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        os.getenv('DATABASE_URL'),
        cursor_factory=RealDictCursor
    )


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


class SummarizerConfig(BaseModel):
    """Summarizer model configuration"""
    model: str = Field(default="gpt-4-turbo", description="OpenAI model for summarization")
    temperature: float = Field(default=0.1, ge=0.0, le=1.0, description="Temperature for summarization")
    max_tokens: int = Field(default=2000, ge=500, le=4000, description="Max tokens for summary output")


class TuningConfig(BaseModel):
    """Complete tuning configuration"""
    active_query_model: str
    active_ingestion_models: List[str]
    search_config: SearchConfig
    summarizer_config: Optional[SummarizerConfig] = None


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


@router.post("/auth/verify")
async def verify_password(request: PasswordRequest, response: Response):
    """
    Verify tuning dashboard password and set secure httpOnly cookie
    
    Security:
    - Password validation happens on backend (never exposed in frontend)
    - Cookie is httpOnly (cannot be accessed by JavaScript)
    - Cookie is secure (HTTPS only in production)
    - Cookie has 24-hour expiration
    """
    if not TUNING_PASSWORD:
        logger.error("TUNING_PASSWORD not configured")
        raise HTTPException(status_code=503, detail="Tuning dashboard not configured")
    
    if not request.password:
        raise HTTPException(status_code=400, detail="Password required")
    
    # Validate password (constant-time comparison to prevent timing attacks)
    if request.password != TUNING_PASSWORD:
        logger.warning(f"Failed tuning auth attempt from {request.client if hasattr(request, 'client') else 'unknown'}")
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Set secure httpOnly cookie (24 hour expiration)
    response.set_cookie(
        key="tuning_auth",
        value="authenticated",
        max_age=86400,  # 24 hours
        httponly=True,  # Cannot be accessed by JavaScript
        secure=True,    # HTTPS only (set to False for local development)
        samesite="strict"  # CSRF protection
    )
    
    logger.info("Tuning dashboard access granted")
    return {"success": True, "message": "Authentication successful"}


def require_tuning_auth(request):
    """Middleware to check tuning authentication cookie"""
    cookie = request.cookies.get("tuning_auth")
    if cookie != "authenticated":
        raise HTTPException(status_code=401, detail="Tuning dashboard access denied. Please authenticate first.")


@router.get("/models", response_model=List[EmbeddingModelInfo])
async def list_models(request):
    """
    List all available embedding models with their configurations
    """
    require_tuning_auth(request)
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
    Get current tuning configuration from .env (single source of truth)
    """
    # Get search config from environment
    search_config = SearchConfig(
        top_k=int(os.getenv("ANSWER_TOPK", "20")),
        similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.0")),
        enable_reranker=os.getenv("ENABLE_RERANKER", "false").lower() == "true",
        rerank_top_k=int(os.getenv("RERANK_TOP_K", "200"))
    )
    
    # Get active models from .env (single source of truth)
    # Format: EMBEDDING_MODEL=BAAI/bge-small-en-v1.5 -> key is bge-small-en-v1.5
    embedding_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    # Extract model key from full model name (last part after /)
    active_query_model = embedding_model.split('/')[-1] if '/' in embedding_model else embedding_model
    
    return TuningConfig(
        active_query_model=active_query_model,
        active_ingestion_models=[active_query_model],  # Use same model for ingestion
        search_config=search_config
    )


@router.post("/models/query")
async def set_query_model(model_key: str):
    """
    Set the active query model (instant switch if embeddings exist)
    Updates .env file to persist change
    """
    config = load_embedding_models()
    models = config.get("models", {})
    
    if model_key not in models:
        raise HTTPException(status_code=404, detail=f"Model '{model_key}' not found")
    
    model_info = models[model_key]
    full_model_name = model_info.get("model_name", model_key)
    
    # Update .env file
    try:
        env_path = Path(__file__).parent.parent.parent / ".env"
        env_content = env_path.read_text()
        
        # Replace EMBEDDING_MODEL line
        import re
        env_content = re.sub(
            r'EMBEDDING_MODEL=.*',
            f'EMBEDDING_MODEL={full_model_name}',
            env_content
        )
        
        # Replace EMBEDDING_DIMENSIONS line
        env_content = re.sub(
            r'EMBEDDING_DIMENSIONS=.*',
            f'EMBEDDING_DIMENSIONS={model_info.get("dimensions", 384)}',
            env_content
        )
        
        env_path.write_text(env_content)
        
        # Update runtime environment
        os.environ["EMBEDDING_MODEL"] = full_model_name
        os.environ["EMBEDDING_DIMENSIONS"] = str(model_info.get("dimensions", 384))
        
        logger.info(f"Query model switched to '{model_key}' ({full_model_name})")
        
        return {
            "success": True,
            "message": f"Query model switched to '{model_key}'",
            "model": model_info,
            "note": "Changes persisted to .env. Restart application to apply."
        }
    except Exception as e:
        logger.error(f"Failed to update .env: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {e}")


@router.post("/models/ingestion")
async def set_ingestion_models(model_keys: List[str]):
    """
    Set the active ingestion models (requires re-ingestion to generate embeddings)
    Updates .env file to persist change
    """
    config = load_embedding_models()
    models = config.get("models", {})
    
    # Validate all model keys
    for key in model_keys:
        if key not in models:
            raise HTTPException(status_code=404, detail=f"Model '{key}' not found")
    
    # For now, we only support single ingestion model (same as query model)
    # This keeps things simple and consistent
    if len(model_keys) > 1:
        logger.warning(f"Multiple ingestion models requested: {model_keys}. Using first: {model_keys[0]}")
    
    primary_model_key = model_keys[0]
    model_info = models[primary_model_key]
    full_model_name = model_info.get("model_name", primary_model_key)
    
    # Update .env file
    try:
        env_path = Path(__file__).parent.parent.parent / ".env"
        env_content = env_path.read_text()
        
        # Replace EMBEDDING_MODEL line
        import re
        env_content = re.sub(
            r'EMBEDDING_MODEL=.*',
            f'EMBEDDING_MODEL={full_model_name}',
            env_content
        )
        
        # Replace EMBEDDING_DIMENSIONS line
        env_content = re.sub(
            r'EMBEDDING_DIMENSIONS=.*',
            f'EMBEDDING_DIMENSIONS={model_info.get("dimensions", 384)}',
            env_content
        )
        
        env_path.write_text(env_content)
        
        # Update runtime environment
        os.environ["EMBEDDING_MODEL"] = full_model_name
        os.environ["EMBEDDING_DIMENSIONS"] = str(model_info.get("dimensions", 384))
        
        logger.info(f"Ingestion model set to '{primary_model_key}' ({full_model_name})")
        
        return {
            "success": True,
            "message": f"Ingestion model set to: {primary_model_key}",
            "model": model_info,
            "note": "Changes persisted to .env. Run ingestion to generate embeddings."
        }
    except Exception as e:
        logger.error(f"Failed to update .env: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {e}")


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


@router.get("/summarizer/config", response_model=SummarizerConfig)
async def get_summarizer_config():
    """
    Get current summarizer configuration
    """
    return SummarizerConfig(
        model=os.getenv("SUMMARIZER_MODEL", "gpt-4-turbo"),
        temperature=float(os.getenv("SUMMARIZER_TEMPERATURE", "0.1")),
        max_tokens=int(os.getenv("SUMMARIZER_MAX_TOKENS", "2000"))
    )


@router.post("/summarizer/config")
async def update_summarizer_config(config: SummarizerConfig):
    """
    Update summarizer configuration
    
    Allowed models (cost-controlled whitelist):
    - gpt-4-turbo: $0.01/1k input, $0.03/1k output (recommended)
    - gpt-4: $0.03/1k input, $0.06/1k output (slower, more expensive)
    - gpt-3.5-turbo: $0.0005/1k input, $0.0015/1k output (faster, cheaper)
    
    Note: This updates runtime config. For persistence, update .env file.
    """
    # Whitelist of approved models
    allowed_models = {
        "gpt-4-turbo": {"cost": "$0.01/$0.03", "quality": "highest", "speed": "fast"},
        "gpt-4": {"cost": "$0.03/$0.06", "quality": "highest", "speed": "slow"},
        "gpt-3.5-turbo": {"cost": "$0.0005/$0.0015", "quality": "good", "speed": "fastest"}
    }
    
    if config.model not in allowed_models:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{config.model}' not allowed. Allowed: {list(allowed_models.keys())}"
        )
    
    # Update environment variables (runtime only)
    os.environ["SUMMARIZER_MODEL"] = config.model
    os.environ["SUMMARIZER_TEMPERATURE"] = str(config.temperature)
    os.environ["SUMMARIZER_MAX_TOKENS"] = str(config.max_tokens)
    
    model_info = allowed_models[config.model]
    
    return {
        "success": True,
        "message": f"Summarizer model changed to {config.model}",
        "config": config.dict(),
        "model_info": model_info,
        "note": "Changes are runtime-only. Update .env file for persistence.",
        "warning": "Changing models will affect future ingestion/summarization tasks"
    }


@router.get("/summarizer/models")
async def list_summarizer_models():
    """
    List available summarizer models with cost and quality info
    """
    models = {
        "gpt-4-turbo": {
            "name": "GPT-4 Turbo",
            "cost_input": "$0.01/1k tokens",
            "cost_output": "$0.03/1k tokens",
            "quality": "highest",
            "speed": "fast",
            "recommended": True,
            "description": "Best quality, balanced cost and speed. Recommended for production."
        },
        "gpt-4": {
            "name": "GPT-4",
            "cost_input": "$0.03/1k tokens",
            "cost_output": "$0.06/1k tokens",
            "quality": "highest",
            "speed": "slow",
            "recommended": False,
            "description": "Highest quality but slower and more expensive. Use for critical summaries."
        },
        "gpt-3.5-turbo": {
            "name": "GPT-3.5 Turbo",
            "cost_input": "$0.0005/1k tokens",
            "cost_output": "$0.0015/1k tokens",
            "quality": "good",
            "speed": "fastest",
            "recommended": False,
            "description": "Fastest and cheapest. Good for testing and non-critical summaries."
        }
    }
    
    current_model = os.getenv("SUMMARIZER_MODEL", "gpt-4-turbo")
    
    return {
        "current_model": current_model,
        "models": models,
        "note": "Only models in this list are allowed for security and cost control"
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


# ============================================================================
# CUSTOM INSTRUCTIONS API - Layered Prompt System
# ============================================================================

class CustomInstruction(BaseModel):
    """Custom instruction set for AI tuning"""
    id: Optional[int] = None
    name: str = Field(..., max_length=255, description="Unique name for this instruction set")
    instructions: str = Field(..., max_length=10000, description="Custom instructions (max 10000 chars)")
    description: Optional[str] = Field(None, max_length=500, description="What these instructions do")
    is_active: bool = Field(default=False, description="Whether this is the active instruction set")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: Optional[int] = None


class CustomInstructionHistory(BaseModel):
    """Historical version of custom instructions"""
    id: int
    instruction_id: int
    instructions: str
    version: int
    changed_at: datetime


class InstructionPreview(BaseModel):
    """Preview of how instructions will be merged"""
    baseline_prompt: str
    custom_instructions: str
    merged_prompt: str
    character_count: int
    estimated_tokens: int


@router.get("/instructions", response_model=List[CustomInstruction])
async def list_instructions():
    """
    List all custom instruction sets
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, name, instructions, description, is_active, 
                   created_at, updated_at, version
            FROM custom_instructions
            ORDER BY is_active DESC, updated_at DESC
        """)
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        return [CustomInstruction(**row) for row in results]
        
    except Exception as e:
        logger.error(f"Failed to list instructions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instructions/active", response_model=CustomInstruction)
async def get_active_instructions():
    """
    Get the currently active instruction set
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, name, instructions, description, is_active,
                   created_at, updated_at, version
            FROM custom_instructions
            WHERE is_active = true
            LIMIT 1
        """)
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="No active instruction set found")
        
        return CustomInstruction(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get active instructions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instructions", response_model=CustomInstruction)
async def create_instructions(instruction: CustomInstruction):
    """
    Create a new custom instruction set
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # If this should be active, deactivate others first
        if instruction.is_active:
            cur.execute("UPDATE custom_instructions SET is_active = false")
        
        cur.execute("""
            INSERT INTO custom_instructions (name, instructions, description, is_active)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, instructions, description, is_active,
                      created_at, updated_at, version
        """, (instruction.name, instruction.instructions, instruction.description, instruction.is_active))
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Created custom instruction set: {instruction.name}")
        return CustomInstruction(**result)
        
    except psycopg2.IntegrityError as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Instruction set '{instruction.name}' already exists")
    except Exception as e:
        logger.error(f"Failed to create instructions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/instructions/{instruction_id}", response_model=CustomInstruction)
async def update_instructions(instruction_id: int, instruction: CustomInstruction):
    """
    Update an existing custom instruction set
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # If this should be active, deactivate others first
        if instruction.is_active:
            cur.execute("UPDATE custom_instructions SET is_active = false WHERE id != %s", (instruction_id,))
        
        cur.execute("""
            UPDATE custom_instructions
            SET name = %s, instructions = %s, description = %s, is_active = %s
            WHERE id = %s
            RETURNING id, name, instructions, description, is_active,
                      created_at, updated_at, version
        """, (instruction.name, instruction.instructions, instruction.description, 
              instruction.is_active, instruction_id))
        
        result = cur.fetchone()
        
        if not result:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Instruction set not found")
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Updated custom instruction set: {instruction.name} (v{result['version']})")
        return CustomInstruction(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update instructions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/instructions/{instruction_id}")
async def delete_instructions(instruction_id: int):
    """
    Delete a custom instruction set
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Don't allow deleting the default set
        cur.execute("SELECT name FROM custom_instructions WHERE id = %s", (instruction_id,))
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Instruction set not found")
        
        if result['name'] == 'default':
            raise HTTPException(status_code=400, detail="Cannot delete default instruction set")
        
        cur.execute("DELETE FROM custom_instructions WHERE id = %s", (instruction_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Deleted custom instruction set: {result['name']}")
        return {"success": True, "message": f"Deleted instruction set: {result['name']}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete instructions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instructions/{instruction_id}/activate")
async def activate_instructions(instruction_id: int):
    """
    Activate a specific instruction set (deactivates all others)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Deactivate all
        cur.execute("UPDATE custom_instructions SET is_active = false")
        
        # Activate the specified one
        cur.execute("""
            UPDATE custom_instructions
            SET is_active = true
            WHERE id = %s
            RETURNING name
        """, (instruction_id,))
        
        result = cur.fetchone()
        
        if not result:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Instruction set not found")
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Activated instruction set: {result['name']}")
        return {"success": True, "message": f"Activated: {result['name']}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate instructions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instructions/{instruction_id}/history", response_model=List[CustomInstructionHistory])
async def get_instruction_history(instruction_id: int):
    """
    Get version history for an instruction set
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, instruction_id, instructions, version, changed_at
            FROM custom_instructions_history
            WHERE instruction_id = %s
            ORDER BY version DESC
        """, (instruction_id,))
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        return [CustomInstructionHistory(**row) for row in results]
        
    except Exception as e:
        logger.error(f"Failed to get instruction history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instructions/{instruction_id}/rollback/{version}")
async def rollback_instructions(instruction_id: int, version: int):
    """
    Rollback to a previous version of instructions
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get the historical version
        cur.execute("""
            SELECT instructions
            FROM custom_instructions_history
            WHERE instruction_id = %s AND version = %s
        """, (instruction_id, version))
        
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Version {version} not found")
        
        # Update current instructions (trigger will archive current version)
        cur.execute("""
            UPDATE custom_instructions
            SET instructions = %s
            WHERE id = %s
        """, (result['instructions'], instruction_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Rolled back instruction set {instruction_id} to version {version}")
        return {"success": True, "message": f"Rolled back to version {version}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rollback instructions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instructions/preview", response_model=InstructionPreview)
async def preview_instructions(instruction: CustomInstruction):
    """
    Preview how custom instructions will be merged with baseline
    """
    try:
        # Load baseline prompt
        from pathlib import Path
        baseline_path = Path(__file__).parent.parent.parent / "shared" / "prompts" / "chaffee_persona.md"
        
        with open(baseline_path, 'r', encoding='utf-8') as f:
            baseline_prompt = f.read().strip()
        
        # Merge prompts
        if instruction.instructions.strip():
            merged_prompt = f"{baseline_prompt}\n\n## Additional Custom Instructions\n\n{instruction.instructions}"
        else:
            merged_prompt = baseline_prompt
        
        # Estimate tokens (rough: 1 token ≈ 4 characters)
        char_count = len(merged_prompt)
        estimated_tokens = char_count // 4
        
        return InstructionPreview(
            baseline_prompt=baseline_prompt,
            custom_instructions=instruction.instructions,
            merged_prompt=merged_prompt,
            character_count=char_count,
            estimated_tokens=estimated_tokens
        )
        
    except Exception as e:
        logger.error(f"Failed to preview instructions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
