"""
Unit tests for video type classification logic.

Tests the _classify_video_type method in SegmentsDatabase to ensure:
1. Monologues are correctly identified (1 speaker)
2. Interviews are correctly identified (>15% guest content)
3. Monologue with clips are correctly identified (<15% guest content)
4. Edge cases are handled properly
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend' / 'scripts'))

from common.segments_database import SegmentsDatabase


class TestVideoTypeClassification:
    """Test video type classification logic"""
    
    @pytest.fixture
    def db(self):
        """Create a mock database instance"""
        with patch('psycopg2.connect'):
            db = SegmentsDatabase("postgresql://test")
            return db
    
    @pytest.fixture
    def mock_conn(self):
        """Create a mock database connection"""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        return conn, cursor
    
    def test_monologue_single_speaker_chaffee(self, db, mock_conn):
        """Test that videos with only Chaffee are classified as monologue"""
        conn, cursor = mock_conn
        
        segments = [
            {'speaker_label': 'Chaffee', 'text': 'Segment 1'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 2'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 3'},
        ]
        
        db._classify_video_type('test_video_1', segments, conn)
        
        # Check UPDATE was called with 'monologue'
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0]
        assert 'monologue' in call_args[0] or call_args[1][0] == 'monologue'
    
    def test_interview_high_guest_percentage(self, db, mock_conn):
        """Test that videos with >15% guest content are classified as interview"""
        conn, cursor = mock_conn
        
        # 20% guest content (2 out of 10)
        segments = [
            {'speaker_label': 'Chaffee', 'text': 'Segment 1'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 2'},
            {'speaker_label': 'GUEST', 'text': 'Segment 3'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 4'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 5'},
            {'speaker_label': 'GUEST', 'text': 'Segment 6'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 7'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 8'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 9'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 10'},
        ]
        
        db._classify_video_type('test_video_2', segments, conn)
        
        # Check UPDATE was called with 'interview'
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0]
        assert 'interview' in call_args[0] or call_args[1][0] == 'interview'
    
    def test_monologue_with_clips_low_guest_percentage(self, db, mock_conn):
        """Test that videos with <15% guest content are classified as monologue_with_clips"""
        conn, cursor = mock_conn
        
        # 10% guest content (1 out of 10)
        segments = [
            {'speaker_label': 'Chaffee', 'text': 'Segment 1'},
            {'speaker_label': 'Guest', 'text': 'Segment 2'},  # Note: different case
            {'speaker_label': 'Chaffee', 'text': 'Segment 3'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 4'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 5'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 6'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 7'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 8'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 9'},
            {'speaker_label': 'Chaffee', 'text': 'Segment 10'},
        ]
        
        db._classify_video_type('test_video_3', segments, conn)
        
        # Check UPDATE was called with 'monologue_with_clips'
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0]
        assert 'monologue_with_clips' in call_args[0] or call_args[1][0] == 'monologue_with_clips'
    
    def test_boundary_case_exactly_15_percent(self, db, mock_conn):
        """Test boundary case: exactly 15% guest content"""
        conn, cursor = mock_conn
        
        # Exactly 15% guest content (3 out of 20)
        segments = [{'speaker_label': 'Chaffee', 'text': f'Segment {i}'} for i in range(17)]
        segments.extend([{'speaker_label': 'GUEST', 'text': f'Guest {i}'} for i in range(3)])
        
        db._classify_video_type('test_video_4', segments, conn)
        
        # At 15%, should still be monologue_with_clips (>15% for interview)
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0]
        assert 'monologue_with_clips' in call_args[0] or call_args[1][0] == 'monologue_with_clips'
    
    def test_boundary_case_just_over_15_percent(self, db, mock_conn):
        """Test boundary case: just over 15% guest content"""
        conn, cursor = mock_conn
        
        # 16% guest content (16 out of 100)
        segments = [{'speaker_label': 'Chaffee', 'text': f'Segment {i}'} for i in range(84)]
        segments.extend([{'speaker_label': 'GUEST', 'text': f'Guest {i}'} for i in range(16)])
        
        db._classify_video_type('test_video_5', segments, conn)
        
        # Just over 15%, should be interview
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0]
        assert 'interview' in call_args[0] or call_args[1][0] == 'interview'
    
    def test_empty_segments_list(self, db, mock_conn):
        """Test handling of empty segments list"""
        conn, cursor = mock_conn
        
        segments = []
        
        db._classify_video_type('test_video_6', segments, conn)
        
        # Should default to 'monologue'
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0]
        assert 'monologue' in call_args[0] or call_args[1][0] == 'monologue'
    
    def test_segments_without_speaker_labels(self, db, mock_conn):
        """Test handling of segments without speaker labels"""
        conn, cursor = mock_conn
        
        segments = [
            {'text': 'Segment 1'},  # No speaker_label
            {'text': 'Segment 2'},
            {'speaker_label': None, 'text': 'Segment 3'},
        ]
        
        db._classify_video_type('test_video_7', segments, conn)
        
        # Should default to 'monologue' when no valid speaker labels
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0]
        assert 'monologue' in call_args[0] or call_args[1][0] == 'monologue'
    
    def test_mixed_speaker_label_formats(self, db, mock_conn):
        """Test handling of different speaker label formats"""
        conn, cursor = mock_conn
        
        segments = [
            {'speaker_label': 'Chaffee', 'text': 'Segment 1'},
            {'speaker_label': 'GUEST', 'text': 'Segment 2'},
            {'speaker_label': 'Guest', 'text': 'Segment 3'},  # Different case
            {'speaker_label': 'SPEAKER_01', 'text': 'Segment 4'},  # Different format
        ]
        
        db._classify_video_type('test_video_8', segments, conn)
        
        # Should handle mixed formats (2+ speakers, 25% GUEST)
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0]
        # 25% guest content (1 GUEST out of 4) -> interview
        assert 'interview' in call_args[0] or call_args[1][0] == 'interview'
    
    def test_database_error_handling(self, db, mock_conn):
        """Test that database errors are handled gracefully"""
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("Database error")
        
        segments = [{'speaker_label': 'Chaffee', 'text': 'Segment 1'}]
        
        # Should not raise exception
        db._classify_video_type('test_video_9', segments, conn)
        
        # Error should be logged but not raised
        assert True  # If we get here, exception was handled
    
    def test_real_world_monologue_example(self, db, mock_conn):
        """Test with realistic monologue data"""
        conn, cursor = mock_conn
        
        # Typical monologue: 150 segments, all Chaffee
        segments = [
            {'speaker_label': 'Chaffee', 'text': f'Segment {i}', 'start': i*10, 'end': i*10+8}
            for i in range(150)
        ]
        
        db._classify_video_type('real_monologue', segments, conn)
        
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0]
        assert 'monologue' in call_args[0] or call_args[1][0] == 'monologue'
    
    def test_real_world_interview_example(self, db, mock_conn):
        """Test with realistic interview data (like 1oKru2X3AvU)"""
        conn, cursor = mock_conn
        
        # Typical interview: 149 segments, ~52% Chaffee, ~48% Guest
        segments = []
        for i in range(149):
            speaker = 'Chaffee' if i % 2 == 0 else 'GUEST'
            segments.append({
                'speaker_label': speaker,
                'text': f'Segment {i}',
                'start': i*10,
                'end': i*10+8
            })
        
        db._classify_video_type('real_interview', segments, conn)
        
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0]
        # ~50% guest -> interview
        assert 'interview' in call_args[0] or call_args[1][0] == 'interview'
    
    def test_commit_called_after_update(self, db, mock_conn):
        """Test that commit is called after UPDATE"""
        conn, cursor = mock_conn
        
        segments = [{'speaker_label': 'Chaffee', 'text': 'Segment 1'}]
        
        db._classify_video_type('test_video_10', segments, conn)
        
        # Verify commit was called
        conn.commit.assert_called_once()
    
    def test_update_query_structure(self, db, mock_conn):
        """Test that UPDATE query has correct structure"""
        conn, cursor = mock_conn
        
        segments = [{'speaker_label': 'Chaffee', 'text': 'Segment 1'}]
        
        db._classify_video_type('test_video_11', segments, conn)
        
        # Check UPDATE query structure
        cursor.execute.assert_called_once()
        query, params = cursor.execute.call_args[0]
        
        assert 'UPDATE segments' in query
        assert 'SET video_type' in query
        assert 'WHERE video_id' in query
        assert params[1] == 'test_video_11'  # video_id parameter


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
