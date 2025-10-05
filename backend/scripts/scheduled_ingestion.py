#!/usr/bin/env python3
"""
Scheduled incremental ingestion for production.

Runs lightweight ingestion of new videos only (1-2 per day).
CPU-friendly for production environments without GPU.
"""
import os
import sys
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


def run_incremental_ingestion():
    """Run incremental ingestion for new videos only."""
    logger.info("=" * 80)
    logger.info("SCHEDULED INCREMENTAL INGESTION")
    logger.info("=" * 80)
    logger.info(f"Started at: {datetime.now()}")
    
    # Get configuration from environment
    limit = int(os.getenv('INGESTION_LIMIT', '5'))
    source = os.getenv('INGESTION_SOURCE', 'yt-dlp')
    
    logger.info(f"Source: {source}")
    logger.info(f"Limit: {limit} unprocessed videos")
    logger.info("Mode: CPU-only (incremental)")
    
    # Build command
    cmd = [
        sys.executable,
        'backend/scripts/ingest_youtube.py',
        '--source', source,
        '--limit', str(limit),
        '--limit-unprocessed',  # Only process new videos
        '--skip-shorts',  # Skip YouTube Shorts
        '--newest-first',  # Process newest first
    ]
    
    logger.info(f"Running: {' '.join(cmd)}")
    
    # Run ingestion
    import subprocess
    try:
        result = subprocess.run(
            cmd,
            capture_output=False,  # Stream output
            text=True,
            timeout=14400  # 4 hour timeout (CPU is slow)
        )
        
        if result.returncode == 0:
            logger.info("✅ Incremental ingestion completed successfully")
        else:
            logger.error(f"❌ Ingestion failed with exit code {result.returncode}")
    except subprocess.TimeoutExpired:
        logger.error("❌ Ingestion timed out after 4 hours")
    except Exception as e:
        logger.error(f"❌ Ingestion error: {e}")
    
    logger.info(f"Completed at: {datetime.now()}")
    logger.info("=" * 80)


def main():
    """Main scheduler function."""
    # Check if in production mode
    if os.getenv('API_ONLY_MODE', '').lower() == 'true':
        logger.error("❌ API_ONLY_MODE is enabled - ingestion disabled")
        logger.error("Set API_ONLY_MODE=false to enable scheduled ingestion")
        sys.exit(1)
    
    # Get schedule from environment
    schedule = os.getenv('INGESTION_SCHEDULE', '0 2 * * *')  # Default: 2 AM daily
    
    logger.info("=" * 80)
    logger.info("SCHEDULED INGESTION SERVICE")
    logger.info("=" * 80)
    logger.info(f"Schedule: {schedule} (cron format)")
    logger.info(f"Limit: {os.getenv('INGESTION_LIMIT', '5')} videos per run")
    logger.info(f"Source: {os.getenv('INGESTION_SOURCE', 'yt-dlp')}")
    logger.info("Mode: CPU-only (incremental)")
    logger.info("")
    logger.info("This will process 1-2 new videos per day on CPU.")
    logger.info("For bulk processing, use local GPU machine.")
    logger.info("=" * 80)
    
    # Create scheduler
    scheduler = BlockingScheduler()
    
    # Add job
    scheduler.add_job(
        run_incremental_ingestion,
        CronTrigger.from_crontab(schedule),
        id='incremental_ingestion',
        name='Incremental Video Ingestion',
        replace_existing=True
    )
    
    # Run immediately on startup (optional)
    if os.getenv('RUN_ON_STARTUP', '').lower() == 'true':
        logger.info("Running ingestion on startup...")
        run_incremental_ingestion()
    
    logger.info("Scheduler started. Press Ctrl+C to exit.")
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
        sys.exit(0)


if __name__ == '__main__':
    main()
