#!/usr/bin/env python3
"""
FastAPI main application for Ask Dr Chaffee
Multi-source transcript processing with admin interface
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncio
import zipfile
import io
import json
import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
import psycopg2
from psycopg2.extras import RealDictCursor

# Import our existing processors
import sys
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(backend_path)
from scripts.process_srt_files import SRTProcessor
from scripts.common.database_upsert import DatabaseUpserter
from scripts.common.transcript_common import TranscriptSegment
from scripts.common.embeddings import EmbeddingGenerator, resolve_embedding_config

# Import tuning router and search config helper
from .tuning import router as tuning_router, get_search_config_from_db, SearchConfigDB

app = FastAPI(
    title="Ask Dr Chaffee API",
    description="Multi-source transcript processing and LLM search",
    version="1.0.0"
)

# Include tuning API
app.include_router(tuning_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event to warm up embedding model (optional on low-memory environments)
@app.on_event("startup")
async def startup_event():
    """Warm up embedding model on startup to avoid slow first request
    
    Skips warmup on low-memory environments (e.g., Render Starter 512MB)
    Model will load on first request instead (~20-25s delay)
    
    Also runs DB embedding consistency check to prevent dimension mismatches.
    """
    import os
    
    # Log resolved embedding configuration
    config = resolve_embedding_config()
    logger.info("=" * 60)
    logger.info("📋 EMBEDDING CONFIGURATION (Single Source of Truth)")
    logger.info("=" * 60)
    logger.info(f"   Provider: {config['provider']}")
    logger.info(f"   Model: {config['model']}")
    logger.info(f"   Dimensions: {config['dimensions']}")
    logger.info(f"   Device: {config['device']}")
    logger.info(f"   FORCE_CPU_ONLY: {os.getenv('FORCE_CPU_ONLY', 'not set')}")
    logger.info("=" * 60)
    
    # Skip warmup on Render Starter (512MB) - not enough memory
    # Set SKIP_WARMUP=true to disable, or let it auto-detect low memory
    skip_warmup = os.getenv('SKIP_WARMUP', '').lower() == 'true'
    
    if skip_warmup:
        logger.info("⏭️  Skipping embedding model warmup (SKIP_WARMUP=true)")
        return
    
    logger.info("🚀 Warming up embedding model on startup...")
    try:
        generator = get_embedding_generator()
        # Generate a dummy embedding to load the model
        generator.generate_embeddings(["warmup"])
        
        # Run DB consistency check after warmup
        is_consistent, message = check_db_embedding_consistency()
        if not is_consistent:
            logger.error("🚨 DB EMBEDDING CONSISTENCY CHECK FAILED!")
            logger.error(message)
            # Don't crash - just warn loudly
        
    except MemoryError:
        logger.exception("❌ Embedding warmup failed (out of memory)")
        logger.info("💡 Model will load on first request (~20-25s delay)")
        logger.info("💡 To fix: upgrade Render plan or set SKIP_WARMUP=true")
    except Exception:
        logger.exception("❌ Embedding warmup failed")
        logger.info("💡 Model will load on first request instead")
    else:
        logger.info("✅ Embedding model warmed up successfully")

# =============================================================================
# Security Configuration
# =============================================================================
# ADMIN_API_KEY: Required for admin endpoints (upload, sync, jobs)
# Must be set in production - no insecure default allowed.
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
if not ADMIN_API_KEY:
    logger.warning("⚠️  ADMIN_API_KEY not set - admin endpoints will be inaccessible")

# INTERNAL_API_KEY: Protects RAG/search endpoints from direct public access.
# Frontend Next.js API routes inject this header when proxying to backend.
# In production, this MUST be set. In dev, can be disabled for convenience.
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")
if not INTERNAL_API_KEY:
    logger.warning("⚠️  INTERNAL_API_KEY not set - RAG endpoints are publicly accessible (dev mode)")

security = HTTPBearer(auto_error=False)

# Background job tracking
processing_jobs: Dict[str, Dict[str, Any]] = {}

# Initialize embedding generator (lazy load)
_embedding_generator = None
_db_embedding_check_done = False

def get_embedding_generator():
    global _embedding_generator
    if _embedding_generator is None:
        # Use resolve_embedding_config() as single source of truth
        config = resolve_embedding_config()
        
        _embedding_generator = EmbeddingGenerator(
            embedding_provider=config['provider'],
            model_name=config['model']
        )
        
        logger.info(f"📋 Embedding generator initialized:")
        logger.info(f"   Provider: {config['provider']}")
        logger.info(f"   Model: {config['model']}")
        logger.info(f"   Dimensions: {config['dimensions']}")
        logger.info(f"   Device: {config['device']}")
    return _embedding_generator


def check_db_embedding_consistency():
    """
    Check that the configured embedding dimensions match what's in the database.
    This prevents accidental model switching that would corrupt search results.
    
    Returns:
        tuple: (is_consistent: bool, message: str)
    """
    global _db_embedding_check_done
    
    if _db_embedding_check_done:
        return True, "Already checked"
    
    try:
        config = resolve_embedding_config()
        expected_dim = config['dimensions']
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if there are any embeddings in the database
        cur.execute("""
            SELECT COUNT(*) as count
            FROM segments
            WHERE embedding IS NOT NULL
        """)
        result = cur.fetchone()
        
        if not result or result['count'] == 0:
            cur.close()
            conn.close()
            _db_embedding_check_done = True
            return True, "No embeddings in database yet"
        
        # Get a sample embedding to check dimensions
        cur.execute("""
            SELECT embedding
            FROM segments
            WHERE embedding IS NOT NULL
            LIMIT 1
        """)
        sample = cur.fetchone()
        cur.close()
        conn.close()
        
        if not sample or not sample['embedding']:
            _db_embedding_check_done = True
            return True, "No embeddings in database yet"
        
        # Determine actual dimensions
        embedding = sample['embedding']
        if isinstance(embedding, (list, tuple)):
            actual_dim = len(embedding)
        elif hasattr(embedding, '__len__') and not isinstance(embedding, str):
            actual_dim = len(embedding)
        else:
            # Parse as string '[0.1, 0.2, ...]'
            embedding_str = str(embedding)
            parts = embedding_str.strip('[]').split(',')
            parts = [p.strip() for p in parts if p.strip()]
            actual_dim = len(parts)
        
        _db_embedding_check_done = True
        
        if actual_dim != expected_dim:
            error_msg = (
                f"❌ EMBEDDING DIMENSION MISMATCH!\n"
                f"   Database has: {actual_dim} dimensions ({result['count']} embeddings)\n"
                f"   Config expects: {expected_dim} dimensions\n"
                f"   Model: {config['model']}\n"
                f"   \n"
                f"   You must either:\n"
                f"   1. Change EMBEDDING_DIMENSIONS to {actual_dim} to match DB\n"
                f"   2. Re-embed all segments with the new model\n"
                f"   \n"
                f"   Mixing dimensions will corrupt search results!"
            )
            logger.error(error_msg)
            return False, error_msg
        
        logger.info(f"✅ DB embedding consistency check passed: {actual_dim} dimensions")
        return True, f"Consistent: {actual_dim} dimensions"
        
    except Exception as e:
        logger.warning(f"Could not check DB embedding consistency: {e}")
        _db_embedding_check_done = True
        return True, f"Check skipped: {e}"

def get_active_model_key():
    """Get the active model key from resolved config"""
    config = resolve_embedding_config()
    
    # Map model name to key
    model_to_key = {
        'BAAI/bge-small-en-v1.5': 'bge-small-en-v1.5',
        'Alibaba-NLP/gte-Qwen2-1.5B-instruct': 'gte-qwen2-1.5b',
        'nomic-embed-text-v1.5': 'nomic-v1.5',
    }
    
    return model_to_key.get(config['model'], 'bge-small-en-v1.5')

# Removed: use_normalized_embeddings() - using legacy storage only

def get_available_embedding_models():
    """Get list of embedding models from legacy segments.embedding column"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        logger.info("Checking legacy segments table for embeddings...")
        cur.execute("""
            SELECT COUNT(*) as count
            FROM segments
            WHERE embedding IS NOT NULL
        """)
        legacy_result = cur.fetchone()
        
        if legacy_result and legacy_result['count'] > 0:
            # Get a sample embedding to determine dimensions
            cur.execute("""
                SELECT embedding
                FROM segments
                WHERE embedding IS NOT NULL
                LIMIT 1
            """)
            sample = cur.fetchone()
            
            if sample and sample['embedding']:
                # Get dimensions from the vector
                # Try multiple methods to be robust
                try:
                    # Method 1: If it's already a list/array (most common)
                    if isinstance(sample['embedding'], (list, tuple)):
                        dimensions = len(sample['embedding'])
                    elif hasattr(sample['embedding'], '__len__') and not isinstance(sample['embedding'], str):
                        dimensions = len(sample['embedding'])
                    else:
                        # Method 2: Parse as string '[0.1, 0.2, ...]'
                        embedding_str = str(sample['embedding'])
                        # Remove brackets and split by comma
                        parts = embedding_str.strip('[]').split(',')
                        # Filter out empty strings
                        parts = [p.strip() for p in parts if p.strip()]
                        dimensions = len(parts)
                except Exception as e:
                    logger.error(f"Failed to determine dimensions: {e}")
                    # Fallback to resolved config dimension
                    dimensions = resolve_embedding_config()['dimensions']
                
                # Get count of embeddings
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM segments
                    WHERE embedding IS NOT NULL
                """)
                result = cur.fetchone()
                cur.close()
                conn.close()
                
                if result and result['count'] > 0:
                    # Map dimensions to model key (must match keys in embedding_models.json)
                    # 384 = BGE-small, 768 = Nomic, 1536 = OpenAI/GTE-Qwen2
                    dimension_to_model = {
                        384: 'bge-small-en-v1.5',
                        768: 'nomic-v1.5',
                        1536: 'gte-qwen2-1.5b'
                    }
                    model_key = dimension_to_model.get(dimensions, 'bge-small-en-v1.5')
                    
                    model = {
                        "model_key": model_key, 
                        "dimensions": dimensions, 
                        "count": result['count']
                    }
                    logger.info(f"Available embedding model: {model}")
                    return [model]
        
        cur.close()
        conn.close()
        return []
    except Exception as e:
        logger.error(f"Failed to get available models: {e}", exc_info=True)
        return []

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        os.getenv('DATABASE_URL'),
        cursor_factory=RealDictCursor
    )

class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    total_files: int
    processed_files: int
    failed_files: int
    current_file: Optional[str] = None
    errors: List[str] = []
    created_at: datetime
    completed_at: Optional[datetime] = None

class UploadRequest(BaseModel):
    source_type: str  # youtube_takeout, zoom, manual, other
    description: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = None  # If None, use database config
    min_similarity: Optional[float] = None  # If None, use database config
    rerank: Optional[bool] = None  # If None, use database config

class SearchResult(BaseModel):
    id: int
    video_id: str
    title: str
    text: str
    url: str
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

class AnswerRequest(BaseModel):
    query: str
    style: Optional[str] = 'concise'
    top_k: Optional[int] = None  # Will use ANSWER_TOP_K env var if not specified

# =============================================================================
# Authentication Dependencies
# =============================================================================

async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify admin API token for protected admin endpoints.
    Requires: Authorization: Bearer <ADMIN_API_KEY>
    
    Used by: /api/upload/*, /api/sync/*, /api/jobs
    """
    if not ADMIN_API_KEY:
        raise HTTPException(
            status_code=503, 
            detail="Admin API not configured. Set ADMIN_API_KEY environment variable."
        )
    if not credentials or credentials.credentials != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    return credentials.credentials


