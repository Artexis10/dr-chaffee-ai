#!/usr/bin/env python3
"""
Bootstrap and improve Chaffee voice profile using existing ingested videos

This script:
1. Queries the database for videos with high Chaffee percentage (>80%)
2. Extracts voice embeddings from Chaffee-labeled segments
3. Deduplicates and improves the voice profile
4. Creates an enhanced centroid-only profile

Usage:
    python bootstrap_chaffee_profile.py --num-videos 30 --min-chaffee-pct 80
"""
import os
import sys
import json
import argparse
import logging
import numpy as np
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import tempfile
import soundfile as sf
import librosa

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from backend.scripts.common.segments_database import SegmentsDatabase
from backend.scripts.common.voice_enrollment_optimized import VoiceEnrollment
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


def get_high_chaffee_videos(db: SegmentsDatabase, num_videos: int = 30, min_chaffee_pct: float = 80.0):
    """Get videos with high Chaffee percentage from database"""
    logger.info(f"Querying database for videos with >{min_chaffee_pct}% Chaffee content...")
    
    # Query to get speaker distribution per video
    query = """
    SELECT 
        video_id,
        COUNT(*) as total_segments,
        SUM(CASE WHEN speaker = 'Chaffee' THEN 1 ELSE 0 END) as chaffee_segments,
        SUM(CASE WHEN speaker = 'Chaffee' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as chaffee_pct
    FROM segments
    WHERE speaker IS NOT NULL
    GROUP BY video_id
    HAVING chaffee_pct >= %s
    ORDER BY total_segments DESC, chaffee_pct DESC
    LIMIT %s
    """
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (min_chaffee_pct, num_videos))
            results = cur.fetchall()
    
    videos = []
    for row in results:
        videos.append({
            'video_id': row[0],
            'total_segments': row[1],
            'chaffee_segments': row[2],
            'chaffee_pct': row[3]
        })
    
    logger.info(f"Found {len(videos)} videos with >{min_chaffee_pct}% Chaffee content")
    return videos


def extract_chaffee_embeddings(db: SegmentsDatabase, video_ids: list, enrollment: VoiceEnrollment):
    """Extract voice embeddings from Chaffee segments"""
    logger.info(f"Extracting embeddings from {len(video_ids)} videos...")
    
    all_embeddings = []
    audio_dir = Path("audio_storage")
    
    for idx, video_id in enumerate(video_ids, 1):
        logger.info(f"[{idx}/{len(video_ids)}] Processing {video_id}...")
        
        # Get Chaffee segments for this video
        query = """
        SELECT start_time, end_time, embedding
        FROM segments
        WHERE video_id = %s AND speaker = 'Chaffee'
        ORDER BY start_time
        """
        
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (video_id,))
                segments = cur.fetchall()
        
        if not segments:
            logger.warning(f"  No Chaffee segments found for {video_id}")
            continue
        
        logger.info(f"  Found {len(segments)} Chaffee segments")
        
        # Find audio file
        audio_path = None
        for ext in ['.m4a', '.mp4', '.wav', '.webm']:
            candidate = audio_dir / f"{video_id}{ext}"
            if candidate.exists():
                audio_path = candidate
                break
        
        if not audio_path:
            logger.warning(f"  Audio file not found for {video_id}")
            continue
        
        # Extract embeddings from segments
        segment_count = 0
        for start_time, end_time, stored_embedding in segments:
            try:
                # Use stored embedding if available
                if stored_embedding:
                    all_embeddings.append(np.array(stored_embedding))
                    segment_count += 1
                else:
                    # Extract from audio
                    duration = end_time - start_time
                    if duration >= 1.0:  # At least 1 second
                        audio, sr = librosa.load(str(audio_path), sr=16000, offset=start_time, duration=duration)
                        
                        # Save to temp file
                        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                            tmp_path = tmp.name
                        
                        sf.write(tmp_path, audio, sr)
                        embeddings = enrollment._extract_embeddings_from_audio(tmp_path)
                        os.unlink(tmp_path)
                        
                        if embeddings:
                            all_embeddings.extend(embeddings)
                            segment_count += len(embeddings)
            except Exception as e:
                logger.debug(f"  Failed to extract embedding from [{start_time:.1f}-{end_time:.1f}s]: {e}")
                continue
        
        logger.info(f"  Extracted {segment_count} embeddings from {video_id}")
    
    logger.info(f"Total embeddings extracted: {len(all_embeddings)}")
    return all_embeddings


