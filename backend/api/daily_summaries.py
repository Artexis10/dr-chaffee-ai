"""
Daily Summaries Module

Generates LLM-powered daily usage digests for admin review.
Aggregates RAG requests and produces actionable insights.
"""

import os
import json
import logging
from datetime import date
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


@dataclass
class FeedbackSummary:
    """Aggregated feedback statistics for a single day."""
    total: int
    positive: int
    negative: int
    by_model: Dict[str, Dict[str, int]]  # model_name -> {positive, negative}
    top_tags: List[Dict[str, Any]]  # [{tag, count}, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "positive": self.positive,
            "negative": self.negative,
            "by_model": self.by_model,
            "top_tags": self.top_tags,
        }


@dataclass
class DailyStats:
    """Aggregated statistics for a single day."""
    summary_date: date
    total_queries: int
    total_answers: int
    total_searches: int
    distinct_sessions: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    success_count: int
    error_count: int
    top_queries: List[str]
    error_messages: List[str]
    feedback_summary: Optional[FeedbackSummary] = None

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.error_count
        return self.success_count / total if total > 0 else 1.0

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "queries": self.total_queries,
            "answers": self.total_answers,
            "searches": self.total_searches,
            "distinct_sessions": self.distinct_sessions,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "avg_tokens": (self.total_input_tokens + self.total_output_tokens) // max(self.total_queries, 1),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "success_rate": round(self.success_rate, 3),
            "success_count": self.success_count,
            "error_count": self.error_count,
        }
        if self.feedback_summary:
            result["feedback_summary"] = self.feedback_summary.to_dict()
        return result


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        os.getenv('DATABASE_URL'),
        cursor_factory=RealDictCursor
    )


def aggregate_feedback_stats(summary_date: date) -> Optional[FeedbackSummary]:
    """
    Aggregate feedback statistics for a given date.
    
    Args:
        summary_date: The date to aggregate feedback for
        
    Returns:
        FeedbackSummary object or None if no feedback exists
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get overall counts
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE rating > 0) as positive,
                    COUNT(*) FILTER (WHERE rating < 0) as negative
                FROM feedback_events
                WHERE DATE(created_at) = %s
            """, [summary_date])
            
            totals = cur.fetchone()
            if not totals or totals['total'] == 0:
                return None
            
            # Get per-model breakdown (from metadata)
            cur.execute("""
                SELECT
                    metadata->>'model_name' as model_name,
                    COUNT(*) FILTER (WHERE rating > 0) as positive,
                    COUNT(*) FILTER (WHERE rating < 0) as negative
                FROM feedback_events
                WHERE DATE(created_at) = %s
                AND metadata->>'model_name' IS NOT NULL
                GROUP BY metadata->>'model_name'
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """, [summary_date])
            
            by_model = {}
            for row in cur.fetchall():
                if row['model_name']:
                    by_model[row['model_name']] = {
                        'positive': row['positive'] or 0,
                        'negative': row['negative'] or 0,
                    }
            
            # Get top tags
            cur.execute("""
                SELECT tag, COUNT(*) as count
                FROM feedback_events, jsonb_array_elements_text(tags) as tag
                WHERE DATE(created_at) = %s
                AND tags IS NOT NULL
                GROUP BY tag
                ORDER BY count DESC
                LIMIT 10
            """, [summary_date])
            
            top_tags = [{'tag': row['tag'], 'count': row['count']} for row in cur.fetchall()]
            
            return FeedbackSummary(
                total=totals['total'] or 0,
                positive=totals['positive'] or 0,
                negative=totals['negative'] or 0,
                by_model=by_model,
                top_tags=top_tags,
            )
    except Exception as e:
        logger.warning(f"Failed to aggregate feedback stats: {e}")
        return None
    finally:
        conn.close()


