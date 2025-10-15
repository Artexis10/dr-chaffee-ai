#!/usr/bin/env python3
"""
Daily Ingestion Wrapper with Error Handling and Notifications

This wrapper:
- Runs the ingestion script
- Handles errors gracefully
- Sends notifications on success/failure
- Logs detailed metrics
- Timeout protection (10h before Render's 12h limit)
- Progress monitoring
- Graceful shutdown
"""
import os
import sys
import logging
import subprocess
import signal
import argparse
import time
from datetime import datetime, timedelta
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

# Global state for timeout handling
process = None
start_time = None
timeout_triggered = False


def parse_duration(duration_str: str) -> int:
    """Parse duration string like '10h', '30m', '2h30m' to seconds"""
    total_seconds = 0
    current_num = ''
    
    for char in duration_str:
        if char.isdigit():
            current_num += char
        elif char == 'h':
            total_seconds += int(current_num) * 3600
            current_num = ''
        elif char == 'm':
            total_seconds += int(current_num) * 60
            current_num = ''
        elif char == 's':
            total_seconds += int(current_num)
            current_num = ''
    
    return total_seconds


def timeout_handler(signum, frame):
    """Handle timeout - kill process gracefully"""
    global process, timeout_triggered
    timeout_triggered = True
    
    logger.error("="*80)
    logger.error("⏰ TIMEOUT REACHED - Stopping gracefully")
    logger.error("="*80)
    logger.error("💡 This job has been running too long.")
    logger.error("💡 Consider processing this content locally and syncing the database.")
    
    if process:
        logger.info("Sending SIGTERM to child process...")
        try:
            process.terminate()
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            logger.warning("Process didn't terminate, sending SIGKILL...")
            process.kill()
    
    sys.exit(124)  # Exit code 124 = timeout (like GNU timeout command)


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


