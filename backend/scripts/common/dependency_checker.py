#!/usr/bin/env python3
"""
Automatic dependency checker and installer.

Ensures critical dependencies are installed before running ingestion.
"""
import os
import subprocess
import sys
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class DependencyChecker:
    """Checks and installs missing critical dependencies."""
    
    # Critical dependencies that must be present
    # Note: In production (API_ONLY_MODE), only a subset is needed
    CRITICAL_DEPS = {
        # Core transcription (skip in production)
        'faster_whisper': 'faster-whisper>=1.0.2',
        # Removed whisperx - using faster-whisper + asr_diarize_v4 directly
        
        # Speaker identification (skip in production)
        'pyannote.audio': 'pyannote.audio>=4.0.0',  # v4 with community pipeline
        'soundfile': 'soundfile>=0.12.1',
        
        # ML/AI (always needed)
        'torch': 'torch>=2.2.0,<2.9.0',
        'transformers': 'transformers==4.33.2',
        
        # YouTube downloads (skip in production)
        'yt_dlp': 'yt-dlp>=2023.11.16',
        
        # Database (always needed)
        'psycopg2': 'psycopg2-binary>=2.9.9',
    }
    
    # Production-only dependencies (API serving)
    PRODUCTION_ONLY_DEPS = {
        'torch': 'torch>=2.2.0,<2.9.0',
        'transformers': 'transformers==4.33.2',
        'psycopg2': 'psycopg2-binary>=2.9.9',
    }
    
    # Optional dependencies (warn but don't fail)
    OPTIONAL_DEPS = {
        'speechbrain': 'speechbrain>=0.5.16',
    }
    
    def __init__(self, auto_install: bool = True):
        """
        Args:
            auto_install: If True, automatically install missing dependencies
        """
        self.auto_install = auto_install
    
    def check_import(self, module_name: str) -> bool:
        """Check if a module can be imported."""
        try:
            __import__(module_name)
            return True
        except (ImportError, AttributeError) as e:
            # AttributeError can occur with incompatible dependencies (e.g., speechbrain + torchaudio)
            logger.debug(f"Import check failed for {module_name}: {e}")
            return False
    
    def check_all_dependencies(self) -> Tuple[List[str], List[str]]:
        """
        Check all dependencies.
        
        Returns:
            (missing_critical, missing_optional)
        """
        missing_critical = []
        missing_optional = []
        
        # Check if in production mode (API-only)
        is_production = os.getenv('API_ONLY_MODE', '').lower() == 'true'
        
        if is_production:
            logger.info("Production mode detected - checking minimal dependencies...")
            deps_to_check = self.PRODUCTION_ONLY_DEPS
        else:
            logger.info("Checking critical dependencies...")
            deps_to_check = self.CRITICAL_DEPS
        
        for module, package in deps_to_check.items():
            if not self.check_import(module):
                logger.warning(f"❌ Missing critical dependency: {package}")
                missing_critical.append(package)
            else:
                logger.debug(f"✅ {module} available")
        
        logger.info("Checking optional dependencies...")
        for module, package in self.OPTIONAL_DEPS.items():
            if not self.check_import(module):
                logger.info(f"⚠️  Optional dependency not installed: {package}")
                missing_optional.append(package)
            else:
                logger.debug(f"✅ {module} available")
        
        return missing_critical, missing_optional
    
    def install_package(self, package: str) -> bool:
        """
        Install a package using pip.
        
        Args:
            package: Package specification (e.g., 'faster-whisper>=1.0.2')
        
        Returns:
            True if installation successful
        """
        try:
            logger.info(f"Installing {package}...")
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes max
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Successfully installed {package}")
                return True
            else:
                logger.error(f"Failed to install {package}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error installing {package}: {e}")
            return False
    
    def auto_fix_dependencies(self) -> bool:
        """
        Automatically check and install missing dependencies.
        
        Returns:
            True if all critical dependencies are available
        """
        missing_critical, missing_optional = self.check_all_dependencies()
        
        # Handle critical dependencies
        if missing_critical:
            if not self.auto_install:
                logger.error("❌ Missing critical dependencies!")
                logger.error("Install with: pip install " + " ".join(missing_critical))
                return False
            
            logger.warning(f"⚠️  Found {len(missing_critical)} missing critical dependencies")
            logger.info("Attempting automatic installation...")
            
            failed = []
            for package in missing_critical:
                if not self.install_package(package):
                    failed.append(package)
            
            if failed:
                logger.error("❌ Failed to install critical dependencies:")
                for package in failed:
                    logger.error(f"  - {package}")
                logger.error("\nManual installation required:")
                logger.error(f"  pip install {' '.join(failed)}")
                return False
            
            logger.info("✅ All critical dependencies installed successfully")
        else:
            logger.info("✅ All critical dependencies available")
        
        # Handle optional dependencies
        if missing_optional:
            logger.info(f"ℹ️  {len(missing_optional)} optional dependencies not installed:")
            for package in missing_optional:
                logger.info(f"  - {package}")
            logger.info("These are optional for advanced features (speaker ID, etc.)")
            logger.info("Install with: pip install " + " ".join(missing_optional))
        
        return True
    
    def check_gpu_availability(self) -> bool:
        """Check if GPU/CUDA is available for PyTorch."""
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            if has_cuda:
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"✅ GPU available: {gpu_name}")
            else:
                logger.warning("⚠️  No GPU detected - will use CPU (slower)")
            return has_cuda
        except Exception as e:
            logger.warning(f"Could not check GPU availability: {e}")
            return False
    
    def check_ytdlp_version(self) -> bool:
        """Check if yt-dlp is up-to-date and update if needed."""
        try:
            # Import the updater (relative import)
            from .ytdlp_updater import check_and_update_ytdlp
            
            logger.info("Checking yt-dlp version...")
            return check_and_update_ytdlp(force=False, use_nightly=False)
        except Exception as e:
            logger.warning(f"Could not check yt-dlp version: {e}")
            return True  # Don't fail if check fails


def check_and_install_dependencies(auto_install: bool = True, check_ytdlp: bool = True) -> bool:
    """
    Convenience function to check and install dependencies.
    
    Args:
        auto_install: If True, automatically install missing dependencies
        check_ytdlp: If True, also check and update yt-dlp version
    
    Returns:
        True if all critical dependencies are available
    """
    checker = DependencyChecker(auto_install=auto_install)
    
    # Check dependencies
    success = checker.auto_fix_dependencies()
    
    # Check GPU
    if success:
        checker.check_gpu_availability()
    
    # Check yt-dlp version
    if success and check_ytdlp:
        checker.check_ytdlp_version()
    
    return success


if __name__ == "__main__":
    # Test the dependency checker
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    import argparse
    parser = argparse.ArgumentParser(description="Check and install dependencies")
    parser.add_argument('--no-auto-install', action='store_true',
                       help='Only check, do not auto-install')
    args = parser.parse_args()
    
    success = check_and_install_dependencies(auto_install=not args.no_auto_install)
    sys.exit(0 if success else 1)