async def verify_internal_api_key(request: Request):
    """
    Verify internal API key for RAG/search endpoints.
    Requires: X-Internal-Key header matching INTERNAL_API_KEY.
    
    This prevents direct public access to backend RAG endpoints.
    The frontend Next.js API routes inject this header when proxying requests.
    
    In dev mode (INTERNAL_API_KEY not set), this check is skipped with a warning.
    In production, INTERNAL_API_KEY MUST be set.
    """
    if not INTERNAL_API_KEY:
        # Dev mode: skip check but log warning (already logged at startup)
        return
    
    header_key = request.headers.get("X-Internal-Key")
    if header_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid internal API key")

@app.get("/")
@app.head("/")
async def root():
    """Root endpoint"""
    return {"status": "ok", "service": "Ask Dr Chaffee API"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint for production monitoring
    Checks: Database connection, embedding service readiness
    Returns: 200 OK if healthy, 503 if degraded
    """
    health_status = {
        "status": "ok",
        "service": "Ask Dr Chaffee API",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Check 1: Database connection
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = "degraded"
        health_status["status"] = "degraded"
    
    # Check 2: Embedding service readiness
    try:
        generator = get_embedding_generator()
        # Quick test embedding (should be fast if model is loaded)
        _ = generator.generate_embeddings(["health check"])
        health_status["checks"]["embeddings"] = "ok"
    except Exception as e:
        logger.error(f"Embedding service health check failed: {e}")
        health_status["checks"]["embeddings"] = "degraded"
        health_status["status"] = "degraded"
    
    # Return 503 if degraded, 200 if ok
    status_code = 503 if health_status["status"] == "degraded" else 200
    return JSONResponse(content=health_status, status_code=status_code)

@app.get("/api/test-db")
async def test_db():
    """Test database connection"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM segments")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "ok", "segment_count": result['count']}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/stats", dependencies=[Depends(verify_internal_api_key)])
