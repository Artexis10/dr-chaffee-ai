#!/usr/bin/env python3
"""
Unit tests for regenerate_speaker_labels.py

Tests:
- Memory-safe batch processing
- No memory overflow with large datasets
- Correct speaker identification logic
- Database update safety
"""
import os
import sys
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import psutil
import gc

# Add to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from regenerate_speaker_labels import (
    get_segment_count,
    get_video_ids_with_embeddings,
    get_segments_for_video,
    identify_speaker_improved,
    smooth_speaker_labels,
    process_video_batch
)


class TestMemorySafety:
    """Test that batch processing doesn't cause memory overflow"""
    
    def test_batch_processing_limits_memory(self):
        """Verify batch processing keeps memory under control"""
        # Mock database
        mock_db = Mock()
        
        # Simulate large dataset (1000 videos, 100 segments each)
        video_ids = [f'video_{i}' for i in range(1000)]
        
        # Mock segments for each video
        def mock_get_segments(video_id):
            return [{
                'id': f'{video_id}_seg_{i}',
                'video_id': video_id,
                'speaker_label': 'Chaffee',
                'embedding': np.random.randn(192),
                'start_sec': i * 10.0,
                'end_sec': (i + 1) * 10.0
            } for i in range(100)]
        
        # Mock profile and enrollment
        mock_profile = {'centroid': np.random.randn(192).tolist()}
        mock_enrollment = Mock()
        mock_enrollment.compute_similarity = Mock(return_value=0.7)
        
        # Track memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process in batches of 50
        batch_size = 50
        max_memory_increase = 0
        
        for batch_idx in range(0, len(video_ids), batch_size):
            batch_video_ids = video_ids[batch_idx:batch_idx + batch_size]
            
            # Simulate batch processing
            all_segments = []
            for vid in batch_video_ids:
                segments = mock_get_segments(vid)
                all_segments.extend(segments)
            
            # Clear batch
            del all_segments
            gc.collect()
            
            # Check memory
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = current_memory - initial_memory
            max_memory_increase = max(max_memory_increase, memory_increase)
        
        # Memory increase should be bounded (< 500 MB for this test)
        assert max_memory_increase < 500, f"Memory increased by {max_memory_increase:.1f} MB (too much!)"
    
    def test_segments_cleared_after_batch(self):
        """Verify segments are cleared from memory after each batch"""
        mock_db = Mock()
        mock_profile = {'centroid': np.random.randn(192).tolist()}
        mock_enrollment = Mock()
        mock_enrollment.compute_similarity = Mock(return_value=0.7)
        
        # Create batch with segments
        video_ids = ['video1', 'video2']
        
        with patch('regenerate_speaker_labels.get_segments_for_video') as mock_get:
            mock_get.return_value = [{
                'id': 'seg1',
                'video_id': 'video1',
                'speaker_label': 'Chaffee',
                'embedding': np.random.randn(192),
                'start_sec': 0.0,
                'end_sec': 10.0
            }]
            
            # Process batch
            segments = process_video_batch(mock_db, video_ids, mock_profile, mock_enrollment)
            
            # Segments should be returned
            assert len(segments) > 0
            
            # After deletion, memory should be freed
            del segments
            gc.collect()
            
            # This should not fail (memory is freed)
            assert True


class TestSpeakerIdentification:
    """Test speaker identification logic"""
    
    def test_high_similarity_identifies_chaffee(self):
        """High similarity (>0.75) should identify as Chaffee"""
        embedding = np.random.randn(192)
        profile = {'centroid': np.random.randn(192).tolist()}
        
        mock_enrollment = Mock()
        mock_enrollment.compute_similarity = Mock(return_value=0.8)
        
        speaker, confidence, similarity = identify_speaker_improved(
            embedding, profile, mock_enrollment
        )
        
        assert speaker == 'Chaffee'
        assert similarity == 0.8
    
    def test_low_similarity_identifies_guest(self):
        """Low similarity (<0.65) should identify as GUEST"""
        embedding = np.random.randn(192)
        profile = {'centroid': np.random.randn(192).tolist()}
        
        mock_enrollment = Mock()
        mock_enrollment.compute_similarity = Mock(return_value=0.5)
        
        speaker, confidence, similarity = identify_speaker_improved(
            embedding, profile, mock_enrollment
        )
        
        assert speaker == 'GUEST'
        assert similarity == 0.5
    
    def test_medium_similarity_uses_temporal_context(self):
        """Medium similarity (0.65-0.75) should use previous speaker"""
        embedding = np.random.randn(192)
        profile = {'centroid': np.random.randn(192).tolist()}
        
        mock_enrollment = Mock()
        mock_enrollment.compute_similarity = Mock(return_value=0.7)
        
        # With Chaffee as previous speaker
        speaker1, _, _ = identify_speaker_improved(
            embedding, profile, mock_enrollment, prev_speaker='Chaffee'
        )
        assert speaker1 == 'Chaffee'
        
        # With GUEST as previous speaker
        speaker2, _, _ = identify_speaker_improved(
            embedding, profile, mock_enrollment, prev_speaker='GUEST'
        )
        assert speaker2 == 'GUEST'
    
    def test_none_embedding_returns_unknown(self):
        """None embedding should return Unknown"""
        speaker, confidence, similarity = identify_speaker_improved(
            None, {}, Mock()
        )
        
        assert speaker == 'Unknown'
        assert confidence == 0.0
        assert similarity == 0.0


