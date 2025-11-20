#!/usr/bin/env python3
"""
FastAPI main application for Ask Dr. Chaffee
Multi-source transcript processing with admin interface
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
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
from scripts.common.embeddings import EmbeddingGenerator

# Import tuning router
from .tuning import router as tuning_router

app = FastAPI(
    title="Ask Dr. Chaffee API",
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
    """
    import os
    
    # Skip warmup on Render Starter (512MB) - not enough memory
    # Set SKIP_WARMUP=true to disable, or let it auto-detect low memory
    skip_warmup = os.getenv('SKIP_WARMUP', '').lower() == 'true'
    
    if skip_warmup:
        logger.info("⏭️  Skipping embedding model warmup (SKIP_WARMUP=true)")
        return
    
    try:
        logger.info("🚀 Warming up embedding model on startup...")
        generator = get_embedding_generator()
        # Generate a dummy embedding to load the model
        _ = generator.generate_embeddings(["warmup"])
        logger.info("✅ Embedding model warmed up successfully")
    except MemoryError as e:
        logger.warning(f"⚠️ Out of memory during warmup: {e}")
        logger.info("💡 Model will load on first request (~20-25s delay)")
        logger.info("💡 To fix: upgrade Render plan or set SKIP_WARMUP=true")
    except Exception as e:
        logger.warning(f"⚠️ Failed to warm up embedding model: {e}")
        logger.info("💡 Model will load on first request instead")

# Security
security = HTTPBearer()
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin-secret-key")

# Background job tracking
processing_jobs: Dict[str, Dict[str, Any]] = {}

# Initialize embedding generator (lazy load)
_embedding_generator = None

def get_embedding_generator():
    global _embedding_generator
    if _embedding_generator is None:
        # Read from .env (single source of truth)
        provider = os.getenv('EMBEDDING_PROVIDER', 'sentence-transformers')
        model = os.getenv('EMBEDDING_MODEL', 'BAAI/bge-small-en-v1.5')
        
        _embedding_generator = EmbeddingGenerator(
            embedding_provider=provider,
            model_name=model
        )
        logger.info(f"Initialized embedding generator: {provider} / {model}")
    return _embedding_generator

def get_active_model_key():
    """Get the active model key from config"""
    import json
    from pathlib import Path
    
    # Load config
    config_path = Path(__file__).parent.parent / 'config' / 'embedding_models.json'
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Get active model from env or config
        active_model = os.getenv('EMBEDDING_QUERY_MODEL', config.get('active_query_model', 'gte-qwen2-1.5b'))
        return active_model
    except Exception as e:
        logger.warning(f"Failed to load embedding config: {e}")
        return 'gte-qwen2-1.5b'

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
                    # Fallback to common dimension
                    dimensions = 1536
                
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
                    model_key = dimension_to_model.get(dimensions, 'gte-qwen2-1.5b')
                    
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
    top_k: Optional[int] = 50
    min_similarity: Optional[float] = 0.5
    rerank: Optional[bool] = True

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

# Authentication
async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    return credentials.credentials

@app.get("/")
@app.head("/")
async def root():
    """Root endpoint"""
    return {"status": "ok", "service": "Ask Dr. Chaffee API"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

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

@app.get("/search")
@app.get("/api/search")
async def search_get(q: str, top_k: int = 50, min_similarity: float = 0.5):
    """GET endpoint for search (for frontend compatibility)"""
    request = SearchRequest(query=q, top_k=top_k, min_similarity=min_similarity)
    return await semantic_search(request)

@app.post("/search", response_model=SearchResponse)
async def search_post(request: SearchRequest):
    """POST endpoint for search (alternative path)"""
    return await semantic_search(request)

@app.post("/api/search", response_model=SearchResponse)
async def semantic_search(request: SearchRequest):
    """
    Semantic search with optional reranking
    
    1. Detect available embeddings in database
    2. Generate query embedding with matching model
    3. Search database using vector similarity
    4. Optionally rerank results for better quality
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Search request: {request.query}")
        
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
            request.min_similarity,
            request.top_k
        ]
        
        # Execute query with appropriate parameters
        cur.execute(search_query, query_params)
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        # Optional reranking
        if request.rerank and len(results) > 0:
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

@app.post("/embed")
@app.post("/api/embed")
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

@app.post("/answer")
@app.post("/api/answer")
async def answer_question(request: AnswerRequest):
    """Generate AI-powered answer using RAG with OpenAI"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Get top_k from request, env var, or default to 50
        top_k = request.top_k or int(os.getenv('ANSWER_TOP_K', '50'))
        
        logger.info(f"Answer request: {request.query} (top_k={top_k})")
        
        # Step 1: Get relevant segments using semantic search
        search_request = SearchRequest(query=request.query, top_k=top_k)
        search_response = await semantic_search(search_request)
        
        if not search_response.results:
            raise HTTPException(status_code=404, detail="No relevant information found")
        
        # Step 2: Build RAG context from top results
        context_parts = []
        citations = []
        
        # Use all retrieved results for context (up to top_k)
        for result in search_response.results:
            # Format context with source info
            context_parts.append(
                f"[{result.title}]: {result.text}"
            )
            citations.append({
                "id": result.id,
                "title": result.title,
                "url": result.url,
                "start_time": result.start_time_seconds,
                "similarity": round(result.similarity, 3)
            })
        
        context = "\n\n".join(context_parts)
        
        # Step 3: Create RAG prompt with Chaffee personality
        prompt = f"""You are Dr. Anthony Chaffee, a neurosurgeon and carnivore diet advocate. Answer this question in YOUR voice, based on your actual content below.

YOUR SPEAKING STYLE:
- Direct, confident, evidence-based
- Use evolutionary biology and clinical experience as foundations
- Emphasize eliminating plant toxins (lectins, phytates, oxalates)
- Focus on autoimmune conditions and metabolic health
- Challenge mainstream dietary guidelines when appropriate
- Use phrases like "the human body is designed to...", "evolutionarily speaking...", "in my clinical experience..."
- Be practical and actionable

QUESTION: {request.query}

YOUR ACTUAL CONTENT (from your videos):
{context}

Answer as Dr. Chaffee would, synthesizing the information above. Be conversational but authoritative. If the content doesn't fully cover the question, say so honestly and suggest what you'd need to research further."""
        
        # Step 4: Query OpenAI
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
        
        response = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4-turbo'),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.1  # Low temperature for medical accuracy
        )
        
        answer = response.choices[0].message.content
        
        # Calculate cost
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = (input_tokens * 0.01 + output_tokens * 0.03) / 1000
        
        logger.info(f"✅ RAG answer generated: ${cost:.4f}")
        
        return {
            "answer": answer,
            "sources": citations,
            "query": request.query,
            "chunks_used": len(citations),
            "cost_usd": cost
        }
        
    except Exception as e:
        logger.error(f"Answer generation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Answer generation failed: {str(e)}")

@app.get("/answer")
@app.get("/api/answer")
async def answer_get(query: str, top_k: int = 10, style: str = 'concise'):
    """GET endpoint for answer (for frontend compatibility)"""
    request = SearchRequest(query=query, top_k=top_k)
    return await answer_question(request)

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
