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
from fastapi import APIRouter, HTTPException, Query, Response, Request, Depends
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tuning", tags=["tuning"])

# Path to embedding models config
EMBEDDING_MODELS_PATH = Path(__file__).parent.parent / "config" / "embedding_models.json"

# Tuning password from environment (must be set for security)
TUNING_PASSWORD = os.getenv('TUNING_PASSWORD')
if not TUNING_PASSWORD:
    logger.warning("=" * 70)
    logger.warning("⚠️  WARNING: TUNING_PASSWORD is not set.")
    logger.warning("⚠️  Tuning endpoints are NOT protected.")
    logger.warning("⚠️  Do NOT use in production without setting TUNING_PASSWORD!")
    logger.warning("=" * 70)


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
    
    model_config = {"protected_namespaces": ()}  # Allow model_name field


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


async def require_tuning_auth(request: Request):
    """
    FastAPI dependency to check tuning authentication cookie.
    Use as: Depends(require_tuning_auth)
    
    All sensitive tuning endpoints MUST use this dependency to ensure
    only authenticated users can access configuration and instructions.
    
    Security checks:
    1. TUNING_PASSWORD must be configured in environment
    2. Client must have valid tuning_auth cookie set to "authenticated"
    """
    # Check if tuning password is configured
    if not TUNING_PASSWORD:
        logger.error("Tuning endpoint accessed but TUNING_PASSWORD is not configured")
        raise HTTPException(
            status_code=503, 
            detail="Tuning dashboard not configured. TUNING_PASSWORD must be set."
        )
    
    # Check for valid authentication cookie
    cookie = request.cookies.get("tuning_auth")
    if cookie != "authenticated":
        raise HTTPException(
            status_code=401, 
            detail="Tuning dashboard access denied. Please authenticate first."
        )


@router.get(
    "/models",
    response_model=List[EmbeddingModelInfo],
    dependencies=[Depends(require_tuning_auth)],
)
async def list_models(request: Request):
    """
    List all available embedding models with their configurations.
    Protected: requires tuning_auth cookie.
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


@router.get(
    "/config",
    response_model=TuningConfig,
    dependencies=[Depends(require_tuning_auth)],
)
async def get_config(request: Request):
    """
    Get current tuning configuration from .env (single source of truth).
    Protected: requires tuning_auth cookie.
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


@router.post(
    "/models/query",
    dependencies=[Depends(require_tuning_auth)],
)
async def set_query_model(model_key: str, request: Request):
    """
    Set the active query model.
    
    TEMPORARILY DISABLED: Model switching is disabled until a re-embedding
    service is implemented. Switching models without re-embedding all segments
    would result in incompatible embeddings and degraded search quality.
    
    Protected: requires tuning_auth cookie.
    """
    # Model switching is disabled until re-embedding service exists
    raise HTTPException(
        status_code=501,
        detail="Model switching is temporarily disabled. A re-embedding service is required to safely switch embedding models. Contact your developer if you need to change models."
    )
    
    # Original implementation preserved for future use:
    config = load_embedding_models()
    models = config.get("models", {})
    
    if model_key not in models:
        raise HTTPException(status_code=404, detail=f"Model '{model_key}' not found")
    
    model_info = models[model_key]
    full_model_name = model_info.get("model_name", model_key)
    dimensions = model_info.get("dimensions", 384)
    
    # Update runtime environment (always works)
    os.environ["EMBEDDING_MODEL"] = full_model_name
    os.environ["EMBEDDING_DIMENSIONS"] = str(dimensions)
    
    # Also update the JSON config file to track active model
    try:
        config["active_query_model"] = model_key
        save_embedding_models(config)
    except Exception as e:
        logger.warning(f"Could not update embedding_models.json: {e}")
    
    # Try to update .env file if it exists (optional, for local dev)
    env_persisted = False
    try:
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            import re
            env_content = env_path.read_text()
            
            # Replace or add EMBEDDING_MODEL line
            if 'EMBEDDING_MODEL=' in env_content:
                env_content = re.sub(r'EMBEDDING_MODEL=.*', f'EMBEDDING_MODEL={full_model_name}', env_content)
            else:
                env_content += f'\nEMBEDDING_MODEL={full_model_name}'
            
            # Replace or add EMBEDDING_DIMENSIONS line
            if 'EMBEDDING_DIMENSIONS=' in env_content:
                env_content = re.sub(r'EMBEDDING_DIMENSIONS=.*', f'EMBEDDING_DIMENSIONS={dimensions}', env_content)
            else:
                env_content += f'\nEMBEDDING_DIMENSIONS={dimensions}'
            
            env_path.write_text(env_content)
            env_persisted = True
            logger.info(f"Query model switched to '{model_key}' and persisted to .env")
    except Exception as e:
        logger.info(f"Could not persist to .env (this is normal in containers): {e}")
    
    logger.info(f"Query model switched to '{model_key}' ({full_model_name})")
    
    return {
        "success": True,
        "message": f"Query model switched to '{model_key}'",
        "model": model_info,
        "persisted": env_persisted,
        "note": "Changes applied to runtime." + (" Also saved to .env." if env_persisted else " Restart will reset to default.")
    }