@app.get("/api/stats", dependencies=[Depends(verify_internal_api_key)])
async def get_stats():
    """
    Get database statistics for segments and embeddings.
    Returns counts and embedding coverage metrics.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Single optimized query to get all stats including embedding coverage
        cur.execute("""
            SELECT 
                COUNT(*) as total_segments,
                COUNT(DISTINCT source_id) as total_videos,
                COUNT(embedding) as segments_with_embeddings,
                CAST(
                    CASE WHEN COUNT(*) > 0 
                    THEN (COUNT(embedding)::float / COUNT(*)::float) * 100 
                    ELSE 0 
                    END AS NUMERIC(5,1)
                ) as embedding_coverage_pct
            FROM segments
        """)
        
        stats = cur.fetchone()
        cur.close()
        conn.close()
        
        segment_count = int(stats['total_segments'] or 0)
        video_count = int(stats['total_videos'] or 0)
        embedded_count = int(stats['segments_with_embeddings'] or 0)
        coverage_pct = float(stats['embedding_coverage_pct'] or 0)
        missing_count = segment_count - embedded_count
        
        return {
            "total_segments": segment_count,
            "total_videos": video_count,
            "segments_with_embeddings": embedded_count,
            "segments_missing_embeddings": missing_count,
            "embedding_coverage": f"{coverage_pct:.1f}%",
            "embedding_dimensions": resolve_embedding_config()['dimensions'],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.exception("Stats endpoint error")
        # Return safe defaults on error (matching frontend expectation)
        return {
            "total_segments": 0,
            "total_videos": 0,
            "segments_with_embeddings": 0,
            "segments_missing_embeddings": 0,
            "embedding_coverage": "0.0%",
            "embedding_dimensions": resolve_embedding_config()['dimensions'],
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@app.get("/search", dependencies=[Depends(verify_internal_api_key)])
@app.get("/api/search", dependencies=[Depends(verify_internal_api_key)])
async def search_get(q: str, top_k: int = 50, min_similarity: float = 0.5):
    """GET endpoint for search (for frontend compatibility)"""
    request = SearchRequest(query=q, top_k=top_k, min_similarity=min_similarity)
    return await semantic_search(request)

@app.post("/search", response_model=SearchResponse, dependencies=[Depends(verify_internal_api_key)])
async def search_post(request: SearchRequest):
    """POST endpoint for search (alternative path)"""
    return await semantic_search(request)

@app.post("/api/search", response_model=SearchResponse, dependencies=[Depends(verify_internal_api_key)])
async def semantic_search(request: SearchRequest):
    """
    Semantic search with optional reranking
    
    1. Load search config from database (or use defaults)
    2. Detect available embeddings in database
    3. Generate query embedding with matching model
    4. Search database using vector similarity
    5. Optionally rerank results for better quality
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Load search config from database
        db_config = get_search_config_from_db()
        
        # Use request values if provided, otherwise use database config
        top_k = request.top_k if request.top_k is not None else db_config.top_k
        min_similarity = request.min_similarity if request.min_similarity is not None else db_config.min_similarity
        use_rerank = request.rerank if request.rerank is not None else db_config.enable_reranker
        
        logger.info(f"Search request: {request.query} (top_k={top_k}, min_sim={min_similarity}, rerank={use_rerank})")
        
        # First, detect what embeddings are available in the database
        available_models = get_available_embedding_models()
        if not available_models:
            raise HTTPException(
                status_code=503, 
                detail="No embeddings found in database. Please run ingestion first."
            )
        
        # Use the first available model (most common one)
        db_model = available_models[0]
        model_key = db_model['model_key']
        expected_dim = db_model['dimensions']
        
        logger.info(f"Database has {db_model['count']} embeddings with model '{model_key}' ({expected_dim} dims)")
        
        # Load config to get model details
        import json
        from pathlib import Path
        config_path = Path(__file__).parent.parent / 'config' / 'embedding_models.json'
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Check if model exists in config
        if model_key not in config['models']:
            raise HTTPException(
                status_code=503,
                detail=f"Model '{model_key}' not found in config. Available: {list(config['models'].keys())}"
            )
        
        model_config = config['models'][model_key]
        
        # Generate query embedding with the correct model
        logger.info(f"Generating query embedding with {model_config['provider']} / {model_config['model_name']}...")
        
        # Create a generator for this specific model
        from scripts.common.embeddings import EmbeddingGenerator
        generator = EmbeddingGenerator(
            embedding_provider=model_config['provider'],
            model_name=model_config['model_name']
        )
        
        embeddings = generator.generate_embeddings([request.query])
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        if not embeddings or len(embeddings) == 0:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        
        query_embedding = embeddings[0]
        embedding_dim = len(query_embedding)
        
        # Verify dimensions match
        if embedding_dim != expected_dim:
            raise HTTPException(
                status_code=503, 
                detail=f"Dimension mismatch: generated={embedding_dim}, database={expected_dim} for model {model_key}"
            )
        
        # Convert embedding to list
        embedding_list = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding
        
        # Connect to database
        conn = get_db_connection()
        cur = conn.cursor()
        
        logger.info(f"Searching with model: {model_key} ({expected_dim} dims)")
        
        # Use legacy embedding column (segments.embedding)
        search_query = """
            SELECT 
                seg.id,
                s.source_id as video_id,
                s.title,
                seg.text,
                seg.start_sec as start_time_seconds,
                seg.end_sec as end_time_seconds,
                s.published_at,
                s.source_type,
                s.url,
                1 - (seg.embedding <=> %s::vector) as similarity
            FROM segments seg
            JOIN sources s ON seg.source_id = s.id
            WHERE seg.embedding IS NOT NULL
              AND 1 - (seg.embedding <=> %s::vector) >= %s
            ORDER BY similarity DESC
            LIMIT %s
        """
        query_params = [
            str(embedding_list),
            str(embedding_list),
            min_similarity,
            top_k
        ]
        
        # Execute query with appropriate parameters
        cur.execute(search_query, query_params)
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        # Optional reranking
        if use_rerank and len(results) > 0:
            query_lower = request.query.lower()
            query_words = set(query_lower.split())
            
            for result in results:
                text_lower = result['text'].lower()
                keyword_matches = sum(1 for word in query_words if word in text_lower)
                keyword_boost = min(0.1, keyword_matches * 0.02)
                result['similarity'] = min(1.0, result['similarity'] + keyword_boost)
            
            results = sorted(results, key=lambda x: x['similarity'], reverse=True)
        
        # Convert to response format
        search_results = [
            SearchResult(
                id=r['id'],
                video_id=r['video_id'],
                title=r['title'],
                text=r['text'],
                url=r['url'] or '',
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
        logger.error(f"Search failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/embed", dependencies=[Depends(verify_internal_api_key)])
@app.post("/api/embed", dependencies=[Depends(verify_internal_api_key)])
async def generate_embedding(request: dict):
    """Generate embedding for a text"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        text = request.get('text') or request.get('query')
        if not text:
            raise HTTPException(status_code=400, detail="Text or query required")
        
        logger.info(f"Generating embedding for: {text[:50]}...")
        generator = get_embedding_generator()
        embeddings = generator.generate_embeddings([text])
        
        if not embeddings or len(embeddings) == 0:
            raise HTTPException(status_code=500, detail="Failed to generate embedding")
        
        embedding = embeddings[0]
        
        return {
            "embedding": embedding,
            "dimensions": len(embedding),
            "text": text
        }
    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

def _format_timestamp(seconds: float) -> str:
    """Format seconds to mm:ss (YouTube style, never h:mm:ss)"""
    total_minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{total_minutes}:{secs:02d}"


def _get_custom_instructions() -> str:
    """
    Load active custom instructions from database.
    
    Returns:
        Custom instructions text or empty string if not found/configured.
    """
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.debug("CustomInstructions: DATABASE_URL not set, skipping")
        return ""
    
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT instructions
            FROM custom_instructions
            WHERE is_active = true
            LIMIT 1
        """)
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result and result['instructions'] and result['instructions'].strip():
            instructions = result['instructions'].strip()
            logger.debug(
                "CustomInstructions: loaded active instructions (len=%d, preview=%r)",
                len(instructions),
                instructions[:100]
            )
            return instructions
        
        logger.debug("CustomInstructions: no active instruction set found")
        return ""
        
    except Exception as e:
        # Table might not exist yet (pre-migration) - graceful degradation
        logger.debug(f"CustomInstructions: could not load from DB: {e}")
        return ""


def _build_chaffee_system_prompt(style: str, include_custom: bool = True) -> str:
    """
    Build the curated Dr. Chaffee system prompt.
    This prompt was carefully tuned for authentic voice and quality answers.
    
    Args:
        style: Answer style ('concise' or 'detailed')
        include_custom: If True, append active custom instructions from database
    
    Returns:
        Complete system prompt (baseline + custom if enabled and available)
    """
    baseline_prompt = """# Emulated Dr Anthony Chaffee (AI) - System Prompt

You are "Emulated Dr Anthony Chaffee (AI)", speaking in Dr. Chaffee's professional but conversational style.

## Speaking Style (CRITICAL)

- **Professional yet approachable**: Clear and articulate, but not stiff or academic
- **Always use first person**: "I recommend", "I've seen", "What I tell people", "I've found"
- **Be specific, not generic**: Don't say "the carnivore diet focuses on..." - say "When you eat carnivore, you're..."
- Natural speech patterns: "you know", "I mean", "so", "and"
- Complete sentences but conversational flow
- Explain things clearly without being overly formal
- Use contractions naturally: "it's", "you're", "don't", "that's"
- **Avoid third-person descriptions**: Don't describe the diet from outside - speak from experience

## Content Approach

- **ONLY use information from the provided context** - Never add generic medical knowledge
- Get to the point but explain thoroughly
- Use clear, straightforward language
- Share practical examples and observations from YOUR content
- Reference your content naturally: "As I talked about...", "I've mentioned..."
- Be confident and knowledgeable without being preachy
- Acknowledge complexity when relevant
- **If something isn't in your content, say so** - Don't make up answers
- **You advocate for carnivore/animal-based eating** - Never recommend plant foods or tea

## What to AVOID

- ❌ Overly casual: "Look", "Here's the deal", "So basically"
- ❌ Academic formality: "moreover", "furthermore", "in conclusion", "it is important to note"
- ❌ Generic descriptions: "The carnivore diet, which focuses on...", "has been associated with"
- ❌ Third-person narration: "The diet can contribute..." - say "I've seen it help..."
- ❌ Essay structure: No formal introductions or conclusions
- ❌ Hedging language: "One might consider", "It could be argued", "may be beneficial"
- ❌ Overly formal transitions: "Another significant benefit is..."
- ❌ Generic disclaimers: "consult with a healthcare professional", "dietary balance", "individual needs may vary"
- ❌ Hedging conclusions: "In summary", "Overall", "It's important to note"
- ❌ Wishy-washy endings: Don't undermine the message with generic medical disclaimers

## Aim For

- ✅ Natural explanation: "So what happens is...", "The thing is..."
- ✅ Professional but human: "I've found that...", "What we see is..."
- ✅ Clear and direct: Just explain it well without being stuffy"""

    # Append custom instructions if enabled
    if include_custom:
        custom = _get_custom_instructions()
        if custom:
            final_prompt = f"{baseline_prompt}\n\n## Additional Custom Instructions\n\n{custom}"
            logger.info(
                "SystemPrompt: base_len=%d, custom_len=%d, custom_preview=%r",
                len(baseline_prompt),
                len(custom),
                custom[:200]
            )
            return final_prompt
        else:
            logger.debug("SystemPrompt: no custom instructions active (base_len=%d)", len(baseline_prompt))
    
    return baseline_prompt


def _build_chaffee_user_prompt(query: str, excerpts: str, style: str) -> str:
    """
    Build the curated user prompt with style-specific instructions.
    """
    # Word limits optimized for quality
    if style == 'detailed':
        target_words = '900-1100'
        min_words = 900
        style_instructions = """🔴 DETAILED MODE REQUIREMENTS (NON-NEGOTIABLE):
  1. LENGTH: 900-1100 words (COUNT THEM!)
  2. STRUCTURE: 2-5 sections with ## Markdown Headings
  3. SECTIONS: Each section has 2-4 paragraphs (4-6 sentences each)
  4. BLANK LINES: MANDATORY double newline (\\n\\n) between EVERY paragraph - no exceptions!
  5. FORMATTING: After each paragraph, press Enter TWICE to create a blank line"""
        paragraph_structure = "Combine related ideas into cohesive paragraphs - Each paragraph should be 4-6 sentences minimum."
    else:
        target_words = '350-450'
        min_words = 350
        style_instructions = """🔵 CONCISE MODE REQUIREMENTS (NON-NEGOTIABLE):
  1. LENGTH: 350-450 words (COUNT THEM!)
  2. NO HEADINGS - just flowing paragraphs
  3. STRUCTURE: 1-2 substantial paragraphs ONLY
  4. Each paragraph: 6-8 sentences minimum
  5. BLANK LINE: Use \\n\\n between the two paragraphs if you write two"""
        paragraph_structure = "CRITICAL: Write as ONE continuous paragraph or maximum TWO paragraphs. Do NOT create 3+ paragraphs. Keep the response flowing without breaks."

    return f"""You are Emulated Dr Anthony Chaffee (AI). Answer this question as if you're explaining it to someone in person - professional but natural.

## User Question
{query}

## Retrieved Context (from your videos and talks)

{excerpts}

## Instructions

**ANSWER STYLE: {style.upper()} ({target_words} WORDS)**

- **ONLY use information from the retrieved context above** - DO NOT add generic medical knowledge or fill in gaps
- **If the context doesn't cover something, explicitly say so** - "I haven't specifically talked about that" or "I don't have content on that specific topic"
- **NEVER recommend non-carnivore foods** - Dr. Chaffee advocates for animal-based eating only
- **ALWAYS speak in first person**: "I recommend", "I've seen", "What I tell people", "I've found"
- **Be specific, not generic**: Don't describe the diet from outside - share what YOU know from the context
- **Avoid third-person**: Don't say "The carnivore diet is..." - say "When you eat carnivore..." or "I've seen..."
- Natural flow: Use "so", "and", "you know", "I mean" where appropriate
- Avoid academic formality: No "moreover", "furthermore", "in conclusion", "has been associated with"
- Avoid overly casual: No "Look", "Here's the deal", "So basically"
- **CITATION FORMAT (CRITICAL)**: Use numbered citations like [1], [2], [3] that correspond to the excerpt numbers in the context above. Example: "As I talked about [1]" or "I've discussed this [2]". Each number should match an excerpt from the retrieved context.
- **CRITICAL LENGTH: {target_words} words (MINIMUM {min_words} words) - This is ABSOLUTELY NON-NEGOTIABLE. COUNT YOUR WORDS BEFORE RESPONDING. If you write less than {min_words} words, START OVER and write more.**
- **PARAGRAPH BREAKS (CRITICAL)**: ALWAYS use double line breaks (\\n\\n) between EVERY paragraph.
- {style_instructions}
- **PARAGRAPH STRUCTURE**: {paragraph_structure}
- **FLOW AND COHESION**: Topics should flow logically, not jump around. Develop each idea fully before moving on.
- **AVOID REPETITIVE TRANSITIONS**: Don't start every paragraph with "I've found", "In my experience", "I've seen" - vary your language naturally.
- **NO GENERIC CONCLUSIONS**: Don't end with "consult a healthcare professional" or "dietary balance" - that's not your style
- **Be confident**: You know carnivore works - don't hedge or undermine your message at the end
- **CRITICAL: Do not hallucinate or add information not in the context** - Stay true to what Dr. Chaffee actually says

TONE: You're Dr. Chaffee explaining from YOUR experience and knowledge - not describing a diet from outside.
VOICE: First person, specific, professional but natural. NOT generic encyclopedia text.
ENDINGS: End naturally without generic disclaimers or hedging. You're confident in what you're saying.

Output MUST be valid **JSON RESPONSE FORMAT** (CRITICAL - MUST be valid JSON):
{{
  "answer": "Markdown text. Use \\\\n\\\\n between paragraphs. MUST be {target_words} words. Use [1], [2], [3] for citations.",
  "citations_used": [1, 2, 3],
  "confidence": 0.85,
  "notes": "Optional brief notes: conflicts seen, gaps, or scope limits."
}}

**IMPORTANT**: The citations_used array should list the excerpt numbers (1, 2, 3, etc.) that you referenced in your answer.

**CRITICAL CITATION FORMAT**: 
- **USE NUMBERED CITATIONS**: [1], [2], [3] etc. that match the excerpt numbers in the context
- **KEEP IT CLEAN**: Just the number in brackets, nothing else
- Example: "I've talked about this before [1] and it's something I see a lot [2]"

**CONFIDENCE SCORING**:
- Set confidence between 0.7-0.95 based on context quality
- 0.9-0.95: Excellent coverage with many relevant excerpts
- 0.8-0.89: Good coverage with solid excerpts
- 0.7-0.79: Adequate coverage but some gaps

Validation requirements:
- Every [N] citation in the answer MUST correspond to an excerpt number from the context.
- Do NOT cite excerpts that weren't provided.
- Keep formatting clean: no stray backslashes, no code fences in answer, no HTML.
- **MEET THE WORD COUNT**: {min_words}+ words is mandatory. Write more content, not less."""


@app.post("/answer", dependencies=[Depends(verify_internal_api_key)])
@app.post("/api/answer", dependencies=[Depends(verify_internal_api_key)])
async def answer_question(request: AnswerRequest):
    """Generate AI-powered answer using RAG with OpenAI and curated Chaffee persona"""
    import logging
    import json
    logger = logging.getLogger(__name__)
    
    try:
        # Load search config from database (tuning dashboard settings)
        search_cfg = get_search_config_from_db()
        
        # Get parameters - use request values if provided, otherwise use DB config
        style = request.style or 'concise'
        # top_k controls how many candidates to fetch from vector search
        initial_top_k = request.top_k if request.top_k is not None else search_cfg.top_k
        # return_top_k controls how many clips are actually used in the LLM prompt
        clips_for_answer = search_cfg.return_top_k
        min_similarity = search_cfg.min_similarity
        max_tokens = 3500 if style == 'detailed' else 1400
        
        # Log search config being used
        logger.info(
            "SearchConfig: initial=%d, min_relevance=%.3f, clips_in_answer=%d, reranker=%s",
            initial_top_k,
            min_similarity,
            clips_for_answer,
            search_cfg.enable_reranker
        )
        
        logger.info(f"Answer request: {request.query[:100]} (style={style})")
        
        # Step 1: Get relevant segments using semantic search
        # Pass the full config to semantic_search so it uses DB settings
        search_request = SearchRequest(
            query=request.query, 
            top_k=initial_top_k,
            min_similarity=min_similarity,
            rerank=search_cfg.enable_reranker
        )
        search_response = await semantic_search(search_request)
        
        if not search_response.results:
            raise HTTPException(status_code=404, detail="No relevant information found")
        
        # Log search pipeline counts
        total_candidates = len(search_response.results)
        
        # Step 2: Limit results to clips_for_answer (return_top_k from tuning dashboard)
        # This is the key setting: "Number of clips to use in answer"
        results_for_llm = search_response.results[:clips_for_answer]
        
        logger.info(
            "SearchQuery: %r | candidates=%d, used_in_answer=%d",
            request.query[:50],
            total_candidates,
            len(results_for_llm)
        )
        
        # Step 3: Build RAG context in the curated format
        # Format: numbered excerpts [1], [2], etc. with video info
        excerpt_parts = []
        source_chunks = []
        
        for idx, result in enumerate(results_for_llm, start=1):
            video_id = result.url.split('v=')[-1].split('&')[0] if 'youtube.com' in result.url else result.id
            timestamp = _format_timestamp(result.start_time_seconds)
            date = result.published_at[:10] if result.published_at else "unknown"
            
            # Use numbered format for cleaner citations
            excerpt_parts.append(
                f'[{idx}] Video: {result.title or "Untitled"}\n    Date: {date}\n    Time: {timestamp}\n    Text: "{result.text}"'
            )
            source_chunks.append({
                "index": idx,  # Add index for citation mapping
                "id": result.id,
                "video_id": video_id,
                "title": result.title,
                "url": result.url,
                "start_time": result.start_time_seconds,
                "timestamp": timestamp,
                "similarity": round(result.similarity, 3),
                "published_at": result.published_at
            })
        
        excerpts = "\n\n".join(excerpt_parts)
        
        # Step 4: Build curated prompts (includes custom instructions from DB)
        system_prompt = _build_chaffee_system_prompt(style, include_custom=True)
        user_prompt = _build_chaffee_user_prompt(request.query, excerpts, style)
        
        # Step 5: Query OpenAI
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            logger.error("OPENAI_API_KEY not configured")
            raise HTTPException(status_code=503, detail="OpenAI API key not configured")
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_api_key)
        except ImportError as e:
            logger.error(f"Failed to import OpenAI: {e}")
            raise HTTPException(status_code=503, detail="OpenAI library not available")
        
        # Use SUMMARIZER_MODEL from tuning dashboard, fall back to OPENAI_MODEL for backward compatibility
        model = os.getenv('SUMMARIZER_MODEL') or os.getenv('OPENAI_MODEL', 'gpt-4.1')
        temperature = float(os.getenv('SUMMARIZER_TEMPERATURE', '0.3'))
        
        # Log summarizer model being used
        logger.info(
            "SummarizerCall: model=%s, query_preview=%r, clips=%d, temperature=%.2f",
            model,
            request.query[:100],
            len(results_for_llm),
            temperature
        )
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,  # Configurable via tuning dashboard
            response_format={"type": "json_object"}  # Ensure JSON output
        )
        
        content = response.choices[0].message.content
        
        # Calculate cost (gpt-4o-mini pricing)
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        # gpt-4o-mini: $0.15/1M input, $0.60/1M output
        cost = (input_tokens * 0.00015 + output_tokens * 0.0006) / 1000
        
        logger.info(f"Token usage - Input: {input_tokens}, Output: {output_tokens}, Cost: ${cost:.4f}")
        
        # Parse JSON response
        try:
            # Handle potential code fences
            json_content = content
            json_match = content.find('```')
            if json_match != -1:
                # Extract JSON from code fence
                start = content.find('{')
                end = content.rfind('}') + 1
                if start != -1 and end > start:
                    json_content = content[start:end]
            
            parsed = json.loads(json_content)
            
            # Validate word count
            word_count = len(parsed.get('answer', '').split())
            min_words = 900 if style == 'detailed' else 350
            logger.info(f"Generated answer: {word_count} words (min: {min_words})")
            
            if word_count < min_words * 0.5:
                logger.warning(f"Answer is severely short: {word_count} words")
                parsed['notes'] = (parsed.get('notes') or '') + f" [Warning: Only {word_count} words]"
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {content[:500]}")
            # Fallback: return raw content as answer
            parsed = {
                "answer": content,
                "citations_used": [],
                "confidence": 0.7,
                "notes": "Response was not valid JSON, returning raw text"
            }
        
        # Build structured citations from citations_used indices
        citations_used = parsed.get('citations_used', [])
        structured_citations = []
        
        # Create a lookup dict for source chunks by index
        chunks_by_index = {chunk['index']: chunk for chunk in source_chunks}
        
        for citation_idx in citations_used:
            if citation_idx in chunks_by_index:
                chunk = chunks_by_index[citation_idx]
                structured_citations.append({
                    "index": citation_idx,
                    "video_id": chunk['video_id'],
                    "title": chunk.get('title') or 'Untitled Video',
                    "t_start_s": chunk['start_time'],
                    "clip_time": chunk['timestamp'],
                    "published_at": chunk.get('published_at') or None
                })
        
        logger.info(f"✅ RAG answer generated: ${cost:.4f}, citations: {len(structured_citations)}")
        
        return {
            "answer": parsed.get('answer', ''),
            "answer_md": parsed.get('answer', ''),  # Alias for frontend compatibility
            "citations": structured_citations,
            "confidence": parsed.get('confidence', 0.8),
            "notes": parsed.get('notes'),
            "sources": source_chunks,
            "query": request.query,
            "style": style,
            "chunks_used": len(source_chunks),
            "cost_usd": cost,
            "used_chunk_ids": [chunks_by_index.get(idx, {}).get('id', '') for idx in citations_used if idx in chunks_by_index]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Answer generation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Answer generation failed: {str(e)}")

@app.get("/answer", dependencies=[Depends(verify_internal_api_key)])
@app.get("/api/answer", dependencies=[Depends(verify_internal_api_key)])
async def answer_get(query: str, top_k: int = 10, style: str = 'concise'):
    """GET endpoint for answer (for frontend compatibility)"""
    request = SearchRequest(query=query, top_k=top_k)
    return await answer_question(request)


# =============================================================================
# Answer Cache Endpoints (for frontend proxy)
# =============================================================================

class CacheLookupRequest(BaseModel):
    query: str
    style: str = 'concise'
    similarity_threshold: float = 0.92

class CacheSaveRequest(BaseModel):
    query: str
    style: str
    answer_md: str
    citations: List[Dict[str, Any]]
    confidence: float
    notes: Optional[str] = None
    used_chunk_ids: List[str] = []
    source_clips: List[Dict[str, Any]] = []
    ttl_hours: int = 336

class ChunksRequest(BaseModel):
    query: str
    top_k: int = 100
    use_semantic: bool = True


@app.post("/answer/cache/lookup", dependencies=[Depends(verify_internal_api_key)])
async def answer_cache_lookup(request: CacheLookupRequest):
    """
    Look up cached answer by semantic similarity.
    Returns cached answer if found, null otherwise.
    """
    try:
        # Generate embedding for the query
        generator = get_embedding_generator()
        embeddings = generator.generate_embeddings([request.query])
        
        if not embeddings or len(embeddings) == 0:
            return {"cached": None}
        
        query_embedding = embeddings[0]
        embedding_list = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding
        
        # Get active model key
        model_key = get_active_model_key()
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Search for similar cached answers
        cur.execute("""
            SELECT 
                ac.id,
                ac.query_text,
                ac.answer_md,
                ac.citations,
                ac.confidence,
                ac.notes,
                ac.used_chunk_ids,
                ac.source_clips,
                ac.created_at,
                ac.access_count,
                1 - (ace.embedding <=> %s::vector) as similarity
            FROM answer_cache ac
            JOIN answer_cache_embeddings ace ON ac.id = ace.answer_cache_id
            WHERE ace.model_key = %s
              AND ac.style = %s
              AND 1 - (ace.embedding <=> %s::vector) >= %s
            ORDER BY similarity DESC
            LIMIT 1
        """, [str(embedding_list), model_key, request.style, str(embedding_list), request.similarity_threshold])
        
        result = cur.fetchone()
        
        if result:
            # Update access count
            cur.execute("""
                UPDATE answer_cache 
                SET accessed_at = NOW(), access_count = access_count + 1
                WHERE id = %s
            """, [result['id']])
            conn.commit()
            
            cur.close()
            conn.close()
            
            logger.info(f"Cache hit for query: {request.query[:50]}... (similarity: {result['similarity']:.2f})")
            
            return {
                "cached": {
                    "id": result['id'],
                    "query_text": result['query_text'],
                    "answer_md": result['answer_md'],
                    "citations": result['citations'],
                    "confidence": result['confidence'],
                    "notes": result['notes'],
                    "used_chunk_ids": result['used_chunk_ids'],
                    "source_clips": result['source_clips'],
                    "created_at": result['created_at'].isoformat() if result['created_at'] else None,
                    "access_count": result['access_count'],
                    "similarity": float(result['similarity'])
                }
            }
        
        cur.close()
        conn.close()
        
        logger.info(f"Cache miss for query: {request.query[:50]}...")
        return {"cached": None}
        
    except Exception as e:
        logger.error(f"Cache lookup failed: {str(e)}", exc_info=True)
        return {"cached": None, "error": str(e)}


@app.post("/answer/cache/save", dependencies=[Depends(verify_internal_api_key)])
async def answer_cache_save(request: CacheSaveRequest):
    """
    Save answer to cache with embedding for semantic lookup.
    """
    try:
        # Generate embedding for the query
        generator = get_embedding_generator()
        embeddings = generator.generate_embeddings([request.query])
        
        if not embeddings or len(embeddings) == 0:
            raise HTTPException(status_code=500, detail="Failed to generate embedding")
        
        query_embedding = embeddings[0]
        embedding_list = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding
        
        # Get active model key
        model_key = get_active_model_key()
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Insert into answer_cache table
        cur.execute("""
            INSERT INTO answer_cache (
                query_text, style, answer_md, citations, 
                confidence, notes, used_chunk_ids, source_clips, ttl_hours
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, [
            request.query,
            request.style,
            request.answer_md,
            json.dumps(request.citations),
            request.confidence,
            request.notes,
            request.used_chunk_ids,
            json.dumps(request.source_clips),
            request.ttl_hours
        ])
        
        cache_id = cur.fetchone()['id']
        
        # Insert embedding into answer_cache_embeddings table
        cur.execute("""
            INSERT INTO answer_cache_embeddings (
                answer_cache_id, model_key, embedding
            ) VALUES (%s, %s, %s::vector)
        """, [cache_id, model_key, str(embedding_list)])
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Cached answer for query: {request.query[:50]}... (id: {cache_id})")
        
        return {"success": True, "cache_id": cache_id}
        
    except Exception as e:
        logger.error(f"Cache save failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cache save failed: {str(e)}")


@app.post("/answer/chunks", dependencies=[Depends(verify_internal_api_key)])
async def get_answer_chunks(request: ChunksRequest):
    """
    Get relevant chunks for RAG answer generation.
    Uses semantic search if embedding available, falls back to text search.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        chunks = []
        
        if request.use_semantic:
            # Generate embedding for the query
            generator = get_embedding_generator()
            embeddings = generator.generate_embeddings([request.query])
            
            if embeddings and len(embeddings) > 0:
                query_embedding = embeddings[0]
                embedding_list = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding
                
                cur.execute("""
                    SELECT 
                        seg.id,
                        s.id as source_id,
                        s.source_id as video_id,
                        s.title,
                        seg.text,
                        seg.start_sec as start_time_seconds,
                        seg.end_sec as end_time_seconds,
                        s.published_at,
                        s.source_type,
                        1 - (seg.embedding <=> %s::vector) as similarity
                    FROM segments seg
                    JOIN sources s ON seg.source_id = s.id
                    WHERE seg.embedding IS NOT NULL
                    ORDER BY seg.embedding <=> %s::vector
                    LIMIT %s
                """, [str(embedding_list), str(embedding_list), request.top_k])
                
                chunks = cur.fetchall()
        
        # Fallback to text search if no semantic results
        if not chunks:
            cur.execute("""
                SELECT 
                    seg.id,
                    s.id as source_id,
                    s.source_id as video_id,
                    s.title,
                    seg.text,
                    seg.start_sec as start_time_seconds,
                    seg.end_sec as end_time_seconds,
                    s.published_at,
                    s.source_type,
                    0.5 as similarity
                FROM segments seg
                JOIN sources s ON seg.source_id = s.id
                WHERE seg.text ILIKE %s
                ORDER BY s.published_at DESC
                LIMIT %s
            """, [f'%{request.query}%', request.top_k])
            
            chunks = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Convert to serializable format
        result_chunks = []
        for chunk in chunks:
            result_chunks.append({
                "id": chunk['id'],
                "source_id": chunk['source_id'],
                "video_id": chunk['video_id'],
                "title": chunk['title'],
                "text": chunk['text'],
                "start_time_seconds": float(chunk['start_time_seconds']) if chunk['start_time_seconds'] else 0,
                "end_time_seconds": float(chunk['end_time_seconds']) if chunk['end_time_seconds'] else 0,
                "published_at": chunk['published_at'].isoformat() if chunk['published_at'] else None,
                "source_type": chunk['source_type'],
                "similarity": float(chunk['similarity']) if chunk['similarity'] else 0.5
            })
        
        return {
            "chunks": result_chunks,
            "total": len(result_chunks),
            "query": request.query
        }
        
    except Exception as e:
        logger.error(f"Chunk retrieval failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chunk retrieval failed: {str(e)}")


# =============================================================================
# Embedding Model Endpoints
# =============================================================================

@app.get("/embeddings/models")
async def list_embedding_models():
    """List available embedding models in the database."""
    models = get_available_embedding_models()
    return {"models": models}


@app.get("/embeddings/active")
async def get_active_embedding_model():
    """Get the currently active embedding model."""
    model_key = get_active_model_key()
    return {"active_model": model_key}


@app.get("/api/jobs", dependencies=[Depends(verify_admin_token)])
async def list_jobs():
    """List all processing jobs"""
    return {"jobs": list(processing_jobs.values())}

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific job (no auth required for status checks)"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return processing_jobs[job_id]

@app.post("/api/upload/youtube-takeout", dependencies=[Depends(verify_admin_token)])
async def upload_youtube_takeout(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    description: Optional[str] = None
):
    """Upload and process Google Takeout ZIP with YouTube captions"""
    
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")
    
    # Create job
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "status": "pending",
        "source_type": "youtube_takeout",
        "total_files": 0,
        "processed_files": 0,
        "failed_files": 0,
        "current_file": None,
        "errors": [],
        "created_at": datetime.now(),
        "completed_at": None,
        "description": description or f"YouTube Takeout upload: {file.filename}"
    }
    processing_jobs[job_id] = job
    
    # Process in background
    background_tasks.add_task(process_youtube_takeout, job_id, file)
    
    return {"job_id": job_id, "message": "Upload started", "status": "pending"}

@app.post("/api/upload/zoom-transcripts", dependencies=[Depends(verify_admin_token)])
async def upload_zoom_transcripts(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    description: Optional[str] = None
):
    """Upload and process Zoom transcript files (VTT, SRT, or TXT)"""
    
    # Validate file types
    allowed_extensions = {'.vtt', '.srt', '.txt'}
    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File {file.filename} has unsupported extension. Allowed: {allowed_extensions}"
            )
    
    # Create job
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "status": "pending",
        "source_type": "zoom",
        "total_files": len(files),
        "processed_files": 0,
        "failed_files": 0,
        "current_file": None,
        "errors": [],
        "created_at": datetime.now(),
        "completed_at": None,
        "description": description or f"Zoom transcripts upload: {len(files)} files"
    }
    processing_jobs[job_id] = job
    
    # Process in background
    background_tasks.add_task(process_zoom_transcripts, job_id, files)
    
    return {"job_id": job_id, "message": "Upload started", "status": "pending"}

