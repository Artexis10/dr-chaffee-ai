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


def get_segment_count(db: SegmentsDatabase):
    """Get total count of segments with embeddings"""
    query = """
    SELECT COUNT(*) FROM segments WHERE embedding IS NOT NULL
    """
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchone()[0]


def get_video_ids_with_embeddings(db: SegmentsDatabase):
    """Get list of all video IDs that have segments with embeddings"""
    query = """
    SELECT DISTINCT video_id 
    FROM segments 
    WHERE embedding IS NOT NULL
    ORDER BY video_id
    """
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return [row[0] for row in cur.fetchall()]


def get_segments_for_video(db: SegmentsDatabase, video_id: str):
    """Get all segments for a specific video (memory-safe per-video loading)"""
    query = """
    SELECT id, video_id, speaker_label, voice_embedding, start_sec, end_sec
    FROM segments
    WHERE video_id = %s AND voice_embedding IS NOT NULL
    ORDER BY start_sec
    """
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (video_id,))
            results = cur.fetchall()
    
    segments = []
    for row in results:
        # Parse voice_embedding from JSON if it's a string
        voice_emb = row[3]
        if isinstance(voice_emb, str):
            import json
            voice_emb = json.loads(voice_emb)
        emb = np.array(voice_emb) if voice_emb else None
        
        segments.append({
            'id': row[0],
            'video_id': row[1],
            'speaker_label': row[2],
            'embedding': emb,  # This is now voice_embedding (192-dim)
            'start_sec': float(row[4]),
            'end_sec': float(row[5])
        })
    
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


def smooth_speaker_labels(segments):
    """
    Post-process to smooth isolated misidentifications within a single video
    
    Args:
        segments: List of segments for a single video
    
    Returns:
        int: Number of segments smoothed
    """
    smoothed_count = 0
    
    if len(segments) < 3:
        return 0
    
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


def process_video_batch(db: SegmentsDatabase, video_ids: list, chaffee_profile, enrollment):
    """Process a batch of videos and return segments with new labels"""
    all_segments = []
    
    for video_id in video_ids:
        segments = get_segments_for_video(db, video_id)
        if not segments:
            continue
        
        # Re-identify speakers with temporal context
        prev_speaker = None
        for seg in segments:
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
            prev_speaker = new_speaker
        
        # Apply smoothing per video
        smooth_speaker_labels(segments)
        all_segments.extend(segments)
    
    return all_segments