def aggregate_daily_stats(summary_date: date, tenant_id: Optional[str] = None) -> DailyStats:
    """
    Aggregate RAG request statistics for a given date.

    Args:
        summary_date: The date to aggregate stats for
        tenant_id: Optional tenant ID for multi-tenant filtering

    Returns:
        DailyStats object with aggregated metrics
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Build tenant filter
            tenant_filter = "AND tenant_id = %s" if tenant_id else "AND tenant_id IS NULL"
            params = [summary_date, tenant_id] if tenant_id else [summary_date]

            # Aggregate main metrics
            cur.execute(f"""
                SELECT
                    COUNT(*) as total_queries,
                    COUNT(*) FILTER (WHERE request_type = 'answer') as total_answers,
                    COUNT(*) FILTER (WHERE request_type = 'search') as total_searches,
                    COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL) as distinct_sessions,
                    COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                    COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                    COALESCE(SUM(cost_usd), 0) as total_cost_usd,
                    COALESCE(AVG(latency_ms), 0) as avg_latency_ms,
                    COUNT(*) FILTER (WHERE success = true) as success_count,
                    COUNT(*) FILTER (WHERE success = false) as error_count
                FROM rag_requests
                WHERE DATE(created_at) = %s
                {tenant_filter}
            """, params)

            row = cur.fetchone()

            # Get top queries (most common)
            cur.execute(f"""
                SELECT query_text, COUNT(*) as cnt
                FROM rag_requests
                WHERE DATE(created_at) = %s
                {tenant_filter}
                GROUP BY query_text
                ORDER BY cnt DESC
                LIMIT 10
            """, params)
            top_queries = [r['query_text'][:200] for r in cur.fetchall()]

            # Get error messages
            cur.execute(f"""
                SELECT DISTINCT error_message
                FROM rag_requests
                WHERE DATE(created_at) = %s
                {tenant_filter}
                AND success = false
                AND error_message IS NOT NULL
                LIMIT 10
            """, params)
            error_messages = [r['error_message'] for r in cur.fetchall()]

            # Aggregate feedback stats for the same date
            feedback_summary = aggregate_feedback_stats(summary_date)
            
            return DailyStats(
                summary_date=summary_date,
                total_queries=row['total_queries'] or 0,
                total_answers=row['total_answers'] or 0,
                total_searches=row['total_searches'] or 0,
                distinct_sessions=row['distinct_sessions'] or 0,
                total_input_tokens=row['total_input_tokens'] or 0,
                total_output_tokens=row['total_output_tokens'] or 0,
                total_cost_usd=float(row['total_cost_usd'] or 0),
                avg_latency_ms=float(row['avg_latency_ms'] or 0),
                success_count=row['success_count'] or 0,
                error_count=row['error_count'] or 0,
                top_queries=top_queries,
                error_messages=error_messages,
                feedback_summary=feedback_summary,
            )
    finally:
        conn.close()


def build_summary_prompt(stats: DailyStats) -> str:
    """
    Build the LLM prompt for generating the daily summary.

    Args:
        stats: Aggregated daily statistics

    Returns:
        Formatted prompt string
    """
    top_queries_str = "\n".join(f"  - {q}" for q in stats.top_queries[:10]) if stats.top_queries else "  (no queries recorded)"
    errors_str = "\n".join(f"  - {e}" for e in stats.error_messages[:5]) if stats.error_messages else "  (no errors)"
    
    # Build feedback section
    feedback_str = "  (no feedback recorded)"
    if stats.feedback_summary:
        fs = stats.feedback_summary
        feedback_str = f"  - Total: {fs.total} (👍 {fs.positive} / 👎 {fs.negative})"
        if fs.by_model:
            for model, counts in fs.by_model.items():
                feedback_str += f"\n  - {model}: 👍 {counts['positive']} / 👎 {counts['negative']}"
        if fs.top_tags:
            tags_str = ", ".join(f"{t['tag']} ({t['count']})" for t in fs.top_tags[:5])
            feedback_str += f"\n  - Top issues: {tags_str}"

    return f"""You are summarizing the last 24 hours of user interactions with Dr. Chaffee AI, a medical/nutrition RAG system.

## Usage Statistics for {stats.summary_date.isoformat()}

