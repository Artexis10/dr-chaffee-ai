"""
Admin Daily Summaries API

Endpoints for viewing and generating daily usage summaries.
Protected by tuning auth (same as other admin endpoints).
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from ..tuning import require_tuning_auth
from ..daily_summaries import (
    generate_daily_summary,
    list_summaries,
    get_summary_by_date,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/daily-summaries",
    tags=["admin", "daily-summaries"],
    dependencies=[Depends(require_tuning_auth)],
)


# =============================================================================
# Pydantic Models
# =============================================================================

class SummaryStats(BaseModel):
    """Statistics from a daily summary."""
    queries: int = 0
    answers: int = 0
    searches: int = 0
    distinct_sessions: int = 0
    total_tokens: int = 0
    avg_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    success_count: int = 0
    error_count: int = 0


class SummaryListItem(BaseModel):
    """Summary metadata for list view."""
    id: str
    summary_date: date
    stats: SummaryStats
    created_at: datetime
    updated_at: Optional[datetime] = None


class SummaryDetail(BaseModel):
    """Full summary with text content."""
    id: str
    summary_date: date
    summary_text: str
    summary_html: Optional[str] = None
    stats: SummaryStats
    created_at: datetime
    updated_at: Optional[datetime] = None


class GenerateRequest(BaseModel):
    """Request to generate a daily summary."""
    summary_date: Optional[str] = Field(
        None,
        description="Date in YYYY-MM-DD format. Defaults to yesterday if omitted."
    )
    force_regenerate: bool = Field(
        False,
        description="If true, regenerate even if summary exists."
    )


# =============================================================================
# Helper Functions
# =============================================================================

def parse_stats(stats_json: Any) -> SummaryStats:
    """Parse stats_json into SummaryStats model."""
    if isinstance(stats_json, str):
        import json
        stats_json = json.loads(stats_json)
    return SummaryStats(**stats_json) if stats_json else SummaryStats()


def format_summary_item(row: dict) -> SummaryListItem:
    """Format a database row into a SummaryListItem."""
    return SummaryListItem(
        id=str(row['id']),
        summary_date=row['summary_date'],
        stats=parse_stats(row.get('stats_json', {})),
        created_at=row['created_at'],
        updated_at=row.get('updated_at'),
    )


def format_summary_detail(row: dict) -> SummaryDetail:
    """Format a database row into a SummaryDetail."""
    return SummaryDetail(
        id=str(row['id']),
        summary_date=row['summary_date'],
        summary_text=row['summary_text'],
        summary_html=row.get('summary_html'),
        stats=parse_stats(row.get('stats_json', {})),
        created_at=row['created_at'],
        updated_at=row.get('updated_at'),
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=List[SummaryListItem])
async def list_daily_summaries(
    limit: int = Query(30, ge=1, le=100, description="Number of summaries to return"),
):
    """
    List recent daily summaries.

    Returns summary metadata (date, stats) without the full text content.
    Use GET /{summary_date} to retrieve full content.
    """
    try:
        rows = list_summaries(limit=limit)
        return [format_summary_item(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to list summaries: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list summaries: {str(e)}")


@router.get("/{summary_date}", response_model=SummaryDetail)
async def get_daily_summary(summary_date: str):
    """
    Get a specific daily summary by date.

    Args:
        summary_date: Date in YYYY-MM-DD format

    Returns:
        Full summary including text content and stats.
    """
    try:
        parsed_date = date.fromisoformat(summary_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    try:
        row = get_summary_by_date(parsed_date)
        if not row:
            raise HTTPException(status_code=404, detail=f"No summary found for {summary_date}")
        return format_summary_detail(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get summary for {summary_date}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")


@router.post("/generate", response_model=SummaryDetail)
async def generate_summary(request: GenerateRequest):
    """
    Generate a daily summary for a specific date.

    If no date is provided, generates for yesterday.
    If a summary already exists and force_regenerate is false, returns the existing summary.

    Args:
        request: GenerateRequest with optional date and force_regenerate flag

    Returns:
        The generated or existing summary.
    """
    # Parse date (default to yesterday)
    if request.summary_date:
        try:
            target_date = date.fromisoformat(request.summary_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        target_date = date.today() - timedelta(days=1)

    # Don't allow future dates
    if target_date > date.today():
        raise HTTPException(status_code=400, detail="Cannot generate summary for future dates.")

    try:
        logger.info(f"Generating daily summary for {target_date} (force={request.force_regenerate})")
        row = generate_daily_summary(
            summary_date=target_date,
            force_regenerate=request.force_regenerate,
        )
        return format_summary_detail(row)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate summary for {target_date}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")
