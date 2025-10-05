#!/usr/bin/env python3
"""
Regenerate Chaffee voice profile with current embedding model

This script extracts audio embeddings from known Chaffee-only videos
and creates a new voice profile compatible with the current embedding model.
"""
import os
import sys
import json
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend' / 'scripts'))

from common.voice_enrollment_optimized import VoiceEnrollmentManager
from common.embeddings import EmbeddingGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def regenerate_profile():
    """Regenerate Chaffee voice profile"""
    
    # Check current embedding dimensions
    embedding_gen = EmbeddingGenerator()
    current_dims = embedding_gen.get_embedding_dimension()
    logger.info(f"Current embedding model: {embedding_gen.model_name}")
    logger.info(f"Current embedding dimensions: {current_dims}")
    
    # Check existing profile
    profile_path = Path('voices/chaffee.json')
    if profile_path.exists():
        with open(profile_path) as f:
            old_profile = json.load(f)
            old_dims = len(old_profile['centroid'])
            logger.info(f"Existing profile dimensions: {old_dims}")
            
            if old_dims == current_dims:
                logger.info("✅ Profile dimensions match! No regeneration needed.")
                return
            else:
                logger.warning(f"⚠️  Dimension mismatch: {old_dims} vs {current_dims}")
                logger.info("Backing up old profile...")
                backup_path = profile_path.with_suffix('.json.bak')
                profile_path.rename(backup_path)
                logger.info(f"Backed up to: {backup_path}")
    
    # Get seed videos for Chaffee - try multiple seed files
    seed_files = [
        Path('chaffee_seed_urls.json'),
        Path('chaffee_voice_seeds.json')
    ]
    
    seeds = None
    for seed_file in seed_files:
        if seed_file.exists():
            logger.info(f"Using seed file: {seed_file}")
            with open(seed_file) as f:
                seeds = json.load(f)
            break
    
    if not seeds:
        logger.error("No seed file found!")
        logger.info("Please create chaffee_seed_urls.json or chaffee_voice_seeds.json")
        return
    
    # Extract video IDs from URLs (handle both file formats)
    urls = []
    
    # Format 1: chaffee_seed_urls.json (list of sources)
    if 'sources' in seeds:
        urls = [source['url'] for source in seeds['sources']]
    # Format 2: chaffee_voice_seeds.json (nested structure)
    elif 'chaffee' in seeds:
        urls = seeds['chaffee'].get('urls', [])
    
    if not urls:
        logger.error("No URLs found in seed file")
        return
    
    # Extract video IDs from YouTube URLs
    video_ids = []
    for url in urls:
        if 'watch?v=' in url:
            video_id = url.split('watch?v=')[1].split('&')[0]
            video_ids.append(video_id)
        elif 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[1].split('?')[0]
            video_ids.append(video_id)
    
    logger.info(f"Found {len(video_ids)} seed videos")
    
    # Initialize voice enrollment manager
    manager = VoiceEnrollmentManager(voices_dir='voices')
    
    # Enroll from videos
    logger.info("Extracting embeddings from seed videos...")
    success_count = 0
    
    for video_id in video_ids[:5]:  # Use first 5 videos
        logger.info(f"Processing video: {video_id}")
        try:
            # Download and extract embeddings
            # This will use the current embedding model
            result = manager.enroll_from_youtube(
                speaker_name='chaffee',
                video_id=video_id,
                force=True
            )
            if result:
                success_count += 1
                logger.info(f"✅ Successfully enrolled from {video_id}")
        except Exception as e:
            logger.error(f"Failed to enroll from {video_id}: {e}")
    
    if success_count > 0:
        logger.info(f"✅ Profile regenerated successfully using {success_count} videos")
        logger.info(f"Profile saved to: {profile_path}")
        
        # Verify new profile
        with open(profile_path) as f:
            new_profile = json.load(f)
            new_dims = len(new_profile['centroid'])
            logger.info(f"New profile dimensions: {new_dims}")
            
            if new_dims == current_dims:
                logger.info("✅ Profile dimensions now match embedding model!")
            else:
                logger.error(f"❌ Dimension mismatch persists: {new_dims} vs {current_dims}")
    else:
        logger.error("❌ Failed to regenerate profile - no successful enrollments")

if __name__ == '__main__':
    regenerate_profile()