@app.post("/api/upload/manual-transcripts", dependencies=[Depends(verify_admin_token)])
async def upload_manual_transcripts(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    source_type: str = "manual",
    description: Optional[str] = None
):
    """Upload and process manual transcript files from any source"""
    
    # Create job
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "status": "pending",
        "source_type": source_type,
        "total_files": len(files),
        "processed_files": 0,
        "failed_files": 0,
        "current_file": None,
        "errors": [],
        "created_at": datetime.now(),
        "completed_at": None,
        "description": description or f"Manual transcripts upload: {len(files)} files"
    }
    processing_jobs[job_id] = job
    
    # Process in background
    background_tasks.add_task(process_manual_transcripts, job_id, files, source_type)
    
    return {"job_id": job_id, "message": "Upload started", "status": "pending"}

@app.post("/api/sync/new-videos", dependencies=[Depends(verify_admin_token)])
async def sync_new_videos(
    background_tasks: BackgroundTasks,
    limit: int = 10,
    use_proxy: bool = True
):
    """Manually trigger sync of new YouTube videos"""
    
    # Create job
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "status": "pending",
        "source_type": "youtube_sync",
        "total_files": 0,  # Will be updated when we discover videos
        "processed_files": 0,
        "failed_files": 0,
        "current_file": None,
        "errors": [],
        "created_at": datetime.now(),
        "completed_at": None,
        "description": f"Sync new YouTube videos (limit: {limit})"
    }
    processing_jobs[job_id] = job
    
    # Process in background
    background_tasks.add_task(sync_youtube_videos, job_id, limit, use_proxy)
    
    return {"job_id": job_id, "message": "Sync started", "status": "pending"}