- **Total Queries**: {stats.total_queries}
- **Answer Requests**: {stats.total_answers}
- **Search Requests**: {stats.total_searches}
- **Distinct Sessions**: {stats.distinct_sessions}
- **Total Tokens Used**: {stats.total_input_tokens + stats.total_output_tokens:,}
- **Total Cost**: ${stats.total_cost_usd:.4f}
- **Average Latency**: {stats.avg_latency_ms:.0f}ms
- **Success Rate**: {stats.success_rate * 100:.1f}%
- **Errors**: {stats.error_count}

## Top Queries
{top_queries_str}

## User Feedback
{feedback_str}

## Errors (if any)
{errors_str}

---

Based on this data, produce a concise daily digest with the following sections:

1. **Top Themes**: What topics did users ask about most? Identify 3-5 key themes.

2. **What Worked Well**: Where did the RAG answers seem strong? (high success rate, relevant queries, positive feedback)

3. **Areas for Improvement**: Where might answers be weak or confusing? Consider negative feedback tags and patterns.

4. **Error Analysis**: If there were errors, what patterns do you see? Any recurring failure modes?

5. **Feedback Insights**: What does user feedback tell us? Any patterns in negative ratings or common issues?

6. **Recommendations**: 2-3 concrete suggestions for improving RAG profiles, search config, or custom instructions.

Keep the summary concise but specific (400-600 words). Focus on actionable insights.
If there were no queries, simply note that it was a quiet day with no user activity."""


def generate_summary_text(stats: DailyStats) -> str:
    """
    Generate the daily summary text using OpenAI.

    Args:
        stats: Aggregated daily statistics

    Returns:
        Generated summary text (markdown)
    """
    from openai import OpenAI

    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    client = OpenAI(api_key=openai_api_key)

    # Use a cost-effective model for summaries
    model = os.getenv('SUMMARIZER_MODEL', 'gpt-4o-mini')

    prompt = build_summary_prompt(stats)

    logger.info(f"Generating daily summary for {stats.summary_date} with {model}")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an analytics assistant for Dr. Chaffee AI. Produce clear, actionable daily summaries."
            },
            {"role": "user", "content": prompt}
        ],
        max_tokens=1500,
        temperature=0.3,
    )

    summary_text = response.choices[0].message.content

    # Log token usage
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    # gpt-4o-mini pricing: $0.15/1M input, $0.60/1M output
    cost = (input_tokens * 0.00015 + output_tokens * 0.0006) / 1000

    logger.info(
        f"DailySummaryGenerated: date={stats.summary_date} model={model} "
        f"in_tokens={input_tokens} out_tokens={output_tokens} cost=${cost:.4f}"
    )

    return summary_text


def generate_daily_summary(
    summary_date: date,
    tenant_id: Optional[str] = None,
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """
    Generate or retrieve a daily summary for the given date.

    Args:
        summary_date: The date to generate summary for
        tenant_id: Optional tenant ID for multi-tenant support
        force_regenerate: If True, regenerate even if summary exists

    Returns:
        Dictionary with summary data
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Check if summary already exists
            tenant_filter = "AND tenant_id = %s" if tenant_id else "AND tenant_id IS NULL"
            params = [summary_date, tenant_id] if tenant_id else [summary_date]

            if not force_regenerate:
                cur.execute(f"""
                    SELECT id, summary_date, summary_text, summary_html, stats_json, created_at, updated_at
                    FROM daily_summaries
                    WHERE summary_date = %s
                    {tenant_filter}
                """, params)
                existing = cur.fetchone()

                if existing:
                    logger.info(f"Returning existing summary for {summary_date}")
                    return dict(existing)

            # Aggregate stats
            stats = aggregate_daily_stats(summary_date, tenant_id)

            # Generate summary text
            summary_text = generate_summary_text(stats)
            stats_json = json.dumps(stats.to_dict())

            # Upsert summary
            cur.execute("""
                INSERT INTO daily_summaries (summary_date, summary_text, stats_json, tenant_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (summary_date, tenant_id)
                DO UPDATE SET
                    summary_text = EXCLUDED.summary_text,
                    stats_json = EXCLUDED.stats_json,
                    updated_at = NOW()
                RETURNING id, summary_date, summary_text, summary_html, stats_json, created_at, updated_at
            """, [summary_date, summary_text, stats_json, tenant_id])

            result = cur.fetchone()
            conn.commit()

            logger.info(f"Daily summary saved for {summary_date}")
            return dict(result)

    finally:
        conn.close()


