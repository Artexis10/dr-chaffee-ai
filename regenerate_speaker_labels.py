#!/usr/bin/env python3
"""
Regenerate speaker labels for all existing segments using improved identification logic

This script:
1. Loads all segments from database
2. Re-runs speaker identification with improved multi-tier thresholds
3. Updates speaker_label in database
4. Uses stored embeddings (no re-transcription needed)

Usage:
    python regenerate_speaker_labels.py --dry-run  # Preview changes
    python regenerate_speaker_labels.py            # Apply changes
"""
import os
import sys
import logging
import argparse
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm

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


def get_all_segments_with_embeddings(db: SegmentsDatabase):
    """Get all segments that have embeddings"""
    logger.info("Fetching all segments with embeddings from database...")
    
    query = """
    SELECT id, video_id, speaker_label, embedding, start_sec, end_sec
    FROM segments
    WHERE embedding IS NOT NULL
    ORDER BY video_id, start_sec
    """
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
    
    segments = []
    for row in results:
        # Convert embedding to numpy array (suppress printing)
        emb = np.array(row[3]) if row[3] else None
        segments.append({
            'id': row[0],
            'video_id': row[1],
            'speaker_label': row[2],
            'embedding': emb,
            'start_sec': float(row[4]),
            'end_sec': float(row[5])
        })
    
    logger.info(f"Found {len(segments)} segments with embeddings")
    return segments


def identify_speaker_improved(embedding, chaffee_profile, enrollment, prev_speaker=None):
    """
    Improved speaker identification with multi-tier thresholds
    
    Args:
        embedding: Voice embedding
        chaffee_profile: Chaffee voice profile
        enrollment: VoiceEnrollment instance
        prev_speaker: Previous segment's speaker (for temporal context)
    
    Returns:
        tuple: (speaker_label, confidence, similarity)
    """
    if embedding is None:
        return 'Unknown', 0.0, 0.0
    
    # Compute similarity to Chaffee profile
    similarity = float(enrollment.compute_similarity(embedding, chaffee_profile))
    
    # Multi-tier threshold system
    if similarity > 0.75:
        # High confidence - definitely Chaffee
        return 'Chaffee', similarity, similarity
    elif similarity > 0.65:
        # Medium confidence - use temporal context
        if prev_speaker == 'Chaffee':
            return 'Chaffee', similarity, similarity
        else:
            return 'GUEST', 1.0 - similarity, similarity
    else:
        # Low confidence - likely Guest
        return 'GUEST', 1.0 - similarity, similarity


def smooth_speaker_labels(segments_by_video):
    """
    Post-process to smooth isolated misidentifications
    
    Args:
        segments_by_video: Dict of video_id -> list of segments
    
    Returns:
        int: Number of segments smoothed
    """
    smoothed_count = 0
    
    for video_id, segments in segments_by_video.items():
        if len(segments) < 3:
            continue
        
        for i in range(1, len(segments) - 1):
            prev_speaker = segments[i-1]['new_speaker']
            curr_speaker = segments[i]['new_speaker']
            next_speaker = segments[i+1]['new_speaker']
            
            # If surrounded by same speaker and different from current
            if prev_speaker == next_speaker and curr_speaker != prev_speaker:
                # Check if it's a short segment (< 10s)
                duration = segments[i]['end_sec'] - segments[i]['start_sec']
                if duration < 10:
                    # Smooth to match surrounding
                    segments[i]['new_speaker'] = prev_speaker
                    segments[i]['smoothed'] = True
                    smoothed_count += 1
    
    return smoothed_count


