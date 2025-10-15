#!/usr/bin/env python3
"""
Daily Ingestion Wrapper with Error Handling and Notifications

This wrapper:
- Runs the ingestion script
- Handles errors gracefully
- Sends notifications on success/failure
- Logs detailed metrics
"""
import os
import sys
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Setup logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "daily_ingest.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def send_notification(subject: str, message: str, success: bool = True):
    """Send notification (email, webhook, etc.)"""
    # Example: Send to webhook
    webhook_url = os.getenv('NOTIFICATION_WEBHOOK_URL')
    if webhook_url:
        try:
            import requests
            emoji = "✅" if success else "❌"
            requests.post(webhook_url, json={
                "text": f"{emoji} {subject}\n\n{message}"
            }, timeout=10)
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
    
    # Example: Send email
    email_to = os.getenv('NOTIFICATION_EMAIL')
    if email_to:
        try:
            # Use sendmail, mailgun, or other email service
            pass
        except Exception as e:
            logger.warning(f"Failed to send email: {e}")


def run_ingestion():
    """Run the ingestion script"""
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info(f"Daily ingestion started at {start_time}")
    logger.info("=" * 80)
    
    # Get script path
    script_path = Path(__file__).parent / "ingest_youtube_enhanced_asr.py"
    
    # Get channel URL from environment
    channel_url = os.getenv('YOUTUBE_CHANNEL_URL', 'https://www.youtube.com/@anthonychaffeemd')
    
    # Build command
    cmd = [
        sys.executable,
        str(script_path),
        "--channel-url", channel_url,
        "--days-back", "2",
        "--skip-existing"
    ]
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    try:
        # Run ingestion
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=28800  # 8 hour timeout
        )
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Log output
        if result.stdout:
            logger.info("STDOUT:\n" + result.stdout)
        if result.stderr:
            logger.warning("STDERR:\n" + result.stderr)
        
        # Check result
        if result.returncode == 0:
            logger.info("=" * 80)
            logger.info(f"✅ Daily ingestion completed successfully")
            logger.info(f"Duration: {duration}")
            logger.info("=" * 80)
            
            # Send success notification
            send_notification(
                "Dr. Chaffee Daily Ingestion - Success",
                f"Completed in {duration}\n\nCheck logs for details.",
                success=True
            )
            return 0
        else:
            logger.error("=" * 80)
            logger.error(f"❌ Daily ingestion failed with exit code {result.returncode}")
            logger.error(f"Duration: {duration}")
            logger.error("=" * 80)
            
            # Send failure notification
            send_notification(
                "Dr. Chaffee Daily Ingestion - Failed",
                f"Exit code: {result.returncode}\n\n{result.stderr[:500]}",
                success=False
            )
            return result.returncode
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Ingestion timed out after 8 hours")
        send_notification(
            "Dr. Chaffee Daily Ingestion - Timeout",
            "Process exceeded 8 hour timeout",
            success=False
        )
        return 1
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        send_notification(
            "Dr. Chaffee Daily Ingestion - Error",
            f"Unexpected error: {str(e)}",
            success=False
        )
        return 1


if __name__ == '__main__':
    sys.exit(run_ingestion())
