"""Drop segment_embeddings table - using legacy storage only

Revision ID: 017_drop_segment_embeddings
Revises: 016_adaptive_embedding_index
Create Date: 2025-11-21 00:48:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '017_drop_segment_embeddings'
down_revision = '016_adaptive_embedding_index'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop segment_embeddings table and related indexes if they exist"""
    # Drop indexes first (IF EXISTS prevents errors if they don't exist)
    op.execute("DROP INDEX IF EXISTS idx_segment_embeddings_model_key")
    op.execute("DROP INDEX IF EXISTS idx_segment_embeddings_embedding")
    
    # Drop the table only if it exists
    # Check if table exists in information_schema
    conn = op.get_bind()
    inspector = conn.dialect.inspector
    if inspector.has_table('segment_embeddings'):
        op.drop_table('segment_embeddings')


def downgrade() -> None:
    """Restore segment_embeddings table if needed
    
    To restore from a backup:
    1. Check git history: git log --oneline | grep segment_embeddings
    2. Restore the migration file from that commit
    3. Run: alembic upgrade head
    
    Or manually recreate:
    CREATE TABLE segment_embeddings (
        id BIGSERIAL PRIMARY KEY,
        segment_id BIGINT NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
        model_key VARCHAR(255) NOT NULL,
        embedding vector(384),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX idx_segment_embeddings_model_key ON segment_embeddings(model_key);
    CREATE INDEX idx_segment_embeddings_embedding ON segment_embeddings USING ivfflat (embedding vector_cosine_ops);
    """
    # Recreate the table
    op.create_table(
        'segment_embeddings',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('segment_id', sa.BigInteger(), nullable=False),
        sa.Column('model_key', sa.String(255), nullable=False),
        sa.Column('embedding', sa.dialects.postgresql.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['segment_id'], ['segments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate indexes
    op.create_index('idx_segment_embeddings_model_key', 'segment_embeddings', ['model_key'])
    op.create_index('idx_segment_embeddings_embedding', 'segment_embeddings', ['embedding'], postgresql_using='ivfflat')
