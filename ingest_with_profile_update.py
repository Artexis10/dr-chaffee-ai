#!/usr/bin/env python3
"""
Ingestion wrapper that automatically updates Chaffee profile with high-confidence segments

This script:
1. Runs normal ingestion
2. After each video, checks if it's >95% Chaffee content
3. If yes, updates the Chaffee profile with those embeddings
4. Profile gets stronger over time with more data

Usage:
    python ingest_with_profile_update.py --channel-url <url>
    python ingest_with_profile_update.py --from-json videos.json
"""
import os
import sys
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from backend.scripts.common.segments_database import SegmentsDatabase
from backend.scripts.common.voice_enrollment_optimized import VoiceEnrollment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


def get_high_confidence_chaffee_videos(db: SegmentsDatabase, min_chaffee_pct: float = 95.0, min_segments: int = 10):
    """Get videos with very high Chaffee percentage for profile updates"""
    query = """
    SELECT 
        video_id,
        COUNT(*) as total_segments,
        SUM(CASE WHEN speaker_label = 'Chaffee' THEN 1 ELSE 0 END) as chaffee_segments,
        SUM(CASE WHEN speaker_label = 'Chaffee' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as chaffee_pct
    FROM segments
    WHERE speaker_label IS NOT NULL
    GROUP BY video_id
    HAVING 
        COUNT(*) >= %s AND
        SUM(CASE WHEN speaker_label = 'Chaffee' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) >= %s
    ORDER BY chaffee_pct DESC, total_segments DESC
    """
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (min_segments, min_chaffee_pct))
            results = cur.fetchall()
    
    videos = []
    for row in results:
        videos.append({
            'video_id': row[0],
            'total_segments': row[1],
            'chaffee_segments': row[2],
            'chaffee_pct': row[3]
        })
    
    return videos


def update_profile_from_videos(video_ids: list, enrollment: VoiceEnrollment):
    """Update Chaffee profile with embeddings from high-confidence videos"""
    audio_dir = Path("audio_storage")
    audio_sources = []
    
    for video_id in video_ids:
        # Find audio file
        for ext in ['.wav', '.m4a', '.mp4', '.webm']:
            audio_path = audio_dir / f"{video_id}{ext}"
            if audio_path.exists():
                audio_sources.append(str(audio_path))
                break
    
    if not audio_sources:
        logger.warning("No audio files found for profile update")
        return False
    
    logger.info(f"Updating Chaffee profile with {len(audio_sources)} high-confidence videos...")
    
    # Update profile (adds to existing embeddings)
    profile = enrollment.enroll_speaker(
        name='chaffee',
        audio_sources=audio_sources,
        overwrite=False,
        update=True,  # KEY: This adds to existing profile
        min_duration=10.0
    )
    
    if profile:
        logger.info(f"✅ Profile updated! Now has {profile['metadata']['num_embeddings']} embeddings")
        return True
    else:
        logger.error("Failed to update profile")
        return False


def main():
    parser = argparse.ArgumentParser(description="Ingest with automatic profile strengthening")
    parser.add_argument('--channel-url', type=str, help='YouTube channel URL')
    parser.add_argument('--from-json', type=str, help='JSON file with video IDs')
    parser.add_argument('--min-chaffee-pct', type=float, default=95.0,
                       help='Minimum Chaffee percentage for profile update (default: 95)')
    parser.add_argument('--update-interval', type=int, default=10,
                       help='Update profile every N videos (default: 10)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be updated without updating')
    
    args = parser.parse_args()
    
    # Initialize
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL not set!")
        return 1
    
    db = SegmentsDatabase(db_url)
    voices_dir = Path(os.getenv('VOICES_DIR', 'voices'))
    enrollment = VoiceEnrollment(voices_dir=str(voices_dir))
    
    # Step 1: Run normal ingestion
    logger.info("=" * 80)
    logger.info("STEP 1: Running ingestion...")
    logger.info("=" * 80)
    
    # Build ingestion command
    cmd = ['python', 'backend/scripts/ingest_youtube_enhanced.py']
    
    if args.channel_url:
        cmd.extend(['--channel-url', args.channel_url])
    elif args.from_json:
        cmd.extend(['--from-json', args.from_json])
    else:
        logger.error("Must specify --channel-url or --from-json")
        return 1
    
    # Run ingestion
    import subprocess
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        logger.error("Ingestion failed!")
        return 1
    
    # Step 2: Find high-confidence Chaffee videos
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2: Finding high-confidence Chaffee videos for profile update...")
    logger.info("=" * 80)
    
    videos = get_high_confidence_chaffee_videos(db, min_chaffee_pct=args.min_chaffee_pct)
    
    if not videos:
        logger.info(f"No videos found with >={args.min_chaffee_pct}% Chaffee content")
        return 0
    
    logger.info(f"\nFound {len(videos)} high-confidence Chaffee videos:")
    for v in videos[:10]:
        logger.info(f"  {v['video_id']}: {v['chaffee_pct']:.1f}% Chaffee ({v['chaffee_segments']}/{v['total_segments']} segments)")
    
    if len(videos) > 10:
        logger.info(f"  ... and {len(videos) - 10} more")
    
    # Step 3: Update profile
    if args.dry_run:
        logger.info("\n[DRY RUN] Would update profile with these videos")
        return 0
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 3: Updating Chaffee profile...")
    logger.info("=" * 80)
    
    # Use top videos for update (limit to avoid too much processing)
    update_videos = [v['video_id'] for v in videos[:args.update_interval]]
    
    success = update_profile_from_videos(update_videos, enrollment)
    
    if success:
        logger.info("\n🎉 Ingestion complete with profile strengthening!")
        return 0
    else:
        logger.warning("\n⚠️  Ingestion complete but profile update failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
