"""Fix rag_requests.rag_profile_id column type

Revision ID: 027
Revises: 026
Create Date: 2025-12-04

This migration ensures rag_profile_id is VARCHAR(36) to accept UUID strings.
The error "invalid input syntax for type integer" indicates the column may have
been created as INTEGER in some deployments.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Ensure rag_profile_id is VARCHAR(36) in rag_requests table."""
    
    # Check if rag_requests table exists
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'rag_requests'
        )
    """))
    table_exists = result.scalar()
    
    if not table_exists:
        print("[SKIP] rag_requests table does not exist")
        return
    
    # Check current column type
    result = conn.execute(sa.text("""
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'rag_requests' 
        AND column_name = 'rag_profile_id'
    """))
    row = result.fetchone()
    
    if not row:
        print("[SKIP] rag_profile_id column does not exist")
        return
    
    current_type = row[0].lower()
    print(f"[INFO] Current rag_profile_id type: {current_type}")
    
    if current_type in ('character varying', 'varchar', 'text'):
        print("[SKIP] rag_profile_id is already a string type")
        return
    
    # Need to alter column type from integer to varchar
    # First, drop any existing data (it's corrupted anyway if type is wrong)
    print("[INFO] Altering rag_profile_id from INTEGER to VARCHAR(36)")
    
    try:
        # Try to cast existing values (will fail if they're integers)
        op.execute("""
            ALTER TABLE rag_requests 
            ALTER COLUMN rag_profile_id TYPE VARCHAR(36) 
            USING rag_profile_id::VARCHAR(36)
        """)
        print("[OK] Altered rag_profile_id to VARCHAR(36)")
    except Exception as e:
        print(f"[WARN] Could not cast existing values: {e}")
        # If cast fails, set to NULL first then alter
        op.execute("UPDATE rag_requests SET rag_profile_id = NULL")
        op.execute("ALTER TABLE rag_requests ALTER COLUMN rag_profile_id TYPE VARCHAR(36)")
        print("[OK] Reset rag_profile_id to NULL and altered to VARCHAR(36)")


def downgrade() -> None:
    """Revert rag_profile_id to original type (no-op, keep as VARCHAR)."""
    # We don't want to revert to INTEGER as that would break things
    print("[SKIP] Keeping rag_profile_id as VARCHAR(36)")
