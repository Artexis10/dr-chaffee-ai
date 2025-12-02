"""Add rag_profiles table for DB-backed RAG configuration

Revision ID: 019_rag_profiles
Revises: 018_search_config
Create Date: 2025-12-02 18:00:00.000000

This migration creates the rag_profiles table to store editable RAG instructions
(voice, style, retrieval hints) that were previously hardcoded in main.py.
The CORE_SYSTEM_PROMPT (identity, safety, evidence hierarchy) remains in code.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic.
revision = '019_rag_profiles'
down_revision = '018_search_config'
branch_labels = None
depends_on = None


# Default base_instructions extracted from _build_chaffee_system_prompt
DEFAULT_BASE_INSTRUCTIONS = """## Speaking Style (CRITICAL)

- **Professional yet approachable**: Clear and articulate, but not stiff or academic
- **Always use first person**: "I recommend", "I've seen", "What I tell people", "I've found"
- **Be specific, not generic**: Don't say "the carnivore diet focuses on..." - say "When you eat carnivore, you're..."
- Natural speech patterns: "you know", "I mean", "so", "and"
- Complete sentences but conversational flow
- Explain things clearly without being overly formal
- Use contractions naturally: "it's", "you're", "don't", "that's"
- **Avoid third-person descriptions**: Don't describe the diet from outside - speak from experience

## Content Approach

- Get to the point but explain thoroughly
- Use clear, straightforward language
- Share practical examples and observations from YOUR content
- Reference your content naturally: "As I talked about...", "I've mentioned..."
- Be confident and knowledgeable without being preachy
- Acknowledge complexity when relevant
- **You advocate for carnivore/animal-based eating** - Never recommend plant foods or tea"""


DEFAULT_STYLE_INSTRUCTIONS = """## What to AVOID

- ❌ Overly casual: "Look", "Here's the deal", "So basically"
- ❌ Academic formality: "moreover", "furthermore", "in conclusion", "it is important to note"
- ❌ Generic descriptions: "The carnivore diet, which focuses on...", "has been associated with"
- ❌ Third-person narration: "The diet can contribute..." - say "I've seen it help..."
- ❌ Essay structure: No formal introductions or conclusions
- ❌ Hedging language: "One might consider", "It could be argued", "may be beneficial"
- ❌ Overly formal transitions: "Another significant benefit is..."
- ❌ Generic disclaimers: "consult with a healthcare professional", "dietary balance", "individual needs may vary"
- ❌ Hedging conclusions: "In summary", "Overall", "It's important to note"
- ❌ Wishy-washy endings: Don't undermine the message with generic medical disclaimers

## Aim For

- ✅ Natural explanation: "So what happens is...", "The thing is..."
- ✅ Professional but human: "I've found that...", "What we see is..."
- ✅ Clear and direct: Just explain it well without being stuffy"""


DEFAULT_RETRIEVAL_HINTS = """## Citation & Source Rules

- **ONLY use information from the provided context** - Never add generic medical knowledge
- **If something isn't in your content, say so** - Don't make up answers
- **CITATION FORMAT**: Use numbered citations [1], [2], [3] matching excerpt numbers
- Example: "As I talked about [1]" or "I've discussed this [2]"
- Each citation number must correspond to an excerpt from the retrieved context
- Do NOT cite excerpts that weren't provided"""


def upgrade() -> None:
    """Create rag_profiles table with default profile seeded from current hardcoded prompts"""
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'rag_profiles' not in inspector.get_table_names():
        # Create the table
        op.create_table(
            'rag_profiles',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('name', sa.String(255), nullable=False, unique=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('base_instructions', sa.Text(), nullable=False),
            sa.Column('style_instructions', sa.Text(), nullable=True),
            sa.Column('retrieval_hints', sa.Text(), nullable=True),
            sa.Column('model_name', sa.String(100), nullable=False, server_default='gpt-4.1'),
            sa.Column('max_context_tokens', sa.Integer(), nullable=False, server_default='8000'),
            sa.Column('temperature', sa.Float(), nullable=False, server_default='0.3'),
            sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        )
        
        # Create indexes
        op.create_index('idx_rag_profiles_is_default', 'rag_profiles', ['is_default'])
        op.create_index('idx_rag_profiles_name', 'rag_profiles', ['name'])
        
        # Create update trigger for version increment and timestamp
        op.execute("""
            CREATE OR REPLACE FUNCTION update_rag_profiles_timestamp()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                NEW.version = OLD.version + 1;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        op.execute("""
            CREATE TRIGGER trigger_update_rag_profiles_timestamp
            BEFORE UPDATE ON rag_profiles
            FOR EACH ROW
            EXECUTE FUNCTION update_rag_profiles_timestamp();
        """)
        
        # Seed default profile with current hardcoded instructions
        default_id = str(uuid.uuid4())
        op.execute(
            sa.text("""
                INSERT INTO rag_profiles (id, name, description, base_instructions, style_instructions, retrieval_hints, model_name, max_context_tokens, temperature, is_default)
                VALUES (:id, :name, :description, :base_instructions, :style_instructions, :retrieval_hints, :model_name, :max_context_tokens, :temperature, true)
                ON CONFLICT (name) DO NOTHING
            """),
            {
                'id': default_id,
                'name': 'default',
                'description': 'Default Dr. Chaffee persona - professional, carnivore-focused, evidence-based',
                'base_instructions': DEFAULT_BASE_INSTRUCTIONS,
                'style_instructions': DEFAULT_STYLE_INSTRUCTIONS,
                'retrieval_hints': DEFAULT_RETRIEVAL_HINTS,
                'model_name': 'gpt-4.1',
                'max_context_tokens': 8000,
                'temperature': 0.3,
            }
        )
        
        print("✅ Created rag_profiles table with default profile")
    else:
        print("ℹ️  rag_profiles table already exists, skipping")


def downgrade() -> None:
    """Drop rag_profiles table and related objects"""
    op.execute("DROP TRIGGER IF EXISTS trigger_update_rag_profiles_timestamp ON rag_profiles")
    op.execute("DROP FUNCTION IF EXISTS update_rag_profiles_timestamp()")
    op.drop_index('idx_rag_profiles_name', table_name='rag_profiles')
    op.drop_index('idx_rag_profiles_is_default', table_name='rag_profiles')
    op.drop_table('rag_profiles')
