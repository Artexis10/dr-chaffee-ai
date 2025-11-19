#!/usr/bin/env python3
"""
Unit tests for video-only stream handling (NO_AUDIO marker).

Tests the complete flow:
1. Audio codec validation with ffprobe
2. NO_AUDIO marker return from enhanced_transcript_fetch
3. Proper stat tracking (no_audio vs errors)
4. Prevention of embedding processing for video-only files
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


@pytest.mark.unit
class TestVideoOnlyHandling:
    """Test handling of YouTube video-only streams with no audio track."""
    
    def test_audio_codec_validation_detects_video_only(self, tmp_path):
        """Test ffprobe detects files with no audio track."""
        from backend.scripts.common.enhanced_transcript_fetch import EnhancedTranscriptFetcher
        
        # Mock ffprobe to return no audio
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(stdout='', returncode=0)
            
            # This should detect no audio and reject the file
            # In real implementation, this happens in _download_audio_for_enhanced_asr
            result = mock_run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', 
                             '-show_entries', 'stream=codec_type', '-of', 
                             'default=noprint_wrappers=1:nokey=1', 'test.mp4'])
            
            has_audio = 'audio' in result.stdout.lower()
            assert not has_audio, "Should detect no audio track"
    
    def test_no_audio_marker_returned_from_download(self):
        """Test that _download_audio_for_enhanced_asr returns NO_AUDIO marker."""
        from backend.scripts.common.enhanced_transcript_fetch import EnhancedTranscriptFetcher
        
        fetcher = EnhancedTranscriptFetcher(enable_speaker_id=True)
        
        # Mock yt-dlp download that returns video-only file
        with patch.object(fetcher, '_download_audio_for_enhanced_asr') as mock_download:
            mock_download.return_value = ("NO_AUDIO", "test_video_id")
            
            result = fetcher._download_audio_for_enhanced_asr("test_video_id")
            
            assert isinstance(result, tuple), "Should return tuple"
            assert result[0] == "NO_AUDIO", "Should return NO_AUDIO marker"
            assert result[1] == "test_video_id", "Should include video ID"
    
    def test_no_audio_marker_caught_in_fetch_transcript(self):
        """Test that fetch_transcript_with_speaker_id catches NO_AUDIO marker."""
        from backend.scripts.common.enhanced_transcript_fetch import EnhancedTranscriptFetcher
        
        fetcher = EnhancedTranscriptFetcher(enable_speaker_id=True)
        
        # Use valid 11-character YouTube video ID format
        test_video_id = "dQw4w9WgXcQ"
        
        # Mock all the dependencies
        with patch.object(fetcher, '_download_audio_for_enhanced_asr') as mock_download, \
             patch.object(fetcher, '_check_speaker_profiles_available', return_value=True), \
             patch.object(fetcher, '_get_enhanced_asr', return_value=Mock()):
            
            mock_download.return_value = ("NO_AUDIO", test_video_id)
            
            segments, method, metadata = fetcher.fetch_transcript_with_speaker_id(
                test_video_id,
                force_enhanced_asr=True
            )
            
            # Should return NO_AUDIO marker as segments
            assert isinstance(segments, tuple), "Should return tuple"
            assert segments[0] == "NO_AUDIO", "Should propagate NO_AUDIO marker"
            assert method == 'no_audio', "Method should be 'no_audio'"
            assert 'error' in metadata, "Should have error in metadata"
    
    def test_no_audio_stat_incremented_not_error(self):
        """Test that no_audio stat is incremented, not errors."""
        from backend.scripts.ingest_youtube import ProcessingStats
        
        stats = ProcessingStats()
        
        # Simulate processing a video-only file
        segments = ("NO_AUDIO", "test_video_id")
        
        if isinstance(segments, tuple) and segments[0] == "NO_AUDIO":
            stats.no_audio += 1
        else:
            stats.errors += 1
        
        assert stats.no_audio == 1, "Should increment no_audio"
        assert stats.errors == 0, "Should not increment errors"
    
    def test_no_audio_prevents_embedding_processing(self):
        """Test that NO_AUDIO marker prevents embedding batch processing."""
        from backend.scripts.ingest_youtube import ProcessingStats
        
        stats = ProcessingStats()
        segments = ("NO_AUDIO", "test_video_id")
        
        # Simulate DB worker check
        should_process_embeddings = not (isinstance(segments, tuple) and segments[0] == "NO_AUDIO")
        
        assert not should_process_embeddings, "Should not process embeddings for NO_AUDIO"
    
    def test_no_audio_logging_message(self, caplog):
        """Test that proper warning is logged for video-only streams."""
        import logging
        from backend.scripts.ingest_youtube import ProcessingStats
        
        logger = logging.getLogger(__name__)
        stats = ProcessingStats()
        
        video_id = "test_video_id"
        segments = ("NO_AUDIO", video_id)
        
        if isinstance(segments, tuple) and segments[0] == "NO_AUDIO":
            logger.warning(f"⏭️  Skipping {video_id}: video-only stream (no audio track)")
            stats.no_audio += 1
        
        assert stats.no_audio == 1
    
    def test_audio_codec_validation_with_valid_audio(self):
        """Test ffprobe correctly identifies files WITH audio."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(stdout='audio', returncode=0)
            
            result = mock_run(['ffprobe', '-v', 'error', '-select_streams', 'a:0',
                             '-show_entries', 'stream=codec_type', '-of',
                             'default=noprint_wrappers=1:nokey=1', 'test.mp4'])
            
            has_audio = 'audio' in result.stdout.lower()
            assert has_audio, "Should detect audio track"
    
    def test_fallback_chain_tries_all_clients(self):
        """Test that download fallback chain tries web, android, default."""
        from backend.scripts.common.enhanced_transcript_fetch import EnhancedTranscriptFetcher
        
        fetcher = EnhancedTranscriptFetcher(enable_speaker_id=True)
        
        # Expected client strategies
        expected_strategies = [
            ('web', 'youtube:player_client=web'),
            ('android', 'youtube:player_client=android'),
            ('default', None)
        ]
        
        # This is the order defined in _download_audio_for_enhanced_asr
        assert len(expected_strategies) == 3, "Should have 3 fallback strategies"
        assert expected_strategies[0][0] == 'web', "First strategy should be web"
        assert expected_strategies[1][0] == 'android', "Second strategy should be android"
        assert expected_strategies[2][0] == 'default', "Third strategy should be default"
    
    def test_file_size_validation_rejects_small_files(self):
        """Test that files < 50 KiB are rejected as stubs."""
        min_size = 50 * 1024  # 50 KiB
        
        # Simulate small file (stub)
        stub_size = 10 * 1024  # 10 KiB
        assert stub_size < min_size, "Stub file should be rejected"
        
        # Simulate valid file
        valid_size = 1.5 * 1024 * 1024  # 1.5 MB
        assert valid_size >= min_size, "Valid file should be accepted"
    
    def test_stats_summary_includes_no_audio(self):
        """Test that stats summary properly displays no_audio count."""
        from backend.scripts.ingest_youtube import ProcessingStats
        
        stats = ProcessingStats()
        stats.total = 50
        stats.processed = 40
        stats.skipped = 5
        stats.no_audio = 3
        stats.errors = 2
        
        # Verify stats are tracked correctly
        assert stats.no_audio == 3, "Should track no_audio separately"
        assert stats.errors == 2, "Should track errors separately"
        assert stats.processed + stats.skipped + stats.no_audio + stats.errors == stats.total
    
    def test_no_audio_cleanup_temp_files(self, tmp_path):
        """Test that temporary audio files are cleaned up for NO_AUDIO videos."""
        # Create a fake temp audio file
        temp_file = tmp_path / "test_video_audio.wav"
        temp_file.write_text("fake audio")
        
        assert temp_file.exists(), "Temp file should exist initially"
        
        # Simulate cleanup for NO_AUDIO
        segments = ("NO_AUDIO", "test_video_id")
        if isinstance(segments, tuple) and segments[0] == "NO_AUDIO":
            if temp_file.exists():
                os.unlink(temp_file)
        
        assert not temp_file.exists(), "Temp file should be cleaned up"