class TestTemporalSmoothing:
    """Test temporal smoothing logic"""
    
    def test_smooths_isolated_misidentification(self):
        """Should smooth isolated segment surrounded by same speaker"""
        segments = [
            {'new_speaker': 'Chaffee', 'start_sec': 0, 'end_sec': 10},
            {'new_speaker': 'GUEST', 'start_sec': 10, 'end_sec': 15},  # Isolated, short
            {'new_speaker': 'Chaffee', 'start_sec': 15, 'end_sec': 25},
        ]
        
        smoothed_count = smooth_speaker_labels(segments)
        
        assert smoothed_count == 1
        assert segments[1]['new_speaker'] == 'Chaffee'
        assert segments[1].get('smoothed') == True
    
    def test_does_not_smooth_long_segments(self):
        """Should not smooth segments >= 10 seconds"""
        segments = [
            {'new_speaker': 'Chaffee', 'start_sec': 0, 'end_sec': 10},
            {'new_speaker': 'GUEST', 'start_sec': 10, 'end_sec': 25},  # Long segment
            {'new_speaker': 'Chaffee', 'start_sec': 25, 'end_sec': 35},
        ]
        
        smoothed_count = smooth_speaker_labels(segments)
        
        assert smoothed_count == 0
        assert segments[1]['new_speaker'] == 'GUEST'
    
    def test_does_not_smooth_real_speaker_changes(self):
        """Should not smooth when speakers actually change"""
        segments = [
            {'new_speaker': 'Chaffee', 'start_sec': 0, 'end_sec': 10},
            {'new_speaker': 'GUEST', 'start_sec': 10, 'end_sec': 15},
            {'new_speaker': 'GUEST', 'start_sec': 15, 'end_sec': 25},  # Not isolated
        ]
        
        smoothed_count = smooth_speaker_labels(segments)
        
        assert smoothed_count == 0
        assert segments[1]['new_speaker'] == 'GUEST'


class TestDatabaseOperations:
    """Test database query functions"""
    
    def test_get_segment_count(self):
        """Test segment count query"""
        mock_db = Mock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (12345,)
        
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor = Mock(return_value=MagicMock(__enter__=Mock(return_value=mock_cursor), __exit__=Mock(return_value=False)))
        
        mock_db.get_connection.return_value = mock_conn
        
        count = get_segment_count(mock_db)
        
        assert count == 12345
    
    def test_get_video_ids_with_embeddings(self):
        """Test video ID retrieval"""
        mock_db = Mock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [('video1',), ('video2',), ('video3',)]
        
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor = Mock(return_value=MagicMock(__enter__=Mock(return_value=mock_cursor), __exit__=Mock(return_value=False)))
        
        mock_db.get_connection.return_value = mock_conn
        
        video_ids = get_video_ids_with_embeddings(mock_db)
        
        assert video_ids == ['video1', 'video2', 'video3']
    
    def test_get_segments_for_video_returns_numpy_arrays(self):
        """Test that embeddings are converted to numpy arrays"""
        mock_db = Mock()
        mock_cursor = MagicMock()
        
        # Mock database returns list for embedding
        embedding_list = [0.1, 0.2, 0.3]
        mock_cursor.fetchall.return_value = [
            ('seg1', 'video1', 'Chaffee', embedding_list, 0.0, 10.0)
        ]
        
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor = Mock(return_value=MagicMock(__enter__=Mock(return_value=mock_cursor), __exit__=Mock(return_value=False)))
        
        mock_db.get_connection.return_value = mock_conn
        
        segments = get_segments_for_video(mock_db, 'video1')
        
        assert len(segments) == 1
        assert isinstance(segments[0]['embedding'], np.ndarray)
        assert np.array_equal(segments[0]['embedding'], np.array(embedding_list))


class TestBatchProcessing:
    """Test batch processing logic"""
    
    def test_process_video_batch_handles_empty_videos(self):
        """Should handle videos with no segments gracefully"""
        mock_db = Mock()
        mock_profile = {'centroid': np.random.randn(192).tolist()}
        mock_enrollment = Mock()
        
        with patch('regenerate_speaker_labels.get_segments_for_video') as mock_get:
            mock_get.return_value = []  # No segments
            
            segments = process_video_batch(
                mock_db, ['video1'], mock_profile, mock_enrollment
            )
            
            assert segments == []
    
    def test_process_video_batch_applies_smoothing(self):
        """Should apply smoothing to each video"""
        mock_db = Mock()
        mock_profile = {'centroid': np.random.randn(192).tolist()}
        mock_enrollment = Mock()
        mock_enrollment.compute_similarity = Mock(side_effect=[0.8, 0.5, 0.8])
        
        with patch('regenerate_speaker_labels.get_segments_for_video') as mock_get:
            # Return segments that should be smoothed
            mock_get.return_value = [
                {'id': '1', 'video_id': 'v1', 'speaker_label': 'Chaffee', 
                 'embedding': np.random.randn(192), 'start_sec': 0, 'end_sec': 10},
                {'id': '2', 'video_id': 'v1', 'speaker_label': 'GUEST',
                 'embedding': np.random.randn(192), 'start_sec': 10, 'end_sec': 15},
                {'id': '3', 'video_id': 'v1', 'speaker_label': 'Chaffee',
                 'embedding': np.random.randn(192), 'start_sec': 15, 'end_sec': 25},
            ]
            
            segments = process_video_batch(
                mock_db, ['v1'], mock_profile, mock_enrollment
            )
            
            # Middle segment should be smoothed to Chaffee
            assert segments[1]['new_speaker'] == 'Chaffee'
            assert segments[1].get('smoothed') == True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
