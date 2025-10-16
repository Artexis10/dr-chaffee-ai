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
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np

# Import our existing processors
import sys
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(backend_path)
from scripts.process_srt_files import SRTProcessor
from scripts.common.database_upsert import DatabaseUpserter
from scripts.common.transcript_common import TranscriptSegment
from scripts.common.embeddings import EmbeddingGenerator

app = FastAPI(
    title="Ask Dr. Chaffee API",
    description="Multi-source transcript processing and LLM search",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        # Use OpenAI for production if available, otherwise use small local model
        if os.getenv('OPENAI_API_KEY'):
            _embedding_generator = EmbeddingGenerator(
                embedding_provider='openai',
                model_name='text-embedding-3-large'
            )
        else:
            # Fallback to tiny model for free tier
            _embedding_generator = EmbeddingGenerator(
                embedding_provider='local',
                model_name='sentence-transformers/all-MiniLM-L6-v2'  # Only 80MB!
            )
    return _embedding_generator

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
    
    1. Generate query embedding
    2. Search database using vector similarity
    3. Optionally rerank results for better quality
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Search request: {request.query}")
        
        # Generate query embedding
        logger.info("Loading embedding generator...")
        generator = get_embedding_generator()
        logger.info("Generating embeddings...")
        embeddings = generator.generate_embeddings([request.query])
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        if not embeddings or len(embeddings) == 0:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        
        query_embedding = embeddings[0]
        embedding_dim = len(query_embedding)
        
        # Check if embedding dimensions match database
        if embedding_dim != 1536:
            raise HTTPException(
                status_code=503, 
                detail=f"Embedding dimension mismatch: query={embedding_dim}, database=1536. Please set OPENAI_API_KEY environment variable."
            )
        
        # Connect to database
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Semantic search query
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
                s.url,
                1 - (seg.embedding <=> %s::vector) as similarity
            FROM segments seg
            JOIN sources s ON seg.video_id = s.source_id
            WHERE seg.speaker_label = 'Chaffee'
              AND seg.embedding IS NOT NULL
              AND 1 - (seg.embedding <=> %s::vector) >= %s
            ORDER BY similarity DESC
            LIMIT %s
        """
        
        # Convert embedding to list
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

@app.get("/answer")
@app.get("/api/answer")
async def answer_get(query: str, style: str = 'concise'):
    """GET endpoint for answer (for frontend compatibility)"""
    # Simple placeholder - return search results formatted as answer
    search_request = SearchRequest(query=query, top_k=5)
    search_response = await semantic_search(search_request)
    
    if not search_response.results:
        raise HTTPException(status_code=404, detail="No relevant information found")
    
    # Format as simple answer
    answer_text = f"Based on Dr. Chaffee's content:\n\n"
    for i, result in enumerate(search_response.results[:3], 1):
        answer_text += f"{i}. {result.text}\n\n"
    
    return {
        "answer": answer_text,
        "sources": search_response.results,
        "query": query
    }

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