# Background processing functions

async def process_youtube_takeout(job_id: str, file: UploadFile):
    """Process YouTube Takeout ZIP file"""
    job = processing_jobs[job_id]
    job["status"] = "processing"
    
    try:
        # Read ZIP file
        content = await file.read()
        
        with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
            # Find SRT files
            srt_files = [f for f in zip_file.namelist() if f.endswith('.srt')]
            job["total_files"] = len(srt_files)
            
            if not srt_files:
                raise Exception("No SRT files found in ZIP archive")
            
            # Initialize processor
            processor = SRTProcessor()
            
            # Process each SRT file
            for srt_path in srt_files:
                job["current_file"] = srt_path
                
                try:
                    # Extract and process SRT content
                    srt_content = zip_file.read(srt_path).decode('utf-8')
                    
                    # Create temporary file
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as temp_file:
                        temp_file.write(srt_content)
                        temp_path = Path(temp_file.name)
                    
                    # Process SRT file
                    success = processor.process_srt_file(temp_path)
                    
                    # Cleanup
                    temp_path.unlink()
                    
                    if success:
                        job["processed_files"] += 1
                    else:
                        job["failed_files"] += 1
                        job["errors"].append(f"Failed to process {srt_path}")
                        
                except Exception as e:
                    job["failed_files"] += 1
                    job["errors"].append(f"Error processing {srt_path}: {str(e)}")
        
        job["status"] = "completed"
        job["completed_at"] = datetime.now()
        
    except Exception as e:
        job["status"] = "failed"
        job["errors"].append(f"Job failed: {str(e)}")
        job["completed_at"] = datetime.now()

