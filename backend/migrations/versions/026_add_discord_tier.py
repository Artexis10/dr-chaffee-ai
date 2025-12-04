"""Add discord_tier column to users table

Revision ID: 026
Revises: 025
Create Date: 2025-12-04

This migration adds a discord_tier column to store the user's membership tier
resolved from their Discord roles. The tier is computed at login time and
stored for efficient retrieval.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add discord_tier column to users table."""
    # Add nullable discord_tier column
    op.add_column(
        'users',
        sa.Column('discord_tier', sa.String(50), nullable=True)
    )
    
    # Add index for potential tier-based queries
    op.create_index(
        'idx_users_discord_tier',
        'users',
        ['discord_tier']
    )


def downgrade() -> None:
    """Remove discord_tier column from users table."""
    op.drop_index('idx_users_discord_tier', table_name='users')
    op.drop_column('users', 'discord_tier')
