"""Fix alembic_version table to use numeric revision IDs

Revision ID: 014
Revises: 012_custom_instructions
Create Date: 2025-11-19 21:54:00

The database has '012_custom_instructions' recorded in alembic_version.
This migration chains from that revision and updates the version number
to '014' while creating the custom_instructions tables.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '014'
down_revision = '012_custom_instructions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The database has '012_custom_instructions' in alembic_version from a previous
    # failed deployment. We need to handle this gracefully.
    conn = op.get_bind()
    
    # Check if the problematic revision exists
    result = conn.execute(sa.text(
        "SELECT version_num FROM alembic_version WHERE version_num = '012_custom_instructions'"
    ))
    
    if result.fetchone():
        # Delete it so Alembic can continue - the tables were already created
        conn.execute(sa.text(
            "DELETE FROM alembic_version WHERE version_num = '012_custom_instructions'"
        ))
    
    # Now apply migration 012's changes if they haven't been applied yet
    # Check if custom_instructions table exists
    inspector = sa.inspect(conn)
    if 'custom_instructions' not in inspector.get_table_names():
        # Create custom_instructions table
        op.create_table(
            'custom_instructions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(255), nullable=False, unique=True),
            sa.Column('instructions', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name', name='uq_custom_instructions_name')
        )
        
        # Create index for active lookup
        op.create_index(
            'idx_custom_instructions_active',
            'custom_instructions',
            ['is_active']
        )
        
        # Create custom_instructions_history table
        op.create_table(
            'custom_instructions_history',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('instruction_id', sa.Integer(), nullable=False),
            sa.Column('instructions', sa.Text(), nullable=False),
            sa.Column('version', sa.Integer(), nullable=False),
            sa.Column('changed_by', sa.String(255), nullable=True),
            sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['instruction_id'], ['custom_instructions.id'], ondelete='CASCADE')
        )
        
        # Create index for history lookup
        op.create_index(
            'idx_custom_instructions_history_instruction_id',
            'custom_instructions_history',
            ['instruction_id']
        )
        
        # Insert default empty instruction set
        op.execute("""
            INSERT INTO custom_instructions (name, instructions, description, is_active)
            VALUES ('default', '', 'Default empty instruction set - add your custom guidance here', true)
            ON CONFLICT (name) DO NOTHING
        """)
        
        # Create trigger function for automatic versioning
        op.execute("""
            CREATE OR REPLACE FUNCTION update_custom_instructions_timestamp()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                NEW.version = OLD.version + 1;
                
                -- Archive old version to history
                INSERT INTO custom_instructions_history (instruction_id, instructions, version, changed_at)
                VALUES (OLD.id, OLD.instructions, OLD.version, CURRENT_TIMESTAMP);
                
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # Create trigger
        op.execute("""
            CREATE TRIGGER trigger_update_custom_instructions_timestamp
            BEFORE UPDATE ON custom_instructions
            FOR EACH ROW
            EXECUTE FUNCTION update_custom_instructions_timestamp();
        """)


def downgrade() -> None:
    # Revert the version number change
    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE alembic_version SET version_num = '012_custom_instructions' WHERE version_num = '012'"
    ))
