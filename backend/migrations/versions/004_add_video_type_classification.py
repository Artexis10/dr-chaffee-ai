"""Add video_type column for monologue vs interview classification

Revision ID: 004
Revises: 003
Create Date: 2025-10-09 03:00:00

This migration adds a video_type column to classify videos as:
- 'monologue': Single speaker (100% Chaffee) - ~90% of content
- 'interview': Multiple speakers with >15% guest content - ~10% of content
- 'monologue_with_clips': Multiple speakers but <15% guest (likely quotes/clips)

This enables:
1. Filtering for high-accuracy AI summarization (monologues only)
2. Identifying videos that may need manual review (interviews)
3. Performance optimization (monologues use fast-path processing)
4. Accuracy reporting (monologues ~100%, interviews ~63%)

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add video_type column and classify existing videos."""
    
    print("="*80)
    print("Adding video_type classification column")
    print("="*80)
    
    # 1. Add the column (if not exists)
    print("\n[1/3] Adding video_type column...")
    op.execute("""
        ALTER TABLE segments 
        ADD COLUMN IF NOT EXISTS video_type VARCHAR(20)
    """)
    print("      [OK] Column added")
    
    # 2. Classify existing videos based on speaker distribution
    print("\n[2/3] Classifying existing videos...")
    op.execute("""
        WITH video_speakers AS (
            SELECT 
                video_id,
                COUNT(DISTINCT speaker_label) as num_speakers,
                SUM(CASE WHEN speaker_label='GUEST' THEN 1 ELSE 0 END) as guest_segments,
                COUNT(*) as total_segments
            FROM segments
            WHERE speaker_label IS NOT NULL
            GROUP BY video_id
        )
        UPDATE segments s
        SET video_type = CASE
            WHEN vs.num_speakers = 1 THEN 'monologue'
            WHEN vs.guest_segments::float / vs.total_segments > 0.15 THEN 'interview'
            ELSE 'monologue_with_clips'
        END
        FROM video_speakers vs
        WHERE s.video_id = vs.video_id
    """)
    print("      [OK] Videos classified")
    
    # 3. Add index for efficient filtering (if not exists)
    print("\n[3/3] Creating index on video_type...")
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_segments_video_type 
        ON segments(video_type)
    """)
    print("      [OK] Index created")
    
    # 4. Add column comment for documentation
    op.execute("""
        COMMENT ON COLUMN segments.video_type IS 
        'Video classification: monologue (1 speaker, ~100% accuracy), interview (2+ speakers >15% guest, ~63% accuracy), or monologue_with_clips (2+ speakers <15% guest)'
    """)
    
    # 5. Show classification results
    print("\n" + "="*80)
    print("Classification Summary:")
    print("="*80)
    result = op.get_bind().execute(sa.text("""
        SELECT 
            video_type,
            COUNT(DISTINCT video_id) as num_videos,
            COUNT(*) as num_segments,
            ROUND(AVG(CASE WHEN speaker_label='Chaffee' THEN 1 ELSE 0 END) * 100, 1) as avg_chaffee_pct
        FROM segments
        WHERE video_type IS NOT NULL
        GROUP BY video_type
        ORDER BY num_videos DESC
    """))
    
    print(f"\n{'Type':<25} {'Videos':<10} {'Segments':<12} {'Avg Chaffee %':<15}")
    print("-"*80)
    for row in result:
        print(f"{row[0]:<25} {row[1]:<10} {row[2]:<12} {row[3]:<15}")
    
    print("\n" + "="*80)
    print("[OK] Migration complete!")
    print("\nUsage examples:")
    print("  -- Get only monologue videos for AI summarization")
    print("  SELECT * FROM segments WHERE video_type = 'monologue'")
    print("\n  -- Filter out interviews for high-accuracy processing")
    print("  SELECT * FROM segments WHERE video_type IN ('monologue', 'monologue_with_clips')")
    print("="*80 + "\n")


def downgrade() -> None:
    """Remove video_type column."""
    
    print("Removing video_type classification...")
    
    # Drop index
    op.drop_index('idx_segments_video_type', table_name='segments')
    
    # Drop column
    op.drop_column('segments', 'video_type')
    
    print("[OK] video_type column removed")