async def process_zoom_transcripts(job_id: str, files: List[UploadFile]):
    """Process Zoom transcript files"""
    job = processing_jobs[job_id]
    job["status"] = "processing"
    
    try:
        processor = SRTProcessor()
        
        for file in files:
            job["current_file"] = file.filename
            
            try:
                content = await file.read()
                
                # Create temporary file
                import tempfile
                suffix = Path(file.filename).suffix
                with tempfile.NamedTemporaryFile(mode='wb', suffix=suffix, delete=False) as temp_file:
                    temp_file.write(content)
                    temp_path = Path(temp_file.name)
                
                # Process based on file type
                if suffix.lower() == '.srt':
                    success = processor.process_srt_file(temp_path)
                elif suffix.lower() in ['.vtt', '.txt']:
                    # Convert to SRT format first, then process
                    success = process_zoom_vtt_or_txt(temp_path, processor)
                else:
                    success = False
                
                # Cleanup
                temp_path.unlink()
                
                if success:
                    job["processed_files"] += 1
                else:
                    job["failed_files"] += 1
                    job["errors"].append(f"Failed to process {file.filename}")
                    
            except Exception as e:
                job["failed_files"] += 1
                job["errors"].append(f"Error processing {file.filename}: {str(e)}")
        
        job["status"] = "completed"
        job["completed_at"] = datetime.now()
        
    except Exception as e:
        job["status"] = "failed"
        job["errors"].append(f"Job failed: {str(e)}")
        job["completed_at"] = datetime.now()

