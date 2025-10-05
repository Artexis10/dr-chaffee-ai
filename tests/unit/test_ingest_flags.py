#!/usr/bin/env python3
"""
Unit tests for command-line flag parsing and config creation.

Tests that all CLI flags are properly parsed and passed to IngestionConfig.
"""
import pytest
import sys
from unittest.mock import patch


@pytest.mark.unit
class TestFlagParsing:
    """Test that CLI flags are correctly parsed and passed to config."""
    
    def test_limit_unprocessed_flag_parsed(self, monkeypatch):
        """Test --limit-unprocessed flag is parsed correctly."""
        from backend.scripts.ingest_youtube import parse_args
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        test_args = ['ingest_youtube.py', '--source', 'yt-dlp', '--limit', '5', '--limit-unprocessed', '--dry-run']
        with patch.object(sys, 'argv', test_args):
            config = parse_args()
        
        assert config.limit == 5
        assert config.limit_unprocessed is True, "limit_unprocessed should be True when flag is provided"
    
    def test_limit_unprocessed_flag_default(self, monkeypatch):
        """Test --limit-unprocessed defaults to False."""
        from backend.scripts.ingest_youtube import parse_args
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        test_args = ['ingest_youtube.py', '--source', 'yt-dlp', '--limit', '5', '--dry-run']
        with patch.object(sys, 'argv', test_args):
            config = parse_args()
        
        assert config.limit == 5
        assert config.limit_unprocessed is False, "limit_unprocessed should default to False"
    
    def test_force_reprocess_flag_parsed(self, monkeypatch):
        """Test --force flag is parsed correctly."""
        from backend.scripts.ingest_youtube import parse_args
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        test_args = ['ingest_youtube.py', '--source', 'yt-dlp', '--force', '--dry-run']
        with patch.object(sys, 'argv', test_args):
            config = parse_args()
        
        assert config.force_reprocess is True, "force_reprocess should be True when --force is provided"
    
    def test_force_reprocess_flag_default(self, monkeypatch):
        """Test --force defaults to False."""
        from backend.scripts.ingest_youtube import parse_args
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        test_args = ['ingest_youtube.py', '--source', 'yt-dlp', '--dry-run']
        with patch.object(sys, 'argv', test_args):
            config = parse_args()
        
        assert config.force_reprocess is False, "force_reprocess should default to False"
    
    def test_skip_existing_flag_default(self, monkeypatch):
        """Test skip_existing defaults to True."""
        from backend.scripts.ingest_youtube import parse_args
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        test_args = ['ingest_youtube.py', '--source', 'yt-dlp', '--dry-run']
        with patch.object(sys, 'argv', test_args):
            config = parse_args()
        
        assert config.skip_existing is True, "skip_existing should default to True"
    
    def test_no_skip_existing_flag_parsed(self, monkeypatch):
        """Test --no-skip-existing flag is parsed correctly."""
        from backend.scripts.ingest_youtube import parse_args
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        test_args = ['ingest_youtube.py', '--source', 'yt-dlp', '--no-skip-existing', '--dry-run']
        with patch.object(sys, 'argv', test_args):
            config = parse_args()
        
        assert config.skip_existing is False, "skip_existing should be False when --no-skip-existing is provided"


@pytest.mark.unit
class TestFlagCombinations:
    """Test combinations of flags work correctly."""
    
    def test_limit_with_limit_unprocessed(self, monkeypatch):
        """Test --limit and --limit-unprocessed work together."""
        from backend.scripts.ingest_youtube import parse_args
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        test_args = ['ingest_youtube.py', '--source', 'yt-dlp', '--limit', '50', '--limit-unprocessed', '--dry-run']
        with patch.object(sys, 'argv', test_args):
            config = parse_args()
        
        assert config.limit == 50
        assert config.limit_unprocessed is True
        assert config.source == 'yt-dlp'
    
    def test_force_with_limit(self, monkeypatch):
        """Test --force and --limit work together."""
        from backend.scripts.ingest_youtube import parse_args
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        test_args = ['ingest_youtube.py', '--source', 'yt-dlp', '--limit', '10', '--force', '--dry-run']
        with patch.object(sys, 'argv', test_args):
            config = parse_args()
        
        assert config.limit == 10
        assert config.force_reprocess is True
        assert config.skip_existing is True  # Default
    
    def test_mutually_exclusive_force_and_no_skip(self, monkeypatch):
        """Test --force and --no-skip-existing can be used together (though redundant)."""
        from backend.scripts.ingest_youtube import parse_args
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        test_args = ['ingest_youtube.py', '--source', 'yt-dlp', '--force', '--no-skip-existing', '--dry-run']
        with patch.object(sys, 'argv', test_args):
            config = parse_args()
        
        assert config.force_reprocess is True
        assert config.skip_existing is False


@pytest.mark.unit
class TestConfigFieldMapping:
    """Test that all important config fields are properly set from args."""
    
    def test_all_processing_flags_mapped(self, monkeypatch):
        """Test all processing-related flags are mapped to config."""
        from backend.scripts.ingest_youtube import parse_args
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        test_args = [
            'ingest_youtube.py',
            '--source', 'yt-dlp',
            '--limit', '100',
            '--limit-unprocessed',
            '--force',
            '--skip-shorts',
            '--newest-first',
            '--dry-run'
        ]
        with patch.object(sys, 'argv', test_args):
            config = parse_args()
        
        # Verify all flags are properly set
        assert config.source == 'yt-dlp'
        assert config.limit == 100
        assert config.limit_unprocessed is True
        assert config.force_reprocess is True
        assert config.skip_shorts is True
        assert config.newest_first is True
        assert config.dry_run is True
    
    def test_whisper_flags_mapped(self, monkeypatch):
        """Test Whisper-related flags are mapped to config."""
        from backend.scripts.ingest_youtube import parse_args
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        test_args = [
            'ingest_youtube.py',
            '--source', 'yt-dlp',
            '--whisper-model', 'distil-large-v3',
            '--force-whisper',
            '--dry-run'
        ]
        with patch.object(sys, 'argv', test_args):
            config = parse_args()
        
        assert config.whisper_model == 'distil-large-v3'
        assert config.force_whisper is True


@pytest.mark.unit
class TestRegressionTests:
    """Regression tests for bugs that were fixed."""
    
    def test_regression_limit_unprocessed_not_passed_to_config(self, monkeypatch):
        """
        Regression test for bug where --limit-unprocessed was parsed but not
        passed to IngestionConfig, causing it to always be False.
        
        This bug was fixed in commit 4437459.
        """
        from backend.scripts.ingest_youtube import parse_args
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        test_args = ['ingest_youtube.py', '--source', 'yt-dlp', '--limit', '5', '--limit-unprocessed', '--dry-run']
        with patch.object(sys, 'argv', test_args):
            config = parse_args()
        
        # This was the bug: limit_unprocessed was always False
        assert config.limit_unprocessed is True, \
            "REGRESSION: limit_unprocessed flag not being passed to config (commit 4437459)"
    
    def test_regression_force_reprocess_not_passed_to_config(self, monkeypatch):
        """
        Regression test for bug where --force was parsed but not passed to
        IngestionConfig, causing it to always be False.
        
        This bug was fixed in commit 4437459.
        """
        from backend.scripts.ingest_youtube import parse_args
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        test_args = ['ingest_youtube.py', '--source', 'yt-dlp', '--force', '--dry-run']
        with patch.object(sys, 'argv', test_args):
            config = parse_args()
        
        # This was also missing
        assert config.force_reprocess is True, \
            "REGRESSION: force_reprocess flag not being passed to config (commit 4437459)"
