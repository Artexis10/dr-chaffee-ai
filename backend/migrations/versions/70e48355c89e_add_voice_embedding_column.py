"""add_voice_embedding_column

Adds voice_embedding column to segments table for storing 192-dim SpeechBrain ECAPA
voice embeddings used for speaker identification. This is separate from the existing
embedding column which stores 1536-dim text embeddings for semantic search.

Revision ID: 70e48355c89e
Revises: 003
Create Date: 2025-10-06 21:08:52.218738

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '70e48355c89e'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add voice_embedding column for speaker identification"""
    
    # Add voice_embedding column (JSONB for 192-dim array)
    op.add_column('segments', 
        sa.Column('voice_embedding', postgresql.JSONB, nullable=True,
                  comment='192-dim SpeechBrain ECAPA voice embedding for speaker identification')
    )
    
    # Add GIN index for faster queries on voice_embedding
    op.create_index(
        'idx_segments_voice_embedding',
        'segments',
        ['voice_embedding'],
        unique=False,
        postgresql_using='gin'
    )


def downgrade() -> None:
    """Remove voice_embedding column"""
    
    # Drop index first
    op.drop_index('idx_segments_voice_embedding', table_name='segments')
    
    # Drop column
    op.drop_column('segments', 'voice_embedding')
