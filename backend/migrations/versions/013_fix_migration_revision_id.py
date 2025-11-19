"""Placeholder migration after custom instructions

Revision ID: 013
Revises: 012_custom_instructions
Create Date: 2025-11-19 21:40:00

This migration serves as a placeholder to establish the migration chain after
the custom_instructions migration.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012_custom_instructions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This migration exists only to bridge the revision ID change
    # The actual custom_instructions tables were already created by the previous migration
    # This just ensures the migration history is consistent
    pass


def downgrade() -> None:
    # No-op for downgrade
    pass
