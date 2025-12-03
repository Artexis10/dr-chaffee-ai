"""
Feedback API Router

Provides endpoints for:
- Creating feedback (answers, tuning, global)
- Listing feedback (admin view)
- Logging AI requests
"""

import os
import logging
from datetime import datetime, date
from typing import Optional, List, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor

from .tuning import require_tuning_auth
from .utils.request_id import get_request_id, get_session_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


# =============================================================================
# Pydantic Models
# =============================================================================

class FeedbackCreate(BaseModel):
    """Request body for creating feedback."""
    target_type: Literal["answer", "tuning_internal", "global"]
    target_id: Optional[str] = None
    rating: Optional[int] = Field(None, ge=-2, le=1)  # -2=broken, -1=bad, 0=neutral, 1=good
    tags: Optional[List[str]] = None
    comment: Optional[str] = Field(None, max_length=5000)
    metadata: Optional[dict] = None  # Additional context from frontend


class FeedbackResponse(BaseModel):
    """Response after creating feedback."""
    success: bool
    feedback_id: str
    message: str = "Feedback submitted successfully"


class FeedbackItem(BaseModel):
    """Single feedback item for list view."""
    id: str
    target_type: str
    target_id: Optional[str]
    rating: Optional[int]
    tags: Optional[List[str]]
    comment: Optional[str]
    metadata: Optional[dict]
    created_at: datetime
    # Joined fields for answer feedback
    input_text_snippet: Optional[str] = None
    output_text_snippet: Optional[str] = None
    model_name: Optional[str] = None


class FeedbackListResponse(BaseModel):
    """Response for feedback list endpoint."""
    items: List[FeedbackItem]
    total: int
    page: int
    page_size: int


class AiRequestCreate(BaseModel):
    """Internal model for logging AI requests."""
    user_id: Optional[int] = None
    request_type: str
    input_text: str
    output_text: Optional[str] = None
    model_name: str
    rag_profile_id: Optional[str] = None
    custom_instruction_id: Optional[str] = None
    search_config_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Optional[dict] = None


# =============================================================================
# Database Connection
# =============================================================================

def get_db_connection():
    """Get database connection."""
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


# =============================================================================
# Helper Functions
# =============================================================================

