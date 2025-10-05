#!/usr/bin/env python3
"""
Automatic yt-dlp version checker and updater.

Ensures yt-dlp is up-to-date before ingestion to avoid YouTube signature issues.
"""
import subprocess
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class YtDlpUpdater:
    """Manages yt-dlp version checking and updates."""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.version_cache_file = self.cache_dir / "ytdlp_version_check.json"
        self.check_interval_hours = 24  # Check once per day
    
    def should_check_update(self) -> bool:
        """Check if we should check for updates (rate limiting)."""
        if not self.version_cache_file.exists():
            return True
        
        try:
            with open(self.version_cache_file, 'r') as f:
                cache = json.load(f)
            
            last_check = datetime.fromisoformat(cache.get('last_check', '2000-01-01'))
            next_check = last_check + timedelta(hours=self.check_interval_hours)
            
            return datetime.now() >= next_check
        except Exception:
            return True
    
    def get_current_version(self) -> str:
        """Get currently installed yt-dlp version."""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'yt_dlp', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return "unknown"
        except Exception as e:
            logger.warning(f"Could not get yt-dlp version: {e}")
            return "unknown"
    
    def check_for_updates(self) -> tuple[bool, str]:
        """
        Check if yt-dlp has updates available.
        
        Returns:
            (has_updates, current_version)
        """
        current_version = self.get_current_version()
        
        try:
            # Check for updates using pip
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'list', '--outdated', '--format=json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                outdated = json.loads(result.stdout)
                for package in outdated:
                    if package['name'] in ['yt-dlp', 'yt_dlp']:
                        logger.info(f"yt-dlp update available: {package['version']} → {package['latest_version']}")
                        return True, current_version
            
            return False, current_version
        except Exception as e:
            logger.warning(f"Could not check for yt-dlp updates: {e}")
            return False, current_version
    
    def update_ytdlp(self, use_nightly: bool = False) -> bool:
        """
        Update yt-dlp to latest version.
        
        Args:
            use_nightly: If True, install nightly build from GitHub
        
        Returns:
            True if update successful
        """
        try:
            if use_nightly:
                logger.info("Installing yt-dlp nightly build from GitHub...")
                cmd = [
                    sys.executable, '-m', 'pip', 'install',
                    '--upgrade', '--force-reinstall',
                    'https://github.com/yt-dlp/yt-dlp/archive/master.tar.gz'
                ]
            else:
                logger.info("Updating yt-dlp to latest stable version...")
                cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', 'yt-dlp']
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                new_version = self.get_current_version()
                logger.info(f"✅ yt-dlp updated successfully to version {new_version}")
                self._update_cache()
                return True
            else:
                logger.error(f"Failed to update yt-dlp: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error updating yt-dlp: {e}")
            return False
    
    def _update_cache(self):
        """Update the version check cache."""
        try:
            cache = {
                'last_check': datetime.now().isoformat(),
                'version': self.get_current_version()
            }
            with open(self.version_cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not update cache: {e}")
    
    def auto_update_if_needed(self, force: bool = False, use_nightly: bool = False) -> bool:
        """
        Automatically check and update yt-dlp if needed.
        
        Args:
            force: Force update check even if recently checked
            use_nightly: Use nightly build instead of stable
        
        Returns:
            True if yt-dlp is up-to-date or was successfully updated
        """
        if not force and not self.should_check_update():
            logger.debug("yt-dlp version check skipped (recently checked)")
            return True
        
        logger.info("Checking yt-dlp version...")
        current_version = self.get_current_version()
        logger.info(f"Current yt-dlp version: {current_version}")
        
        if use_nightly:
            logger.info("Nightly build requested - updating...")
            return self.update_ytdlp(use_nightly=True)
        
        has_updates, _ = self.check_for_updates()
        
        if has_updates:
            logger.warning("⚠️  yt-dlp update available - updating automatically...")
            return self.update_ytdlp()
        else:
            logger.info("✅ yt-dlp is up-to-date")
            self._update_cache()
            return True


def check_and_update_ytdlp(force: bool = False, use_nightly: bool = False) -> bool:
    """
    Convenience function to check and update yt-dlp.
    
    Args:
        force: Force update check
        use_nightly: Use nightly build
    
    Returns:
        True if yt-dlp is ready to use
    """
    updater = YtDlpUpdater()
    return updater.auto_update_if_needed(force=force, use_nightly=use_nightly)


if __name__ == "__main__":
    # Test the updater
    logging.basicConfig(level=logging.INFO)
    
    import argparse
    parser = argparse.ArgumentParser(description="Update yt-dlp")
    parser.add_argument('--force', action='store_true', help='Force update check')
    parser.add_argument('--nightly', action='store_true', help='Install nightly build')
    args = parser.parse_args()
    
    success = check_and_update_ytdlp(force=args.force, use_nightly=args.nightly)
    sys.exit(0 if success else 1)
