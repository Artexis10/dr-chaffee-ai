"""Add cascade delete from sources to segments

Revision ID: 010
Revises: 009
Create Date: 2025-11-13 01:30:00

When a source (video) is deleted, all associated segments should be deleted automatically.
This migration adds a proper foreign key constraint with ON DELETE CASCADE.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add source_id column to segments (references sources.id primary key)
    op.add_column('segments', sa.Column('source_id', sa.Integer(), nullable=True))
    
    # Populate source_id from existing video_id references
    # This matches segments to their source records
    op.execute("""
        UPDATE segments s
        SET source_id = src.id
        FROM sources src
        WHERE s.video_id = src.source_id
    """)
    
    # Make source_id NOT NULL after populating
    op.alter_column('segments', 'source_id', nullable=False)
    
    # Add foreign key constraint with cascade delete
    op.create_foreign_key(
        'fk_segments_source',
        'segments',
        'sources',
        ['source_id'],
        ['id'],
        ondelete='CASCADE',
        onupdate='CASCADE'
    )
    
    # Create index on the foreign key for better query performance
    op.create_index('idx_segments_source_fk', 'segments', ['source_id'])


def downgrade() -> None:
    # Remove the foreign key constraint
    op.drop_constraint('fk_segments_source', 'segments', type_='foreignkey')
    
    # Remove the index
    op.drop_index('idx_segments_source_fk', table_name='segments')
    
    # Remove the source_id column
    op.drop_column('segments', 'source_id')