async def process_manual_transcripts(job_id: str, files: List[UploadFile], source_type: str):
    """Process manual transcript files"""
    # Similar to Zoom processing but with different source type
    job = processing_jobs[job_id]
    job["status"] = "processing"
    
    try:
        processor = SRTProcessor()
        
        for file in files:
            job["current_file"] = file.filename
            
            try:
                content = await file.read()
                
                # Create temporary file and process
                import tempfile
                suffix = Path(file.filename).suffix
                with tempfile.NamedTemporaryFile(mode='wb', suffix=suffix, delete=False) as temp_file:
                    temp_file.write(content)
                    temp_path = Path(temp_file.name)
                
                # Process file (customize based on source_type if needed)
                success = processor.process_srt_file(temp_path)
                temp_path.unlink()
                
                if success:
                    job["processed_files"] += 1
                else:
                    job["failed_files"] += 1
                    job["errors"].append(f"Failed to process {file.filename}")
                    
            except Exception as e:
                job["failed_files"] += 1
                job["errors"].append(f"Error processing {file.filename}: {str(e)}")
        
        job["status"] = "completed" 
        job["completed_at"] = datetime.now()
        
    except Exception as e:
        job["status"] = "failed"
        job["errors"].append(f"Job failed: {str(e)}")
        job["completed_at"] = datetime.now()

