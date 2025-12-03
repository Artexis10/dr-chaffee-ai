"""Create ai_requests and feedback_events tables for unified feedback system

Revision ID: 025
Revises: 024
Create Date: 2025-12-03

This migration creates:
1. ai_requests - Logs every AI call (Q&A, summarizer) with full context
2. feedback_events - Unified feedback table for answers, tuning, and global feedback
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ai_requests and feedback_events tables."""
    
    # 1. Create ai_requests table - logs every AI call
    op.create_table(
        'ai_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        
        # User identification (nullable for anonymous users)
        sa.Column('user_id', sa.Integer(), nullable=True, index=True),
        
        # Request type: 'qa', 'summariser', 'search_summariser', 'tuning_test', etc.
        sa.Column('request_type', sa.String(50), nullable=False, index=True),
        
        # Input/output content
        sa.Column('input_text', sa.Text(), nullable=False),
        sa.Column('output_text', sa.Text(), nullable=True),  # Nullable in case of errors
        
        # Model configuration
        sa.Column('model_name', sa.String(100), nullable=False),
        
        # Profile references (nullable - may not always apply)
        sa.Column('rag_profile_id', sa.String(50), nullable=True),
        sa.Column('custom_instruction_id', sa.String(50), nullable=True),
        sa.Column('search_config_id', sa.String(50), nullable=True),
        
        # Request/session correlation
        sa.Column('request_id', sa.String(50), nullable=True, index=True),
        sa.Column('session_id', sa.String(50), nullable=True, index=True),
        
        # Performance metrics
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        
        # Status
        sa.Column('success', sa.Boolean(), default=True, nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        
        # Flexible metadata (raw messages, extra context, etc.)
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default='{}'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Index for date-based queries
    op.create_index(
        'idx_ai_requests_created_date',
        'ai_requests',
        ['created_at'],
    )
    
    # 2. Create feedback_events table - unified feedback for all contexts
    op.create_table(
        'feedback_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        
        # User identification (nullable for anonymous users)
        sa.Column('user_id', sa.Integer(), nullable=True, index=True),
        
        # Target type: 'answer', 'tuning_internal', 'global'
        sa.Column('target_type', sa.String(30), nullable=False, index=True),
        
        # Target ID (ai_request_id for answers, profile/config ID for tuning, null for global)
        sa.Column('target_id', sa.String(100), nullable=True, index=True),
        
        # Rating: 1 = thumbs up, -1 = thumbs down, 0 = neutral/broken
        sa.Column('rating', sa.SmallInteger(), nullable=True),
        
        # Tags for categorization (e.g., ['wrong_facts', 'missed_context'])
        sa.Column('tags', postgresql.JSONB(), nullable=True, server_default='[]'),
        
        # Freeform comment
        sa.Column('comment', sa.Text(), nullable=True),
        
        # Metadata snapshot at time of feedback
        # For answers: model_name, rag_profile_id, custom_instruction_id, search_config_id
        # For tuning: config details
        # For global: route, device info, etc.
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default='{}'),
        
        # Session correlation
        sa.Column('session_id', sa.String(50), nullable=True, index=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Index for filtering by target_type and rating
    op.create_index(
        'idx_feedback_events_type_rating',
        'feedback_events',
        ['target_type', 'rating'],
    )
    
    # Index for date-based queries
    op.create_index(
        'idx_feedback_events_created_date',
        'feedback_events',
        ['created_at'],
    )
    
    print("[OK] Created ai_requests table for AI call logging")
    print("[OK] Created feedback_events table for unified feedback")


def downgrade() -> None:
    """Drop feedback_events and ai_requests tables."""
    op.drop_index('idx_feedback_events_created_date', table_name='feedback_events')
    op.drop_index('idx_feedback_events_type_rating', table_name='feedback_events')
    op.drop_table('feedback_events')
    
    op.drop_index('idx_ai_requests_created_date', table_name='ai_requests')
    op.drop_table('ai_requests')
    
    print("[OK] Dropped feedback_events and ai_requests tables")
