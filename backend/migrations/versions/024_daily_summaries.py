"""Create daily_summaries and rag_requests tables

Revision ID: 024
Revises: 023
Create Date: 2025-12-03

This migration creates:
1. daily_summaries - Stores LLM-generated daily usage digests
2. rag_requests - Lightweight request log for aggregation (optional, can be disabled)

The daily_summaries table is designed for multi-tenant use:
- tenant_id column is nullable for future multi-tenant support
- summary_date is unique per tenant (or globally if tenant_id is null)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create daily_summaries and rag_requests tables."""
    
    # 1. Create rag_requests table for lightweight request logging
    # This enables aggregation for daily summaries
    op.create_table(
        'rag_requests',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        
        # Request identification
        sa.Column('request_id', sa.String(32), nullable=True, index=True),
        sa.Column('session_id', sa.String(32), nullable=True, index=True),
        
        # Request details
        sa.Column('request_type', sa.String(20), nullable=False),  # 'search' or 'answer'
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('style', sa.String(20), nullable=True),  # 'concise', 'detailed', etc.
        
        # Response metrics
        sa.Column('results_count', sa.Integer(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        
        # Status
        sa.Column('success', sa.Boolean(), default=True, nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        
        # RAG profile used (if any)
        sa.Column('rag_profile_id', sa.Integer(), nullable=True),
        sa.Column('rag_profile_name', sa.String(100), nullable=True),
        
        # Multi-tenant support (nullable for now)
        sa.Column('tenant_id', sa.String(50), nullable=True, index=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create index for daily aggregation queries
    op.create_index(
        'idx_rag_requests_created_date',
        'rag_requests',
        [sa.text("DATE(created_at)")],
    )
    
    # 2. Create daily_summaries table
    op.create_table(
        'daily_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        
        # Summary date (unique per tenant or globally)
        sa.Column('summary_date', sa.Date(), nullable=False),
        
        # Summary content
        sa.Column('summary_text', sa.Text(), nullable=False),  # Markdown/plaintext
        sa.Column('summary_html', sa.Text(), nullable=True),   # Optional HTML rendering
        
        # Aggregated statistics
        sa.Column('stats_json', postgresql.JSONB(), nullable=False, server_default='{}'),
        # Example stats_json: {
        #   "queries": 42,
        #   "answers": 40,
        #   "searches": 15,
        #   "total_tokens": 50000,
        #   "avg_tokens": 1234,
        #   "total_cost_usd": 0.50,
        #   "distinct_sessions": 10,
        #   "success_rate": 0.95,
        #   "avg_latency_ms": 1500
        # }
        
        # Multi-tenant support (nullable for now)
        sa.Column('tenant_id', sa.String(50), nullable=True, index=True),
        
        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create unique constraint on (summary_date, tenant_id)
    # For single-tenant (tenant_id IS NULL), this ensures one summary per date
    op.create_index(
        'idx_daily_summaries_date_tenant',
        'daily_summaries',
        ['summary_date', 'tenant_id'],
        unique=True,
    )
    
    # Create index for recent summaries query
    op.create_index(
        'idx_daily_summaries_created',
        'daily_summaries',
        ['created_at'],
    )
    
    print("[OK] Created rag_requests table for request logging")
    print("[OK] Created daily_summaries table for usage digests")


def downgrade() -> None:
    """Drop daily_summaries and rag_requests tables."""
    op.drop_index('idx_daily_summaries_created', table_name='daily_summaries')
    op.drop_index('idx_daily_summaries_date_tenant', table_name='daily_summaries')
    op.drop_table('daily_summaries')
    
    op.drop_index('idx_rag_requests_created_date', table_name='rag_requests')
    op.drop_table('rag_requests')
    
    print("[OK] Dropped daily_summaries and rag_requests tables")