def list_summaries(
    limit: int = 30,
    tenant_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List recent daily summaries.

    Args:
        limit: Maximum number of summaries to return
        tenant_id: Optional tenant ID for multi-tenant filtering

    Returns:
        List of summary metadata (without full text)
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            tenant_filter = "WHERE tenant_id = %s" if tenant_id else "WHERE tenant_id IS NULL"
            params = [tenant_id, limit] if tenant_id else [limit]

            cur.execute(f"""
                SELECT id, summary_date, stats_json, created_at, updated_at
                FROM daily_summaries
                {tenant_filter}
                ORDER BY summary_date DESC
                LIMIT %s
            """, params if tenant_id else [limit])

            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_summary_by_date(
    summary_date: date,
    tenant_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get a specific daily summary by date.

    Args:
        summary_date: The date to retrieve
        tenant_id: Optional tenant ID for multi-tenant filtering

    Returns:
        Summary data or None if not found
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            tenant_filter = "AND tenant_id = %s" if tenant_id else "AND tenant_id IS NULL"
            params = [summary_date, tenant_id] if tenant_id else [summary_date]

            cur.execute(f"""
                SELECT id, summary_date, summary_text, summary_html, stats_json, created_at, updated_at
                FROM daily_summaries
                WHERE summary_date = %s
                {tenant_filter}
            """, params)

            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def log_rag_request(
    request_type: str,
    query_text: str,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    style: Optional[str] = None,
    results_count: Optional[int] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cost_usd: Optional[float] = None,
    latency_ms: Optional[float] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    rag_profile_id: Optional[str] = None,
    rag_profile_name: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> None:
    """
    Log a RAG request for daily aggregation.

    This is a fire-and-forget operation - errors are logged but not raised.

    Args:
        request_type: 'search' or 'answer'
        query_text: The user's query
        request_id: Request ID for correlation
        session_id: Session ID for correlation
        style: Answer style (concise, detailed, etc.)
        results_count: Number of results returned
        input_tokens: LLM input tokens
        output_tokens: LLM output tokens
        cost_usd: Estimated cost in USD
        latency_ms: Request latency in milliseconds
        success: Whether the request succeeded
        error_message: Error message if failed
        rag_profile_id: RAG profile UUID string
        rag_profile_name: RAG profile name used
        tenant_id: Tenant ID for multi-tenant support
    """
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Check if rag_requests table exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'rag_requests'
                    )
                """)
                table_exists = cur.fetchone()['exists']
                
                if not table_exists:
                    logger.debug("rag_requests table does not exist, skipping log")
                    return
                
                cur.execute("""
                    INSERT INTO rag_requests (
                        request_type, query_text, request_id, session_id, style,
                        results_count, input_tokens, output_tokens, cost_usd, latency_ms,
                        success, error_message, rag_profile_id, rag_profile_name, tenant_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    request_type, query_text[:2000], request_id, session_id, style,
                    results_count, input_tokens, output_tokens, cost_usd, latency_ms,
                    success, error_message, rag_profile_id, rag_profile_name, tenant_id
                ])
                conn.commit()
                logger.debug(f"Logged RAG request: type={request_type}, profile={rag_profile_name}")
        finally:
            conn.close()
    except Exception as e:
        # Log but don't raise - this is non-critical
        # Include more context for debugging
        logger.warning(
            f"Failed to log RAG request: {e} "
            f"(type={request_type}, profile_id={rag_profile_id}, profile_name={rag_profile_name})"
        )
