"""Initial database schema with pgvector support

Revision ID: 001
Revises: 
Create Date: 2025-10-01 13:10:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create sources table (merged videos + processing state)
    op.create_table('sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.String(255), nullable=False, comment='video_id or unique identifier'),
        sa.Column('source_type', sa.String(50), nullable=False, comment='youtube, zoom, local, etc.'),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('channel_name', sa.String(255), nullable=True),
        sa.Column('channel_url', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('duration_s', sa.Integer(), nullable=True, comment='Duration in seconds'),
        sa.Column('view_count', sa.Integer(), nullable=True),
        sa.Column('like_count', sa.Integer(), nullable=True),
        sa.Column('comment_count', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, comment='Processing metadata, model info, etc.'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending', comment='pending, processing, completed, failed'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_type', 'source_id', name='unique_source')
    )
    
    # Enable pgvector extension first
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create segments table (transcript segments with speaker attribution)
    op.execute("""
        CREATE TABLE segments (
            id SERIAL PRIMARY KEY,
            video_id VARCHAR(255) NOT NULL,
            start_sec FLOAT NOT NULL,
            end_sec FLOAT NOT NULL,
            text TEXT NOT NULL,
            speaker_label VARCHAR(50),
            speaker_confidence FLOAT,
            embedding vector(384),
            avg_logprob FLOAT,
            compression_ratio FLOAT,
            no_speech_prob FLOAT,
            temperature_used FLOAT,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)
    
    # Create api_cache table for YouTube Data API caching
    op.create_table('api_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(255), nullable=False),
        sa.Column('etag', sa.String(255), nullable=True),
        sa.Column('data', postgresql.JSONB(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cache_key')
    )
    
    # Create indexes for performance
    op.create_index('idx_segments_video_id', 'segments', ['video_id'])
    op.create_index('idx_segments_speaker', 'segments', ['speaker_label'])
    op.create_index('idx_segments_time', 'segments', ['video_id', 'start_sec'])
    op.create_index('idx_sources_lookup', 'sources', ['source_type', 'source_id'])
    op.create_index('idx_sources_status', 'sources', ['status'])
    op.create_index('idx_sources_updated', 'sources', ['updated_at'])
    
    # Create pgvector index for semantic search
    # Note: This requires data to be present for optimal performance
    # Lists parameter tuned for expected dataset size (~100k segments)
    op.execute("""
        CREATE INDEX segments_embedding_idx 
        ON segments USING ivfflat (embedding vector_l2_ops) 
        WITH (lists = 100)
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('api_cache')
    op.drop_table('segments')
    op.drop_table('sources')
    
    # Drop pgvector extension
    op.execute('DROP EXTENSION IF EXISTS vector CASCADE')
