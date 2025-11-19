"""Add custom instructions for AI tuning (stub - already applied)

Revision ID: 012_custom_instructions
Revises: 011
Create Date: 2025-11-14 20:30:00.000000

This is a stub migration that was already partially applied to the database.
The actual schema changes are applied in migration 014.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '012_custom_instructions'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This migration is a no-op because the tables were already created
    # in the previous failed deployment. Migration 014 will handle
    # creating them if they don't exist.
    pass


def downgrade() -> None:
    pass
