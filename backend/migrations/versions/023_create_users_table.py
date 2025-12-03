"""Create users table for Discord OAuth

Revision ID: 023
Revises: 022
Create Date: 2025-12-03

This migration creates a users table to store Discord user information
for OAuth authentication. The table is designed to:
- Store Discord user identity (discord_id as unique key)
- Track user metadata (username, discriminator, global_name)
- Support future auth providers via nullable discord fields
- Not break existing tuning dashboard users (separate auth system)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create users table with Discord OAuth fields."""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        
        # Discord OAuth fields
        sa.Column('discord_id', sa.String(255), unique=True, nullable=True, index=True),
        sa.Column('discord_username', sa.String(255), nullable=True),
        sa.Column('discord_discriminator', sa.String(10), nullable=True),
        sa.Column('discord_global_name', sa.String(255), nullable=True),
        sa.Column('discord_avatar', sa.String(255), nullable=True),
        
        # Audit fields
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
    )
    
    # Create index on discord_id for fast lookups
    op.create_index('idx_users_discord_id', 'users', ['discord_id'], unique=True)


def downgrade() -> None:
    """Drop users table."""
    op.drop_index('idx_users_discord_id', table_name='users')
    op.drop_table('users')
