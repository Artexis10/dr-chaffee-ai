"""Add auto_select_model column to rag_profiles

Revision ID: 020_rag_profiles_auto_select
Revises: 019_rag_profiles
Create Date: 2025-12-02 20:00:00.000000

This migration adds the auto_select_model boolean column to enable
automatic model selection based on context length and capabilities.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '020_rag_profiles_auto_select'
down_revision = '019_rag_profiles'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add auto_select_model column with default False for backward compatibility"""
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if column already exists
    columns = [col['name'] for col in inspector.get_columns('rag_profiles')]
    
    if 'auto_select_model' not in columns:
        op.add_column(
            'rag_profiles',
            sa.Column('auto_select_model', sa.Boolean(), nullable=False, server_default='false')
        )
        print("✅ Added auto_select_model column to rag_profiles")
    else:
        print("ℹ️  auto_select_model column already exists, skipping")


def downgrade() -> None:
    """Remove auto_select_model column"""
    op.drop_column('rag_profiles', 'auto_select_model')