def regenerate_labels(db: SegmentsDatabase, dry_run=False, batch_size=50):
    """Regenerate speaker labels for all segments using batch processing"""
    
    # Load Chaffee profile
    voices_dir = Path(os.getenv('VOICES_DIR', 'voices'))
    enrollment = VoiceEnrollment(voices_dir=str(voices_dir))
    chaffee_profile = enrollment.load_profile('chaffee')
    
    if not chaffee_profile:
        logger.error("Chaffee profile not found!")
        return 1
    
    logger.info(f"Loaded Chaffee profile from {voices_dir / 'chaffee.json'}")
    
    # Get video IDs and total count
    video_ids = get_video_ids_with_embeddings(db)
    total_segments = get_segment_count(db)
    
    if not video_ids:
        logger.error("No videos with embeddings found!")
        return 1
    
    logger.info(f"Processing {len(video_ids)} videos with {total_segments} segments...")
    logger.info(f"Batch size: {batch_size} videos (memory-safe processing)")
    
    # Process in batches
    total_changes = 0
    total_smoothed = 0
    all_stats = {'old_chaffee': 0, 'old_guest': 0, 'old_unknown': 0,
                 'new_chaffee': 0, 'new_guest': 0, 'new_unknown': 0}
    sample_changes = []
    processed_segments = 0
    
    for batch_idx in range(0, len(video_ids), batch_size):
        batch_video_ids = video_ids[batch_idx:batch_idx + batch_size]
        logger.info(f"\nProcessing batch {batch_idx//batch_size + 1}/{(len(video_ids) + batch_size - 1)//batch_size} ({len(batch_video_ids)} videos)...")
        
        # Process batch
        segments = process_video_batch(db, batch_video_ids, chaffee_profile, enrollment)
        
        if not segments:
            continue
        
        # Collect statistics
        old_chaffee = sum(1 for s in segments if s['speaker_label'] == 'Chaffee')
        old_guest = sum(1 for s in segments if s['speaker_label'] and 'GUEST' in s['speaker_label'].upper())
        old_unknown = sum(1 for s in segments if not s['speaker_label'] or s['speaker_label'] == 'Unknown')
        
        new_chaffee = sum(1 for s in segments if s['new_speaker'] == 'Chaffee')
        new_guest = sum(1 for s in segments if s['new_speaker'] == 'GUEST')
        new_unknown = sum(1 for s in segments if s['new_speaker'] == 'Unknown')
        
        changes = sum(1 for s in segments if s['speaker_label'] != s['new_speaker'])
        smoothed = sum(1 for s in segments if s.get('smoothed', False))
        
        all_stats['old_chaffee'] += old_chaffee
        all_stats['old_guest'] += old_guest
        all_stats['old_unknown'] += old_unknown
        all_stats['new_chaffee'] += new_chaffee
        all_stats['new_guest'] += new_guest
        all_stats['new_unknown'] += new_unknown
        total_changes += changes
        total_smoothed += smoothed
        processed_segments += len(segments)
        
        # Collect sample changes (limit to 10 total)
        if len(sample_changes) < 10:
            batch_samples = [s for s in segments if s['speaker_label'] != s['new_speaker']][:10 - len(sample_changes)]
            sample_changes.extend(batch_samples)
        
        logger.info(f"  Batch: {len(segments)} segments, {changes} changes, {smoothed} smoothed")
        
        # Update database for this batch
        if not dry_run and changes > 0:
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    for seg in segments:
                        if seg['speaker_label'] != seg['new_speaker']:
                            cur.execute("""
                                UPDATE segments
                                SET speaker_label = %s
                                WHERE id = %s
                            """, (seg['new_speaker'], seg['id']))
                    conn.commit()
        
        # Clear batch from memory
        del segments
    
    # Show final statistics
    logger.info("\n" + "="*80)
    logger.info("SPEAKER LABEL CHANGES")
    logger.info("="*80)
    logger.info(f"Total segments processed: {processed_segments}")
    logger.info(f"Old labels: Chaffee={all_stats['old_chaffee']}, Guest={all_stats['old_guest']}, Unknown={all_stats['old_unknown']}")
    logger.info(f"New labels: Chaffee={all_stats['new_chaffee']}, Guest={all_stats['new_guest']}, Unknown={all_stats['new_unknown']}")
    logger.info(f"Changes: {total_changes} segments ({total_changes/processed_segments*100:.1f}%)")
    logger.info(f"Smoothed: {total_smoothed} segments")
    logger.info("="*80)
    
    if dry_run:
        logger.info("[DRY RUN] No changes made to database")
    else:
        logger.info(f"✅ Updated {total_changes} segments in database")
    
    # Show sample changes
    logger.info("\nSample changes:")
    for seg in sample_changes:
        logger.info(f"  Video {seg['video_id']}: {seg['speaker_label']} → {seg['new_speaker']} (sim: {seg['similarity']:.3f})")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="Regenerate speaker labels with improved identification")
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without updating database')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Number of videos to process per batch (default: 50, increase for more speed/RAM usage)')
    
    args = parser.parse_args()
    
    # Initialize database
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not set!")
        return 1
    
    db = SegmentsDatabase(db_url)
    
    # Regenerate labels
    return regenerate_labels(db, dry_run=args.dry_run, batch_size=args.batch_size)


if __name__ == "__main__":
    sys.exit(main())
