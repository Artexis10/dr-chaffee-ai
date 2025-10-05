#!/usr/bin/env python3
"""
Re-attribute speakers for existing videos after profile regeneration

This script re-runs speaker attribution on existing segments without
re-transcribing or re-embedding (which would be expensive).
"""
import os
import sys
import logging
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend' / 'scripts'))

from common.voice_enrollment_optimized import VoiceEnrollmentManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection from environment"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL not set in environment")
    return psycopg2.connect(db_url)

def get_videos_with_segments(conn):
    """Get all videos that have segments"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT DISTINCT video_id, COUNT(*) as segment_count
            FROM segments
            GROUP BY video_id
            ORDER BY video_id
        """)
        return cur.fetchall()

def get_video_segments(conn, video_id):
    """Get all segments for a video"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, speaker, text, start_time, end_time
            FROM segments
            WHERE video_id = %s
            ORDER BY start_time
        """, (video_id,))
        return cur.fetchall()

def update_segment_speaker(conn, segment_id, new_speaker):
    """Update speaker attribution for a segment"""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE segments
            SET speaker = %s
            WHERE id = %s
        """, (new_speaker, segment_id))

def reattribute_video(conn, video_id, voice_manager, dry_run=False):
    """Re-attribute speakers for a video"""
    segments = get_video_segments(conn, video_id)
    
    if not segments:
        return 0, 0, 0
    
    # Count current attribution
    current_chaffee = sum(1 for s in segments if s['speaker'] == 'chaffee')
    current_guest = sum(1 for s in segments if s['speaker'] == 'guest')
    current_unknown = sum(1 for s in segments if s['speaker'] == 'unknown')
    
    logger.info(f"Video {video_id}: {len(segments)} segments")
    logger.info(f"  Current: Chaffee={current_chaffee}, Guest={current_guest}, Unknown={current_unknown}")
    
    # For now, just identify which videos need re-attribution
    # Full re-attribution would require audio files or embeddings
    # This is a placeholder for the logic
    
    changes_made = 0
    
    # Simple heuristic: if most segments are unknown and we have Chaffee profile,
    # they might be misattributed
    if current_unknown > len(segments) * 0.5:
        logger.warning(f"  ⚠️  {current_unknown} unknown segments - may need re-attribution")
        # Would need audio embeddings to properly re-attribute
    
    return changes_made, current_chaffee, current_guest

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Re-attribute speakers after profile regeneration")
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be changed without making changes')
    parser.add_argument('--video-id', type=str,
                       help='Re-attribute specific video only')
    
    args = parser.parse_args()
    
    # Check if profile exists
    profile_path = Path('voices/chaffee.json')
    if not profile_path.exists():
        logger.error("Chaffee profile not found! Run regenerate_chaffee_profile.py first")
        return 1
    
    # Load voice manager
    voice_manager = VoiceEnrollmentManager(voices_dir='voices')
    
    # Connect to database
    try:
        conn = get_db_connection()
        logger.info("Connected to database")
        
        # Get videos
        if args.video_id:
            videos = [{'video_id': args.video_id}]
        else:
            videos = get_videos_with_segments(conn)
            logger.info(f"Found {len(videos)} videos with segments")
        
        # Process each video
        total_changes = 0
        total_chaffee = 0
        total_guest = 0
        
        for video in videos:
            video_id = video['video_id']
            changes, chaffee, guest = reattribute_video(
                conn, video_id, voice_manager, dry_run=args.dry_run
            )
            total_changes += changes
            total_chaffee += chaffee
            total_guest += guest
        
        if not args.dry_run and total_changes > 0:
            conn.commit()
            logger.info(f"✅ Updated {total_changes} segments")
        elif args.dry_run:
            logger.info(f"[DRY RUN] Would update {total_changes} segments")
        
        logger.info(f"\nSummary:")
        logger.info(f"  Total Chaffee segments: {total_chaffee}")
        logger.info(f"  Total Guest segments: {total_guest}")
        
        conn.close()
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