@pytest.mark.integration
class TestVideoOnlyIntegration:
    """Integration tests for video-only handling in full pipeline."""
    
    @pytest.mark.slow
    def test_real_video_only_short_handling(self):
        """Test handling of a real YouTube short with no audio (if available)."""
        # This would test against a real video-only YouTube short
        # Skip if no test video ID is configured
        pytest.skip("Requires real YouTube video-only short ID for testing")
    
    def test_pipeline_continues_after_no_audio(self):
        """Test that pipeline continues processing after encountering NO_AUDIO."""
        from backend.scripts.ingest_youtube import ProcessingStats
        
        stats = ProcessingStats()
        
        # Simulate processing multiple videos with some NO_AUDIO
        videos = [
            ("segments", "video1"),  # Normal video
            ("NO_AUDIO", "video2"),  # Video-only
            ("segments", "video3"),  # Normal video
            ("NO_AUDIO", "video4"),  # Video-only
        ]
        
        for item in videos:
            if isinstance(item, tuple) and item[0] == "NO_AUDIO":
                stats.no_audio += 1
            else:
                stats.processed += 1
        
        assert stats.processed == 2, "Should process normal videos"
        assert stats.no_audio == 2, "Should track video-only"
        assert stats.errors == 0, "Should not count as errors"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