async def sync_youtube_videos(job_id: str, limit: int, use_proxy: bool):
    """Sync new YouTube videos using existing pipeline with proxy support"""
    job = processing_jobs[job_id]
    job["status"] = "processing"
    
    try:
        # Import YouTube ingestion pipeline
        from scripts.ingest_youtube_enhanced import EnhancedYouTubeIngester, IngestionConfig
        
        # Configure with proxy if needed
        config = IngestionConfig(
            source='api',
            limit=limit,
            skip_shorts=True,
            youtube_api_key=os.getenv('YOUTUBE_API_KEY'),
            proxy=os.getenv('NORDVPN_PROXY') if use_proxy else None
        )
        
        # Run ingestion
        ingester = EnhancedYouTubeIngester(config)
        await ingester.run_async()  # Implement async version
        
        job["status"] = "completed"
        job["completed_at"] = datetime.now()
        job["processed_files"] = limit  # Approximate
        
    except Exception as e:
        job["status"] = "failed"
        job["errors"].append(f"Sync failed: {str(e)}")
        job["completed_at"] = datetime.now()

def process_zoom_vtt_or_txt(file_path: Path, processor: SRTProcessor) -> bool:
    """Convert Zoom VTT/TXT to SRT format and process"""
    try:
        # Basic VTT to SRT conversion
        # Implement based on Zoom's specific format
        # This is a placeholder - actual implementation depends on Zoom format
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Convert to SRT format (implement specific conversion logic)
        srt_content = convert_to_srt(content)
        
        # Create temporary SRT file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as temp_file:
            temp_file.write(srt_content)
            srt_path = Path(temp_file.name)
        
        # Process as SRT
        success = processor.process_srt_file(srt_path)
        srt_path.unlink()
        
        return success
        
    except Exception as e:
        print(f"Error converting VTT/TXT: {e}")
        return False

def convert_to_srt(content: str) -> str:
    """Convert VTT or TXT content to SRT format"""
    # Placeholder implementation
    # Actual implementation depends on the specific format of Zoom transcripts
    return content

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