@router.post(
    "/models/ingestion",
    dependencies=[Depends(require_tuning_auth)],
)
async def set_ingestion_models(model_keys: List[str], request: Request):
    """
    Set the active ingestion models.
    
    TEMPORARILY DISABLED: Model switching is disabled until a re-embedding
    service is implemented. Switching models without re-embedding all segments
    would result in incompatible embeddings and degraded search quality.
    
    Protected: requires tuning_auth cookie.
    """
    # Model switching is disabled until re-embedding service exists
    raise HTTPException(
        status_code=501,
        detail="Model switching is temporarily disabled. A re-embedding service is required to safely switch embedding models. Contact your developer if you need to change models."
    )
    
    # Original implementation preserved for future use:
    config = load_embedding_models()
    models = config.get("models", {})
    
    # Validate all model keys
    for key in model_keys:
        if key not in models:
            raise HTTPException(status_code=404, detail=f"Model '{key}' not found")
    
    # For now, we only support single ingestion model (same as query model)
    if len(model_keys) > 1:
        logger.warning(f"Multiple ingestion models requested: {model_keys}. Using first: {model_keys[0]}")
    
    primary_model_key = model_keys[0]
    model_info = models[primary_model_key]
    full_model_name = model_info.get("model_name", primary_model_key)
    dimensions = model_info.get("dimensions", 384)
    
    # Update runtime environment (always works)
    os.environ["EMBEDDING_MODEL"] = full_model_name
    os.environ["EMBEDDING_DIMENSIONS"] = str(dimensions)
    
    # Also update the JSON config file to track active model
    try:
        config["active_ingestion_models"] = [primary_model_key]
        save_embedding_models(config)
    except Exception as e:
        logger.warning(f"Could not update embedding_models.json: {e}")
    
    # Try to update .env file if it exists (optional, for local dev)
    env_persisted = False
    try:
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            import re
            env_content = env_path.read_text()
            
            if 'EMBEDDING_MODEL=' in env_content:
                env_content = re.sub(r'EMBEDDING_MODEL=.*', f'EMBEDDING_MODEL={full_model_name}', env_content)
            else:
                env_content += f'\nEMBEDDING_MODEL={full_model_name}'
            
            if 'EMBEDDING_DIMENSIONS=' in env_content:
                env_content = re.sub(r'EMBEDDING_DIMENSIONS=.*', f'EMBEDDING_DIMENSIONS={dimensions}', env_content)
            else:
                env_content += f'\nEMBEDDING_DIMENSIONS={dimensions}'
            
            env_path.write_text(env_content)
            env_persisted = True
    except Exception as e:
        logger.info(f"Could not persist to .env (this is normal in containers): {e}")
    
    logger.info(f"Ingestion model set to '{primary_model_key}' ({full_model_name})")
    
    return {
        "success": True,
        "message": f"Ingestion model set to: {primary_model_key}",
        "model": model_info,
        "persisted": env_persisted,
        "note": "Changes applied to runtime. Run ingestion to generate embeddings."
    }