def log_ai_request(
    request_type: str,
    input_text: str,
    model_name: str,
    output_text: Optional[str] = None,
    user_id: Optional[int] = None,
    rag_profile_id: Optional[str] = None,
    custom_instruction_id: Optional[str] = None,
    search_config_id: Optional[str] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cost_usd: Optional[float] = None,
    latency_ms: Optional[float] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Optional[str]:
    """
    Log an AI request to the database.
    
    Returns the ai_request_id (UUID string) on success, None on failure.
    This is a fire-and-forget operation - errors are logged but not raised.
    """
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ai_requests (
                        user_id, request_type, input_text, output_text, model_name,
                        rag_profile_id, custom_instruction_id, search_config_id,
                        request_id, session_id, input_tokens, output_tokens,
                        cost_usd, latency_ms, success, error_message, metadata
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING id
                """, [
                    user_id,
                    request_type,
                    input_text[:10000] if input_text else None,  # Truncate if too long
                    output_text[:50000] if output_text else None,  # Truncate if too long
                    model_name,
                    rag_profile_id,
                    custom_instruction_id,
                    search_config_id,
                    request_id,
                    session_id,
                    input_tokens,
                    output_tokens,
                    cost_usd,
                    latency_ms,
                    success,
                    error_message[:500] if error_message else None,
                    psycopg2.extras.Json(metadata) if metadata else None,
                ])
                result = cur.fetchone()
                conn.commit()
                
                ai_request_id = str(result['id']) if result else None
                logger.info(f"Logged AI request: type={request_type}, id={ai_request_id}")
                return ai_request_id
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"Failed to log AI request: {e}")
        return None


def get_ai_request_metadata(ai_request_id: str) -> Optional[dict]:
    """
    Fetch metadata from an ai_request for attaching to feedback.
    
    Returns dict with model_name, rag_profile_id, custom_instruction_id, search_config_id, request_type.
    """
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT model_name, rag_profile_id, custom_instruction_id, search_config_id, request_type
                    FROM ai_requests
                    WHERE id = %s
                """, [ai_request_id])
                result = cur.fetchone()
                if result:
                    return dict(result)
                return None
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"Failed to fetch AI request metadata: {e}")
        return None


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("", response_model=FeedbackResponse)
@router.post("/", response_model=FeedbackResponse)
async def create_feedback(feedback: FeedbackCreate, request: Request):
    """
    Create a feedback event.
    
    Supports three target types:
    - 'answer': Feedback on a specific AI answer (target_id = ai_request_id)
    - 'tuning_internal': Feedback on tuning configs (target_id = profile/config ID)
    - 'global': General feedback (target_id = route or null)
    
    For 'answer' feedback, automatically attaches model/profile metadata from ai_requests.
    """
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Build metadata
                metadata = feedback.metadata or {}
                
                # For answer feedback, enrich with ai_request metadata
                if feedback.target_type == "answer" and feedback.target_id:
                    ai_metadata = get_ai_request_metadata(feedback.target_id)
                    if ai_metadata:
                        metadata.update({
                            "model_name": ai_metadata.get("model_name"),
                            "rag_profile_id": ai_metadata.get("rag_profile_id"),
                            "custom_instruction_id": ai_metadata.get("custom_instruction_id"),
                            "search_config_id": ai_metadata.get("search_config_id"),
                            "request_type": ai_metadata.get("request_type"),
                        })
                
                # Get session ID from request context
                session_id = get_session_id() or request.headers.get("X-Session-ID")
                
                # Insert feedback
                cur.execute("""
                    INSERT INTO feedback_events (
                        target_type, target_id, rating, tags, comment, metadata, session_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, [
                    feedback.target_type,
                    feedback.target_id,
                    feedback.rating,
                    psycopg2.extras.Json(feedback.tags) if feedback.tags else None,
                    feedback.comment,
                    psycopg2.extras.Json(metadata) if metadata else None,
                    session_id,
                ])
                
                result = cur.fetchone()
                conn.commit()
                
                feedback_id = str(result['id'])
                logger.info(
                    f"Feedback created: id={feedback_id}, type={feedback.target_type}, "
                    f"target={feedback.target_id}, rating={feedback.rating}"
                )
                
                return FeedbackResponse(
                    success=True,
                    feedback_id=feedback_id,
                    message="Feedback submitted successfully"
                )
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Failed to create feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")


@router.get("", response_model=FeedbackListResponse, dependencies=[Depends(require_tuning_auth)])
@router.get("/", response_model=FeedbackListResponse, dependencies=[Depends(require_tuning_auth)])
async def list_feedback(
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    rating: Optional[int] = Query(None, description="Filter by rating"),
    model_name: Optional[str] = Query(None, description="Filter by model name (in metadata)"),
    rag_profile_id: Optional[str] = Query(None, description="Filter by RAG profile ID"),
    custom_instruction_id: Optional[str] = Query(None, description="Filter by custom instruction ID"),
    from_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
):
    """
    List feedback events with filtering and pagination.
    
    Protected: requires tuning_auth cookie (admin only).
    
    For 'answer' type feedback, includes snippets of input/output text from ai_requests.
    """
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Build WHERE clause
                conditions = []
                params = []
                
                if target_type:
                    conditions.append("f.target_type = %s")
                    params.append(target_type)
                
                if rating is not None:
                    conditions.append("f.rating = %s")
                    params.append(rating)
                
                if model_name:
                    conditions.append("f.metadata->>'model_name' = %s")
                    params.append(model_name)
                
                if rag_profile_id:
                    conditions.append("f.metadata->>'rag_profile_id' = %s")
                    params.append(rag_profile_id)
                
                if custom_instruction_id:
                    conditions.append("f.metadata->>'custom_instruction_id' = %s")
                    params.append(custom_instruction_id)
                
                if from_date:
                    conditions.append("DATE(f.created_at) >= %s")
                    params.append(from_date)
                
                if to_date:
                    conditions.append("DATE(f.created_at) <= %s")
                    params.append(to_date)
                
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                
                # Count total
                cur.execute(f"""
                    SELECT COUNT(*) as total
                    FROM feedback_events f
                    WHERE {where_clause}
                """, params)
                total = cur.fetchone()['total']
                
                # Fetch page with LEFT JOIN to ai_requests for answer feedback
                offset = (page - 1) * page_size
                cur.execute(f"""
                    SELECT 
                        f.id,
                        f.target_type,
                        f.target_id,
                        f.rating,
                        f.tags,
                        f.comment,
                        f.metadata,
                        f.created_at,
                        CASE 
                            WHEN f.target_type = 'answer' AND ar.id IS NOT NULL 
                            THEN LEFT(ar.input_text, 200)
                            ELSE NULL 
                        END as input_text_snippet,
                        CASE 
                            WHEN f.target_type = 'answer' AND ar.id IS NOT NULL 
                            THEN LEFT(ar.output_text, 200)
                            ELSE NULL 
                        END as output_text_snippet,
                        ar.model_name
                    FROM feedback_events f
                    LEFT JOIN ai_requests ar ON f.target_type = 'answer' AND f.target_id::uuid = ar.id
                    WHERE {where_clause}
                    ORDER BY f.created_at DESC
                    LIMIT %s OFFSET %s
                """, params + [page_size, offset])
                
                rows = cur.fetchall()
                
                items = []
                for row in rows:
                    items.append(FeedbackItem(
                        id=str(row['id']),
                        target_type=row['target_type'],
                        target_id=row['target_id'],
                        rating=row['rating'],
                        tags=row['tags'] if row['tags'] else None,
                        comment=row['comment'],
                        metadata=row['metadata'] if row['metadata'] else None,
                        created_at=row['created_at'],
                        input_text_snippet=row['input_text_snippet'],
                        output_text_snippet=row['output_text_snippet'],
                        model_name=row['model_name'],
                    ))
                
                return FeedbackListResponse(
                    items=items,
                    total=total,
                    page=page,
                    page_size=page_size,
                )
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Failed to list feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch feedback: {str(e)}")


@router.get("/stats", dependencies=[Depends(require_tuning_auth)])
async def get_feedback_stats(
    from_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
):
    """
    Get aggregated feedback statistics.
    
    Protected: requires tuning_auth cookie (admin only).
    """
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Build date filter
                date_conditions = []
                params = []
                
                if from_date:
                    date_conditions.append("DATE(created_at) >= %s")
                    params.append(from_date)
                
                if to_date:
                    date_conditions.append("DATE(created_at) <= %s")
                    params.append(to_date)
                
                date_filter = " AND ".join(date_conditions) if date_conditions else "1=1"
                
                # Get stats by target_type
                cur.execute(f"""
                    SELECT 
                        target_type,
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE rating = 1) as positive,
                        COUNT(*) FILTER (WHERE rating = -1) as negative,
                        COUNT(*) FILTER (WHERE rating = 0 OR rating = -2) as neutral_or_broken,
                        COUNT(*) FILTER (WHERE comment IS NOT NULL AND comment != '') as with_comments
                    FROM feedback_events
                    WHERE {date_filter}
                    GROUP BY target_type
                """, params)
                
                by_type = {row['target_type']: dict(row) for row in cur.fetchall()}
                
                # Get overall totals
                cur.execute(f"""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE rating = 1) as positive,
                        COUNT(*) FILTER (WHERE rating = -1) as negative
                    FROM feedback_events
                    WHERE {date_filter}
                """, params)
                
                totals = cur.fetchone()
                
                return {
                    "by_type": by_type,
                    "totals": dict(totals),
                    "from_date": from_date,
                    "to_date": to_date,
                }
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Failed to get feedback stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")