def deduplicate_embeddings(embeddings: list, similarity_threshold: float = 0.99):
    """Remove duplicate and near-duplicate embeddings"""
    logger.info(f"Deduplicating {len(embeddings)} embeddings...")
    
    from sklearn.metrics.pairwise import cosine_similarity
    
    embeddings_array = np.array(embeddings)
    
    # Remove exact duplicates
    unique_embeddings = np.unique(embeddings_array, axis=0)
    logger.info(f"  After removing exact duplicates: {len(unique_embeddings)} embeddings")
    
    # Remove near-duplicates
    deduplicated = [unique_embeddings[0]]
    for emb in unique_embeddings[1:]:
        # Check similarity with all kept embeddings
        sims = cosine_similarity([emb], deduplicated)[0]
        if np.max(sims) < similarity_threshold:
            deduplicated.append(emb)
    
    logger.info(f"  After removing near-duplicates (>{similarity_threshold} similarity): {len(deduplicated)} embeddings")
    return deduplicated


def create_improved_profile(embeddings: list, output_path: Path, source_videos: list):
    """Create improved centroid-only profile"""
    logger.info("Creating improved voice profile...")
    
    # Calculate centroid
    centroid = np.mean(embeddings, axis=0).tolist()
    
    # Create profile
    profile = {
        'name': 'chaffee',
        'centroid': centroid,
        'threshold': 0.62,
        'created_at': datetime.now().isoformat(),
        'audio_sources': [v['video_id'] for v in source_videos],
        'metadata': {
            'source': 'bootstrap_chaffee_profile.py',
            'num_embeddings': len(embeddings),
            'num_source_videos': len(source_videos),
            'profile_type': 'centroid_only',
            'bootstrap_version': '2.0'
        }
    }
    
    # Save profile
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2)
    
    logger.info(f"✅ Saved improved profile to {output_path}")
    logger.info(f"   Centroid dimensions: {len(centroid)}")
    logger.info(f"   Source embeddings: {len(embeddings)}")
    logger.info(f"   Source videos: {len(source_videos)}")


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Chaffee voice profile from existing data")
    parser.add_argument('--num-videos', type=int, default=30,
                       help='Number of videos to use (default: 30)')
    parser.add_argument('--min-chaffee-pct', type=float, default=80.0,
                       help='Minimum Chaffee percentage (default: 80.0)')
    parser.add_argument('--output', type=str, default='voices/chaffee_bootstrapped.json',
                       help='Output profile path (default: voices/chaffee_bootstrapped.json)')
    parser.add_argument('--overwrite-main', action='store_true',
                       help='Overwrite main chaffee.json profile')
    
    args = parser.parse_args()
    
    # Initialize database
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not set!")
        return 1
    db = SegmentsDatabase(db_url)
    
    # Initialize voice enrollment
    voices_dir = Path(os.getenv('VOICES_DIR', 'voices'))
    voices_dir.mkdir(exist_ok=True)
    enrollment = VoiceEnrollment(voices_dir=str(voices_dir))
    
    # Step 1: Get high-Chaffee videos
    videos = get_high_chaffee_videos(db, args.num_videos, args.min_chaffee_pct)
    
    if not videos:
        logger.error("No suitable videos found!")
        return 1
    
    logger.info("\nTop videos:")
    for i, v in enumerate(videos[:10], 1):
        logger.info(f"  {i}. {v['video_id']}: {v['chaffee_pct']:.1f}% Chaffee ({v['chaffee_segments']}/{v['total_segments']} segments)")
    
    # Step 2: Extract embeddings
    video_ids = [v['video_id'] for v in videos]
    embeddings = extract_chaffee_embeddings(db, video_ids, enrollment)
    
    if not embeddings:
        logger.error("No embeddings extracted!")
        return 1
    
    # Step 3: Deduplicate
    deduplicated = deduplicate_embeddings(embeddings)
    
    # Step 4: Create improved profile
    output_path = Path(args.output)
    create_improved_profile(deduplicated, output_path, videos)
    
    # Optionally overwrite main profile
    if args.overwrite_main:
        main_profile = voices_dir / 'chaffee.json'
        logger.info(f"\n⚠️  Backing up existing profile to chaffee_backup.json")
        if main_profile.exists():
            import shutil
            shutil.copy(main_profile, voices_dir / 'chaffee_backup.json')
        
        shutil.copy(output_path, main_profile)
        logger.info(f"✅ Overwrote main profile: {main_profile}")
    
    logger.info("\n🎉 Profile bootstrap complete!")
    logger.info(f"   New profile: {output_path}")
    logger.info(f"   To use it, copy to voices/chaffee.json or run with --overwrite-main")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
