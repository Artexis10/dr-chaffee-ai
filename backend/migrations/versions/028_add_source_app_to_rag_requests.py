"""Add source_app column to rag_requests for per-source metrics breakdown

Revision ID: 028
Revises: 027
Create Date: 2025-12-06

This migration adds:
- source_app column to rag_requests table to track which application/client
  made the request (e.g., 'main_app', 'tuning_dashboard', 'discord_bot')

This enables per-source-app breakdowns in daily summaries alongside the
existing per-request-type breakdowns.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '028'
down_revision = '027'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add source_app column to rag_requests."""
    
    # Add source_app column with default 'unknown' for historical rows
    op.add_column(
        'rag_requests',
        sa.Column('source_app', sa.String(50), nullable=True, server_default='unknown')
    )
    
    # Create index for efficient GROUP BY queries
    op.create_index(
        'idx_rag_requests_source_app',
        'rag_requests',
        ['source_app'],
    )
    
    print("[OK] Added source_app column to rag_requests table")


def downgrade() -> None:
    """Remove source_app column from rag_requests."""
    op.drop_index('idx_rag_requests_source_app', table_name='rag_requests')
    op.drop_column('rag_requests', 'source_app')
    
    print("[OK] Removed source_app column from rag_requests table")
