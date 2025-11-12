"""Fix duplicate segments and ensure speaker labels

Revision ID: 002
Revises: 001
Create Date: 2025-10-01 13:11:00

This migration:
1. Removes duplicate segments (same video_id + text)
2. Fixes NULL speaker labels (defaults to 'Chaffee')
3. Adds unique constraint to prevent future duplicates

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Remove duplicate segments (keep first occurrence)
    op.execute("""
        CREATE TEMP TABLE segment_ranks AS
        SELECT 
            id,
            video_id,
            text,
            ROW_NUMBER() OVER (PARTITION BY video_id, text ORDER BY id) as row_num
        FROM segments
    """)
    
    op.execute("""
        DELETE FROM segments
        WHERE id IN (
            SELECT id FROM segment_ranks WHERE row_num > 1
        )
    """)
    
    op.execute("DROP TABLE segment_ranks")
    
    # Step 2: Fix NULL speaker labels (default to 'Chaffee' for Dr. Chaffee content)
    op.execute("""
        UPDATE segments
        SET speaker_label = 'Chaffee'
        WHERE speaker_label IS NULL
    """)
    
    # Step 3: Unique constraint already added in migration 001
    # (video_id, start_sec, end_sec, text) - more precise than just (video_id, text)
    # Skipping duplicate constraint creation


def downgrade() -> None:
    # No constraint to remove (handled in migration 001)
    # Note: We cannot restore deleted duplicates or revert speaker label changes
    # This is acceptable as the upgrade fixes data quality issues
    pass
