"""Add missing segment quality columns

Revision ID: 008
Revises: 004
Create Date: 2025-10-16 21:32:00

Add back re_asr, is_overlap, needs_refinement columns that are used by ingestion pipeline
Also rename speaker_confidence to speaker_conf for consistency
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing columns"""
    
    # Rename speaker_confidence to speaker_conf
    op.execute("ALTER TABLE segments RENAME COLUMN speaker_confidence TO speaker_conf")
    
    # Add missing quality control columns
    op.add_column('segments', sa.Column('re_asr', sa.Boolean(), nullable=True))
    op.add_column('segments', sa.Column('is_overlap', sa.Boolean(), nullable=True))
    op.add_column('segments', sa.Column('needs_refinement', sa.Boolean(), nullable=True))
    
    print("✅ Added missing segment quality columns")


def downgrade() -> None:
    """Remove columns"""
    op.drop_column('segments', 'needs_refinement')
    op.drop_column('segments', 'is_overlap')
    op.drop_column('segments', 're_asr')
    op.execute("ALTER TABLE segments RENAME COLUMN speaker_conf TO speaker_confidence")
