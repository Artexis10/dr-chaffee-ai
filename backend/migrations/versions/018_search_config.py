"""Add search_config table for persistent search configuration

Revision ID: 018_search_config
Revises: 017
Create Date: 2025-11-27 03:30:00.000000

This migration creates the search_config table to persist search parameters
configured via the tuning dashboard. Without this table, search config
changes are runtime-only and reset on server restart.

To apply: alembic upgrade head
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '018_search_config'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create search_config table for persistent search configuration"""
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'search_config' not in inspector.get_table_names():
        op.create_table(
            'search_config',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('top_k', sa.Integer(), nullable=False, server_default='100'),
            sa.Column('min_similarity', sa.Float(), nullable=False, server_default='0.3'),
            sa.Column('enable_reranker', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('rerank_top_k', sa.Integer(), nullable=False, server_default='200'),
            sa.Column('return_top_k', sa.Integer(), nullable=False, server_default='20'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Insert default row (id=1) so upsert works correctly
        op.execute("""
            INSERT INTO search_config (id, top_k, min_similarity, enable_reranker, rerank_top_k, return_top_k)
            VALUES (1, 100, 0.3, false, 200, 20)
            ON CONFLICT (id) DO NOTHING
        """)
        
        print("✅ Created search_config table with default values")
    else:
        print("ℹ️  search_config table already exists, skipping")


def downgrade() -> None:
    """Drop search_config table"""
    op.drop_table('search_config')