def run_ingestion(args):
    """Run the ingestion script with safety measures"""
    global process, start_time
    
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info(f"Daily ingestion started at {start_time}")
    logger.info(f"Max runtime: {args.max_runtime}")
    logger.info(f"Days back: {args.days_back}")
    logger.info("=" * 80)
    
    # Setup timeout handler
    max_seconds = parse_duration(args.max_runtime)
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(max_seconds)
    logger.info(f"⏰ Timeout protection enabled: {max_seconds}s ({args.max_runtime})")
    
    # Get script path
    script_path = Path(__file__).parent / "ingest_youtube_enhanced.py"
    if not script_path.exists():
        # Try alternative name
        script_path = Path(__file__).parent / "ingest_youtube_enhanced_asr.py"
    
    if not script_path.exists():
        logger.error(f"❌ Ingestion script not found at {script_path}")
        return 1
    
    # Get channel URL from environment or args
    channel_url = args.channel_url or os.getenv('YOUTUBE_CHANNEL_URL', 'https://www.youtube.com/@anthonychaffeemd')
    
    # Build command
    cmd = [
        sys.executable,
        str(script_path),
        "--channel-url", channel_url,
        "--days-back", str(args.days_back),
        "--skip-existing"
    ]
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    try:
        # Run ingestion with progress monitoring
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor progress
        stdout_lines = []
        stderr_lines = []
        last_progress_time = time.time()
        
        logger.info("📊 Monitoring progress...")
        
        # Read output in real-time
        while True:
            # Check if process finished
            if process.poll() is not None:
                break
            
            # Read available output
            try:
                import select
                ready = select.select([process.stdout, process.stderr], [], [], 1.0)[0]
                
                for stream in ready:
                    line = stream.readline()
                    if line:
                        if stream == process.stdout:
                            stdout_lines.append(line)
                            logger.info(line.rstrip())
                        else:
                            stderr_lines.append(line)
                            logger.warning(line.rstrip())
                        last_progress_time = time.time()
            except:
                # Fallback for Windows (no select on pipes)
                time.sleep(1)
            
            # Check elapsed time and log progress
            elapsed = time.time() - start_time.timestamp()
            if elapsed % 600 < 1:  # Every 10 minutes
                elapsed_str = str(timedelta(seconds=int(elapsed)))
                remaining = max_seconds - elapsed
                remaining_str = str(timedelta(seconds=int(remaining)))
                logger.info(f"⏱️  Elapsed: {elapsed_str} | Remaining: {remaining_str}")
            
            # Warn if approaching timeout
            if elapsed > max_seconds * 0.9:  # 90% of max time
                logger.warning("⚠️  Approaching timeout limit (90% of max runtime)")
        
        # Get remaining output
        remaining_stdout, remaining_stderr = process.communicate()
        if remaining_stdout:
            stdout_lines.extend(remaining_stdout.splitlines(keepends=True))
        if remaining_stderr:
            stderr_lines.extend(remaining_stderr.splitlines(keepends=True))
        
        # Create result object
        class Result:
            def __init__(self, returncode, stdout, stderr):
                self.returncode = returncode
                self.stdout = ''.join(stdout)
                self.stderr = ''.join(stderr)
        
        result = Result(process.returncode, stdout_lines, stderr_lines)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Cancel timeout alarm
        signal.alarm(0)
        
        # Check result
        if result.returncode == 0:
            logger.info("=" * 80)
            logger.info(f"✅ Daily ingestion completed successfully")
            logger.info(f"Duration: {duration}")
            logger.info(f"Average speed: {duration.total_seconds() / 3600:.2f}h processing time")
            logger.info("=" * 80)
            
            # Send success notification
            send_notification(
                "Dr. Chaffee Daily Ingestion - Success",
                f"Completed in {duration}\n\nCheck logs for details.",
                success=True
            )
            return 0
        elif result.returncode == 124:
            # Timeout exit code
            logger.error("=" * 80)
            logger.error(f"⏰ Daily ingestion timed out")
            logger.error(f"Duration: {duration}")
            logger.error("💡 Consider processing locally and syncing database")
            logger.error("=" * 80)
            
            send_notification(
                "Dr. Chaffee Daily Ingestion - Timeout",
                f"Process exceeded {args.max_runtime} timeout\n\nConsider local processing.",
                success=False
            )
            return 124
        else:
            logger.error("=" * 80)
            logger.error(f"❌ Daily ingestion failed with exit code {result.returncode}")
            logger.error(f"Duration: {duration}")
            logger.error("=" * 80)
            
            # Send failure notification
            error_msg = result.stderr[-500:] if result.stderr else "No error details"
            send_notification(
                "Dr. Chaffee Daily Ingestion - Failed",
                f"Exit code: {result.returncode}\n\n{error_msg}",
                success=False
            )
            return result.returncode
            
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        if process:
            logger.info("Terminating child process...")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        return 130  # Standard exit code for SIGINT
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        send_notification(
            "Dr. Chaffee Daily Ingestion - Error",
            f"Unexpected error: {str(e)}",
            success=False
        )
        return 1


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description='Daily ingestion wrapper with timeout protection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: 2 days back, 10 hour timeout
  python daily_ingest_wrapper.py
  
  # Custom timeout
  python daily_ingest_wrapper.py --max-runtime 8h
  
  # More days back (careful with timeout!)
  python daily_ingest_wrapper.py --days-back 7 --max-runtime 10h
  
  # Custom channel
  python daily_ingest_wrapper.py --channel-url https://youtube.com/@example
        """
    )
    
    parser.add_argument(
        '--days-back',
        type=int,
        default=2,
        help='Number of days back to check for new videos (default: 2)'
    )
    
    parser.add_argument(
        '--max-runtime',
        type=str,
        default='10h',
        help='Maximum runtime before timeout (e.g., 10h, 8h30m, 600m). Default: 10h (2h before Render limit)'
    )
    
    parser.add_argument(
        '--channel-url',
        type=str,
        default=None,
        help='YouTube channel URL (default: from YOUTUBE_CHANNEL_URL env var)'
    )
    
    args = parser.parse_args()
    
    # Validate max-runtime
    try:
        max_seconds = parse_duration(args.max_runtime)
        if max_seconds > 12 * 3600:
            logger.warning(f"⚠️  Max runtime {args.max_runtime} exceeds Render's 12h limit")
            logger.warning("⚠️  Setting to 10h for safety")
            args.max_runtime = '10h'
    except Exception as e:
        logger.error(f"❌ Invalid max-runtime format: {args.max_runtime}")
        logger.error(f"   Use format like: 10h, 8h30m, 600m")
        return 1
    
    # Run ingestion
    return run_ingestion(args)


if __name__ == '__main__':
    sys.exit(main())