def regenerate_labels(db: SegmentsDatabase, dry_run=False):
    """Regenerate speaker labels for all segments"""
    
    # Load Chaffee profile
    voices_dir = Path(os.getenv('VOICES_DIR', 'voices'))
    enrollment = VoiceEnrollment(voices_dir=str(voices_dir))
    chaffee_profile = enrollment.load_profile('chaffee')
    
    if not chaffee_profile:
        logger.error("Chaffee profile not found!")
        return 1
    
    logger.info(f"Loaded Chaffee profile from {voices_dir / 'chaffee.json'}")
    
    # Get all segments
    segments = get_all_segments_with_embeddings(db)
    
    if not segments:
        logger.error("No segments with embeddings found!")
        return 1
    
    # Group by video for temporal context
    segments_by_video = {}
    for seg in segments:
        video_id = seg['video_id']
        if video_id not in segments_by_video:
            segments_by_video[video_id] = []
        segments_by_video[video_id].append(seg)
    
    logger.info(f"Processing {len(segments_by_video)} videos...")
    
    # Re-identify speakers
    changes = 0
    prev_speaker_by_video = {}
    
    logger.info(f"Re-identifying speakers for {len(segments)} segments...")
    for idx, seg in enumerate(segments, 1):
        if idx % 100 == 0:
            logger.info(f"  Progress: {idx}/{len(segments)} segments ({idx/len(segments)*100:.1f}%)")
        
        video_id = seg['video_id']
        prev_speaker = prev_speaker_by_video.get(video_id)
        
        new_speaker, confidence, similarity = identify_speaker_improved(
            seg['embedding'],
            chaffee_profile,
            enrollment,
            prev_speaker
        )
        
        seg['new_speaker'] = new_speaker
        seg['confidence'] = confidence
        seg['similarity'] = similarity
        seg['smoothed'] = False
        
        prev_speaker_by_video[video_id] = new_speaker
        
        if seg['speaker_label'] != new_speaker:
            changes += 1
    
    # Apply smoothing
    logger.info("Applying temporal smoothing...")
    smoothed_count = smooth_speaker_labels(segments_by_video)
    logger.info(f"Smoothed {smoothed_count} isolated misidentifications")
    
    # Show statistics
    old_chaffee = sum(1 for s in segments if s['speaker_label'] == 'Chaffee')
    old_guest = sum(1 for s in segments if s['speaker_label'] and 'GUEST' in s['speaker_label'].upper())
    old_unknown = sum(1 for s in segments if not s['speaker_label'] or s['speaker_label'] == 'Unknown')
    
    new_chaffee = sum(1 for s in segments if s['new_speaker'] == 'Chaffee')
    new_guest = sum(1 for s in segments if s['new_speaker'] == 'GUEST')
    new_unknown = sum(1 for s in segments if s['new_speaker'] == 'Unknown')
    
    logger.info("\n" + "="*80)
    logger.info("SPEAKER LABEL CHANGES")
    logger.info("="*80)
    logger.info(f"Old labels: Chaffee={old_chaffee}, Guest={old_guest}, Unknown={old_unknown}")
    logger.info(f"New labels: Chaffee={new_chaffee}, Guest={new_guest}, Unknown={new_unknown}")
    logger.info(f"Changes: {changes} segments ({changes/len(segments)*100:.1f}%)")
    logger.info("="*80)
    
    # Update database
    if not dry_run:
        logger.info("Updating database...")
        update_count = 0
        
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                for idx, seg in enumerate(segments, 1):
                    if idx % 100 == 0:
                        logger.info(f"  Updating: {idx}/{len(segments)} segments ({idx/len(segments)*100:.1f}%)")
                    
                    if seg['speaker_label'] != seg['new_speaker']:
                        cur.execute("""
                            UPDATE segments
                            SET speaker_label = %s
                            WHERE id = %s
                        """, (seg['new_speaker'], seg['id']))
                        update_count += 1
            
            conn.commit()
        
        logger.info(f"✅ Updated {update_count} segments in database")
    else:
        logger.info("[DRY RUN] No changes made to database")
    
    # Show sample changes
    logger.info("\nSample changes:")
    sample_changes = [s for s in segments if s['speaker_label'] != s['new_speaker']][:10]
    for seg in sample_changes:
        logger.info(f"  Video {seg['video_id']}: {seg['speaker_label']} → {seg['new_speaker']} (sim: {seg['similarity']:.3f})")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="Regenerate speaker labels with improved identification")
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without updating database')
    
    args = parser.parse_args()
    
    # Initialize database
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not set!")
        return 1
    
    db = SegmentsDatabase(db_url)
    
    # Regenerate labels
    return regenerate_labels(db, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
