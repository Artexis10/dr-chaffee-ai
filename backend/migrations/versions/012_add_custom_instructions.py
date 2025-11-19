"""Add custom instructions for AI tuning

Revision ID: 012_custom_instructions
Revises: 011
Create Date: 2025-11-14 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create custom_instructions and custom_instructions_history tables"""
    
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
    """Drop custom_instructions tables and related objects"""
    
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS trigger_update_custom_instructions_timestamp ON custom_instructions")
    
    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_custom_instructions_timestamp()")
    
    # Drop indexes
    op.drop_index('idx_custom_instructions_history_instruction_id', table_name='custom_instructions_history')
    op.drop_index('idx_custom_instructions_active', table_name='custom_instructions')
    
    # Drop tables
    op.drop_table('custom_instructions_history')
    op.drop_table('custom_instructions')