@router.post(
    "/search/config",
    dependencies=[Depends(require_tuning_auth)],
)
async def update_search_config(config: SearchConfig, request: Request):
    """
    Update search configuration parameters.
    Note: This updates the in-memory config. For persistence, update .env file.
    Protected: requires tuning_auth cookie.
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


@router.get(
    "/summarizer/config",
    response_model=SummarizerConfig,
    dependencies=[Depends(require_tuning_auth)],
)
async def get_summarizer_config(request: Request):
    """
    Get current summarizer configuration.
    Protected: requires tuning_auth cookie.
    """
    return SummarizerConfig(
        model=os.getenv("SUMMARIZER_MODEL", "gpt-4-turbo"),
        temperature=float(os.getenv("SUMMARIZER_TEMPERATURE", "0.1")),
        max_tokens=int(os.getenv("SUMMARIZER_MAX_TOKENS", "2000"))
    )


@router.post(
    "/summarizer/config",
    dependencies=[Depends(require_tuning_auth)],
)
async def update_summarizer_config(config: SummarizerConfig, request: Request):
    """
    Update summarizer configuration.
    
    Allowed models (cost-controlled whitelist):
    - gpt-4-turbo: $0.01/1k input, $0.03/1k output (recommended)
    - gpt-4: $0.03/1k input, $0.06/1k output (slower, more expensive)
    - gpt-3.5-turbo: $0.0005/1k input, $0.0015/1k output (faster, cheaper)
    
    Note: This updates runtime config. For persistence, update .env file.
    Protected: requires tuning_auth cookie.
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


@router.post(
    "/search/test",
    response_model=List[TestSearchResult],
    dependencies=[Depends(require_tuning_auth)],
)
async def test_search(search_request: TestSearchRequest, request: Request):
    """
    Test search with current or specified model.
    Protected: requires tuning_auth cookie.
    """
    from ..services.embeddings_service import EmbeddingsService
    import psycopg2
    
    try:
        # Get active model or use override
        config = load_embedding_models()
        model_key = search_request.model_key or config.get("active_query_model")
        
        # Generate query embedding
        embeddings_service = EmbeddingsService.get_instance()
        query_embedding = embeddings_service.encode_text(search_request.query)
        
        # Search database
        top_k = search_request.top_k or int(os.getenv("ANSWER_TOPK", "20"))
        
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


@router.get(
    "/instructions",
    response_model=List[CustomInstruction],
    dependencies=[Depends(require_tuning_auth)],
)
async def list_instructions(request: Request):
    """
    List all custom instruction sets.
    Protected: requires tuning_auth cookie.
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


@router.get(
    "/instructions/active",
    response_model=CustomInstruction,
    dependencies=[Depends(require_tuning_auth)],
)
async def get_active_instructions(request: Request):
    """
    Get the currently active instruction set.
    Protected: requires tuning_auth cookie.
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


@router.post(
    "/instructions",
    response_model=CustomInstruction,
    dependencies=[Depends(require_tuning_auth)],
)
async def create_instructions(instruction: CustomInstruction, request: Request):
    """
    Create a new custom instruction set.
    Protected: requires tuning_auth cookie.
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


@router.put(
    "/instructions/{instruction_id}",
    response_model=CustomInstruction,
    dependencies=[Depends(require_tuning_auth)],
)
async def update_instructions(instruction_id: int, instruction: CustomInstruction, request: Request):
    """
    Update an existing custom instruction set.
    Protected: requires tuning_auth cookie.
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


@router.delete(
    "/instructions/{instruction_id}",
    dependencies=[Depends(require_tuning_auth)],
)
async def delete_instructions(instruction_id: int, request: Request):
    """
    Delete a custom instruction set.
    Protected: requires tuning_auth cookie.
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


@router.post(
    "/instructions/{instruction_id}/activate",
    dependencies=[Depends(require_tuning_auth)],
)
async def activate_instructions(instruction_id: int, request: Request):
    """
    Activate a specific instruction set (deactivates all others).
    Protected: requires tuning_auth cookie.
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


