#!/usr/bin/env python3
"""
Unit tests for --limit-unprocessed logic in list_videos().

Tests that the smart limit feature correctly finds N unprocessed videos.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from dataclasses import dataclass


@dataclass
class MockVideoInfo:
    """Mock VideoInfo for testing."""
    video_id: str
    title: str
    duration_s: int = 300
    published_at: datetime = None


@pytest.mark.unit
class TestLimitUnprocessedLogic:
    """Test --limit-unprocessed finds N unprocessed videos."""
    
    def test_limit_unprocessed_finds_unprocessed_videos(self, monkeypatch):
        """Test that --limit-unprocessed correctly finds N unprocessed videos."""
        from backend.scripts.ingest_youtube import EnhancedYouTubeIngester, IngestionConfig
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        # Create config with limit_unprocessed=True
        config = IngestionConfig(
            source='yt-dlp',
            limit=3,
            limit_unprocessed=True,
            dry_run=True
        )
        
        # Create ingester
        ingester = EnhancedYouTubeIngester(config)
        
        # Mock video lister to return 10 videos
        mock_videos = [
            MockVideoInfo(f"video_{i}", f"Title {i}", published_at=datetime.now(timezone.utc))
            for i in range(10)
        ]
        
        # Mock segments_db.check_video_exists to return:
        # - Videos 0, 1, 2: already processed (source_id=1, segment_count=10)
        # - Videos 3, 4, 5: unprocessed (source_id=None, segment_count=0)
        # - Videos 6, 7, 8, 9: already processed
        def mock_check_exists(video_id):
            video_num = int(video_id.split('_')[1])
            if video_num in [3, 4, 5]:
                return (None, 0)  # Unprocessed
            else:
                return (1, 10)  # Processed
        
        ingester.segments_db.check_video_exists = Mock(side_effect=mock_check_exists)
        ingester.video_lister.list_channel_videos = Mock(return_value=mock_videos)
        
        # Call list_videos()
        result = ingester.list_videos()
        
        # Should return exactly 3 unprocessed videos (3, 4, 5)
        assert len(result) == 3
        assert result[0].video_id == "video_3"
        assert result[1].video_id == "video_4"
        assert result[2].video_id == "video_5"
    
    def test_limit_unprocessed_stops_after_finding_limit(self, monkeypatch):
        """Test that search stops after finding N unprocessed videos."""
        from backend.scripts.ingest_youtube import EnhancedYouTubeIngester, IngestionConfig
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        config = IngestionConfig(
            source='yt-dlp',
            limit=2,
            limit_unprocessed=True,
            dry_run=True
        )
        
        ingester = EnhancedYouTubeIngester(config)
        
        # Create 100 videos
        mock_videos = [
            MockVideoInfo(f"video_{i}", f"Title {i}", published_at=datetime.now(timezone.utc))
            for i in range(100)
        ]
        
        # First 50 are processed, next 50 are unprocessed
        def mock_check_exists(video_id):
            video_num = int(video_id.split('_')[1])
            if video_num < 50:
                return (1, 10)  # Processed
            else:
                return (None, 0)  # Unprocessed
        
        ingester.segments_db.check_video_exists = Mock(side_effect=mock_check_exists)
        ingester.video_lister.list_channel_videos = Mock(return_value=mock_videos)
        
        result = ingester.list_videos()
        
        # Should return exactly 2 videos (video_50, video_51)
        assert len(result) == 2
        assert result[0].video_id == "video_50"
        assert result[1].video_id == "video_51"
        
        # Should have checked 52 videos (0-49 processed, 50-51 unprocessed)
        assert ingester.segments_db.check_video_exists.call_count == 52
    
    def test_limit_unprocessed_returns_fewer_if_not_enough(self, monkeypatch):
        """Test returns fewer videos if not enough unprocessed exist."""
        from backend.scripts.ingest_youtube import EnhancedYouTubeIngester, IngestionConfig
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        config = IngestionConfig(
            source='yt-dlp',
            limit=10,
            limit_unprocessed=True,
            dry_run=True
        )
        
        ingester = EnhancedYouTubeIngester(config)
        
        # Only 5 videos total
        mock_videos = [
            MockVideoInfo(f"video_{i}", f"Title {i}", published_at=datetime.now(timezone.utc))
            for i in range(5)
        ]
        
        # Only 2 are unprocessed
        def mock_check_exists(video_id):
            video_num = int(video_id.split('_')[1])
            if video_num in [1, 3]:
                return (None, 0)  # Unprocessed
            else:
                return (1, 10)  # Processed
        
        ingester.segments_db.check_video_exists = Mock(side_effect=mock_check_exists)
        ingester.video_lister.list_channel_videos = Mock(return_value=mock_videos)
        
        result = ingester.list_videos()
        
        # Should return only 2 videos (not 10)
        assert len(result) == 2
        assert result[0].video_id == "video_1"
        assert result[1].video_id == "video_3"
    
    def test_limit_without_limit_unprocessed_takes_first_n(self, monkeypatch):
        """Test that --limit without --limit-unprocessed takes first N videos."""
        from backend.scripts.ingest_youtube import EnhancedYouTubeIngester, IngestionConfig
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        config = IngestionConfig(
            source='yt-dlp',
            limit=3,
            limit_unprocessed=False,  # Standard limit
            dry_run=True
        )
        
        ingester = EnhancedYouTubeIngester(config)
        
        mock_videos = [
            MockVideoInfo(f"video_{i}", f"Title {i}", published_at=datetime.now(timezone.utc))
            for i in range(10)
        ]
        
        ingester.video_lister.list_channel_videos = Mock(return_value=mock_videos)
        ingester.segments_db.check_video_exists = Mock(return_value=(None, 0))
        
        result = ingester.list_videos()
        
        # Should return first 3 videos (standard limit, not smart limit)
        assert len(result) == 3
        assert result[0].video_id == "video_0"
        assert result[1].video_id == "video_1"
        assert result[2].video_id == "video_2"
    
    def test_limit_unprocessed_respects_newest_first_sorting(self, monkeypatch):
        """Test that --limit-unprocessed respects --newest-first sorting."""
        from backend.scripts.ingest_youtube import EnhancedYouTubeIngester, IngestionConfig
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        config = IngestionConfig(
            source='yt-dlp',
            limit=2,
            limit_unprocessed=True,
            newest_first=True,
            dry_run=True
        )
        
        ingester = EnhancedYouTubeIngester(config)
        
        # Create videos with different publish dates
        mock_videos = [
            MockVideoInfo("old_video", "Old", published_at=datetime(2020, 1, 1, tzinfo=timezone.utc)),
            MockVideoInfo("new_video", "New", published_at=datetime(2024, 1, 1, tzinfo=timezone.utc)),
            MockVideoInfo("newer_video", "Newer", published_at=datetime(2024, 6, 1, tzinfo=timezone.utc)),
        ]
        
        # All unprocessed
        ingester.segments_db.check_video_exists = Mock(return_value=(None, 0))
        ingester.video_lister.list_channel_videos = Mock(return_value=mock_videos)
        
        result = ingester.list_videos()
        
        # Should return 2 newest videos
        assert len(result) == 2
        # After sorting by newest_first, should get newer_video and new_video
        assert result[0].video_id == "newer_video"
        assert result[1].video_id == "new_video"


@pytest.mark.unit
class TestLimitUnprocessedEdgeCases:
    """Test edge cases for --limit-unprocessed."""
    
    def test_limit_unprocessed_with_all_processed(self, monkeypatch):
        """Test returns empty list if all videos are processed."""
        from backend.scripts.ingest_youtube import EnhancedYouTubeIngester, IngestionConfig
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        config = IngestionConfig(
            source='yt-dlp',
            limit=5,
            limit_unprocessed=True,
            dry_run=True
        )
        
        ingester = EnhancedYouTubeIngester(config)
        
        mock_videos = [
            MockVideoInfo(f"video_{i}", f"Title {i}", published_at=datetime.now(timezone.utc))
            for i in range(10)
        ]
        
        # All videos are processed
        ingester.segments_db.check_video_exists = Mock(return_value=(1, 10))
        ingester.video_lister.list_channel_videos = Mock(return_value=mock_videos)
        
        result = ingester.list_videos()
        
        # Should return empty list
        assert len(result) == 0
    
    def test_limit_unprocessed_with_zero_segments_counts_as_unprocessed(self, monkeypatch):
        """Test that videos with 0 segments are considered unprocessed."""
        from backend.scripts.ingest_youtube import EnhancedYouTubeIngester, IngestionConfig
        
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        config = IngestionConfig(
            source='yt-dlp',
            limit=2,
            limit_unprocessed=True,
            dry_run=True
        )
        
        ingester = EnhancedYouTubeIngester(config)
        
        mock_videos = [
            MockVideoInfo("video_0", "Title 0", published_at=datetime.now(timezone.utc)),
            MockVideoInfo("video_1", "Title 1", published_at=datetime.now(timezone.utc)),
        ]
        
        # Video has source_id but 0 segments (failed processing)
        ingester.segments_db.check_video_exists = Mock(return_value=(1, 0))
        ingester.video_lister.list_channel_videos = Mock(return_value=mock_videos)
        
        result = ingester.list_videos()
        
        # Should treat as unprocessed and return both
        assert len(result) == 2
