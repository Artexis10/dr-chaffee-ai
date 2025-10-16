#!/usr/bin/env python3
"""
Bootstrap Chaffee voice profile on Render if it doesn't exist
Run this before the daily ingestion cron job
"""
import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Seed URLs for building Chaffee profile (pure monologue videos)
CHAFFEE_SEED_URLS = [
    "https://www.youtube.com/watch?v=zw2c7s7NcqI",
    "https://www.youtube.com/watch?v=jLb5XUITtHQ",
    "https://www.youtube.com/watch?v=1EojwUJIdtc",
    "https://www.youtube.com/watch?v=tYWGVs2ax-A",
    "https://www.youtube.com/watch?v=zl_QM65_TpA",
    "https://www.youtube.com/watch?v=D3v8c2SM-wI",
    "https://www.youtube.com/watch?v=CrI-qZnZjnw",
    "https://www.youtube.com/watch?v=TR93yJqX7jE",
    "https://www.youtube.com/watch?v=naRYI5Q-uYw",
    "https://www.youtube.com/watch?v=4suBVks9UN0",
]

def check_profile_exists():
    """Check if Chaffee voice profile exists"""
    voices_dir = Path(os.getenv('VOICES_DIR', 'voices'))
    profile_path = voices_dir / "chaffee.json"
    return profile_path.exists()

def build_profile():
    """Build Chaffee voice profile from seed videos"""
    logger.info("🔧 Building Chaffee voice profile from seed videos...")
    logger.info(f"Using {len(CHAFFEE_SEED_URLS)} seed videos")
    
    # Import here to avoid loading if not needed
    from scripts.ingest_youtube import EnhancedYouTubeIngester, IngestionConfig
    
    # Create config for profile building
    config = IngestionConfig(
        source='yt-dlp',
        from_url=CHAFFEE_SEED_URLS,
        setup_chaffee=True,
        overwrite_profile=True,
        limit=10,  # Use first 10 videos (faster, still good quality)
        voices_dir=os.getenv('VOICES_DIR', 'voices'),
        chaffee_min_sim=0.62,
    )
    
    # Build profile
    ingester = EnhancedYouTubeIngester(config)
    success = ingester.setup_chaffee_profile(
        audio_sources=CHAFFEE_SEED_URLS[:10],
        overwrite=True
    )
    
    if success:
        logger.info("✅ Voice profile built successfully!")
        return True
    else:
        logger.error("❌ Failed to build voice profile")
        return False

def main():
    """Main bootstrap function"""
    logger.info("=" * 60)
    logger.info("Voice Profile Bootstrap")
    logger.info("=" * 60)
    
    if check_profile_exists():
        logger.info("✅ Voice profile already exists - skipping bootstrap")
        return 0
    
    logger.info("⚠️  Voice profile not found - building from seed videos...")
    logger.info("This will take ~15-20 minutes on first run")
    
    success = build_profile()
    
    if success:
        logger.info("=" * 60)
        logger.info("✅ Bootstrap complete! Profile ready for ingestion")
        logger.info("=" * 60)
        return 0
    else:
        logger.error("=" * 60)
        logger.error("❌ Bootstrap failed!")
        logger.error("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