@router.get(
    "/instructions/{instruction_id}/history",
    response_model=List[CustomInstructionHistory],
    dependencies=[Depends(require_tuning_auth)],
)
async def get_instruction_history(instruction_id: int, request: Request):
    """
    Get version history for an instruction set.
    Protected: requires tuning_auth cookie.
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


@router.post(
    "/instructions/{instruction_id}/rollback/{version}",
    dependencies=[Depends(require_tuning_auth)],
)
async def rollback_instructions(instruction_id: int, version: int, request: Request):
    """
    Rollback to a previous version of instructions.
    Protected: requires tuning_auth cookie.
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


@router.post(
    "/instructions/preview",
    response_model=InstructionPreview,
    dependencies=[Depends(require_tuning_auth)],
)
async def preview_instructions(instruction: CustomInstruction, request: Request):
    """
    Preview how custom instructions will be merged with baseline.
    Protected: requires tuning_auth cookie (sensitive - shows baseline prompt).
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


# =============================================================================
# Search Configuration Endpoints (Database-backed)
# =============================================================================

class SearchConfigDB(BaseModel):
    """Search configuration stored in database"""
    top_k: int = Field(default=100, ge=1, le=500, description="Initial results to consider")
    min_similarity: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum relevance threshold")
    enable_reranker: bool = Field(default=False, description="Use reranking step")
    rerank_top_k: int = Field(default=200, ge=1, le=500, description="Candidates for reranking")
    return_top_k: int = Field(default=20, ge=1, le=100, description="Final results to return")


class SearchConfigResponse(BaseModel):
    """Response wrapper for search config with error info"""
    config: Optional[SearchConfigDB] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


def get_search_config_from_db() -> SearchConfigDB:
    """
    Get search configuration from database, with defaults if not found.
    
    This function ALWAYS returns a valid SearchConfigDB object with defaults
    if the table is missing or any error occurs. This ensures /search and /answer
    never 500 due to missing migrations.
    
    Returns:
        SearchConfigDB: Configuration object (defaults if table missing)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT top_k, min_similarity, enable_reranker, rerank_top_k, return_top_k
            FROM search_config
            WHERE id = 1
        """)
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            return SearchConfigDB(
                top_k=row['top_k'],
                min_similarity=row['min_similarity'],
                enable_reranker=row['enable_reranker'],
                rerank_top_k=row['rerank_top_k'],
                return_top_k=row['return_top_k']
            )
        else:
            # Table exists but no row - return defaults
            logger.info("search_config table exists but has no row, using defaults")
            return SearchConfigDB()
            
    except psycopg2.errors.UndefinedTable:
        logger.warning("search_config table does not exist - migration 015 needs to be applied. Using defaults.")
        return SearchConfigDB()
    except psycopg2.ProgrammingError as e:
        if "does not exist" in str(e):
            logger.warning(f"search_config table missing: {e}. Using defaults.")
            return SearchConfigDB()
        logger.error(f"Database programming error: {e}. Using defaults.")
        return SearchConfigDB()
    except Exception as e:
        logger.warning(f"Failed to load search config from DB: {e}. Using defaults.")
        return SearchConfigDB()


def get_search_config_with_status() -> tuple[SearchConfigDB, Optional[str], Optional[str]]:
    """
    Get search configuration with error status for the tuning UI.
    
    This function returns both the config and any error information so the
    tuning UI can display migration warnings to the user.
    
    Returns:
        tuple: (config, error_message, error_code)
        - config: SearchConfigDB with values (defaults if table missing)
        - error_message: Human-readable error or None
        - error_code: Error code for frontend handling or None
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT top_k, min_similarity, enable_reranker, rerank_top_k, return_top_k
            FROM search_config
            WHERE id = 1
        """)
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            return SearchConfigDB(
                top_k=row['top_k'],
                min_similarity=row['min_similarity'],
                enable_reranker=row['enable_reranker'],
                rerank_top_k=row['rerank_top_k'],
                return_top_k=row['return_top_k']
            ), None, None
        else:
            # Table exists but no row - return defaults
            return SearchConfigDB(), None, None
            
    except psycopg2.errors.UndefinedTable:
        logger.warning("search_config table does not exist - migration 015 needs to be applied")
        return SearchConfigDB(), "Database migration required: search_config table does not exist. Please apply migration 015_search_config.sql", "MIGRATION_REQUIRED"
    except psycopg2.ProgrammingError as e:
        if "does not exist" in str(e):
            logger.warning(f"search_config table missing: {e}")
            return SearchConfigDB(), "Database migration required: search_config table does not exist. Please apply migration 015_search_config.sql", "MIGRATION_REQUIRED"
        logger.error(f"Database programming error: {e}")
        return SearchConfigDB(), f"Database error: {str(e)}", "DB_ERROR"
    except Exception as e:
        logger.warning(f"Failed to load search config from DB: {e}, using defaults")
        return SearchConfigDB(), None, None


@router.get(
    "/search-config",
    response_model=SearchConfigResponse,
    dependencies=[Depends(require_tuning_auth)],
)
async def get_search_config(request: Request):
    """
    Get current search configuration from database.
    Protected: requires tuning_auth cookie.
    
    Returns config with optional error info if table is missing.
    """
    config, error, error_code = get_search_config_with_status()
    return SearchConfigResponse(config=config, error=error, error_code=error_code)


@router.put(
    "/search-config",
    response_model=SearchConfigResponse,
    dependencies=[Depends(require_tuning_auth)],
)
async def update_search_config(config: SearchConfigDB, request: Request):
    """
    Update search configuration in database.
    Protected: requires tuning_auth cookie.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Upsert the config (insert or update)
        cur.execute("""
            INSERT INTO search_config (id, top_k, min_similarity, enable_reranker, rerank_top_k, return_top_k)
            VALUES (1, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                top_k = EXCLUDED.top_k,
                min_similarity = EXCLUDED.min_similarity,
                enable_reranker = EXCLUDED.enable_reranker,
                rerank_top_k = EXCLUDED.rerank_top_k,
                return_top_k = EXCLUDED.return_top_k,
                updated_at = NOW()
            RETURNING top_k, min_similarity, enable_reranker, rerank_top_k, return_top_k
        """, (config.top_k, config.min_similarity, config.enable_reranker, config.rerank_top_k, config.return_top_k))
        
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Search config updated: top_k={config.top_k}, min_similarity={config.min_similarity}")
        
        return SearchConfigResponse(
            config=SearchConfigDB(
                top_k=row['top_k'],
                min_similarity=row['min_similarity'],
                enable_reranker=row['enable_reranker'],
                rerank_top_k=row['rerank_top_k'],
                return_top_k=row['return_top_k']
            )
        )
        
    except psycopg2.errors.UndefinedTable:
        logger.error("Cannot save search config - table does not exist")
        return SearchConfigResponse(
            config=config,
            error="Database migration required: search_config table does not exist. Please apply migration 015_search_config.sql",
            error_code="MIGRATION_REQUIRED"
        )
    except psycopg2.ProgrammingError as e:
        if "does not exist" in str(e):
            logger.error(f"Cannot save search config - table missing: {e}")
            return SearchConfigResponse(
                config=config,
                error="Database migration required: search_config table does not exist. Please apply migration 015_search_config.sql",
                error_code="MIGRATION_REQUIRED"
            )
        logger.error(f"Failed to update search config: {e}")
        return SearchConfigResponse(config=config, error=f"Database error: {str(e)}", error_code="DB_ERROR")
    except Exception as e:
        logger.error(f"Failed to update search config: {e}")
        return SearchConfigResponse(config=config, error=f"Failed to save configuration: {str(e)}", error_code="SAVE_ERROR")
