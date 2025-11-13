"""Remove duplicate video_id from segments, keep only source_id FK

Revision ID: 011
Revises: 010
Create Date: 2025-11-13 02:00:00

The segments table had video_id (YouTube ID) which duplicated sources.source_id.
Now that we have source_id FK to sources.id, we can remove video_id and JOIN when needed.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove the unique constraint that includes video_id
    op.drop_constraint('segments_video_id_start_sec_end_sec_text_key', 'segments', type_='unique')
    
    # Remove the video_id column
    op.drop_column('segments', 'video_id')
    
    # Create new unique constraint on (source_id, start_sec, end_sec, text)
    op.create_unique_constraint(
        'segments_source_id_start_sec_end_sec_text_key',
        'segments',
        ['source_id', 'start_sec', 'end_sec', 'text']
    )


def downgrade() -> None:
    # Remove the new unique constraint
    op.drop_constraint('segments_source_id_start_sec_end_sec_text_key', 'segments', type_='unique')
    
    # Re-add video_id column
    op.add_column('segments', sa.Column('video_id', sa.String(255), nullable=True))
    
    # Populate video_id from sources table
    op.execute("""
        UPDATE segments s
        SET video_id = src.source_id
        FROM sources src
        WHERE s.source_id = src.id
    """)
    
    # Make video_id NOT NULL
    op.alter_column('segments', 'video_id', nullable=False)
    
    # Re-create the original unique constraint
    op.create_unique_constraint(
        'segments_video_id_start_sec_end_sec_text_key',
        'segments',
        ['video_id', 'start_sec', 'end_sec', 'text']
    )
