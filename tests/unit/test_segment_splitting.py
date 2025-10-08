#!/usr/bin/env python3
"""
Unit tests for segment splitting at speaker boundaries.

Tests the _split_segments_at_speaker_boundaries() function that prevents
segments from spanning multiple speakers.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend'))

from backend.scripts.common.enhanced_asr import EnhancedASR, TranscriptionResult


class TestSegmentSplitting:
    """Test segment splitting at diarization boundaries"""
    
    @pytest.fixture
    def enhanced_asr(self):
        """Create EnhancedASR instance with mocked config"""
        config = Mock()
        config.whisper = Mock()
        config.quality = Mock()
        config.device = 'cpu'
        config.chaffee_min_sim = 0.62
        config.unknown_label = 'UNKNOWN'
        return EnhancedASR(config)
    
    def test_no_split_needed(self, enhanced_asr):
        """Test segments that don't cross speaker boundaries"""
        # Create transcription result
        result = TranscriptionResult(
            segments=[
                {'start': 0.0, 'end': 5.0, 'text': 'hello world', 'words': []},
                {'start': 10.0, 'end': 15.0, 'text': 'goodbye', 'words': []},
            ],
            words=[],
            metadata={}
        )
        
        # Diarization segments (no boundaries crossed)
        diarization = [
            (0.0, 8.0, 0),   # Speaker 0: 0-8s
            (8.0, 20.0, 1),  # Speaker 1: 8-20s
        ]
        
        split_result = enhanced_asr._split_segments_at_speaker_boundaries(result, diarization)
        
        # Should have same number of segments (no splits)
        assert len(split_result.segments) == 2
        assert split_result.segments[0]['text'] == 'hello world'
        assert split_result.segments[1]['text'] == 'goodbye'
    
    def test_split_at_boundary(self, enhanced_asr):
        """Test segment that crosses speaker boundary"""
        # Create segment that spans 0-10s with speaker change at 5s
        words = [
            {'start': 0.0, 'end': 1.0, 'word': 'hello'},
            {'start': 1.0, 'end': 2.0, 'word': 'world'},
            {'start': 6.0, 'end': 7.0, 'word': 'goodbye'},
            {'start': 7.0, 'end': 8.0, 'word': 'friend'},
        ]
        
        result = TranscriptionResult(
            segments=[
                {'start': 0.0, 'end': 10.0, 'text': 'hello world goodbye friend', 'words': words},
            ],
            words=[],
            metadata={}
        )
        
        # Diarization: speaker change at 5s
        diarization = [
            (0.0, 5.0, 0),   # Speaker 0: 0-5s
            (5.0, 10.0, 1),  # Speaker 1: 5-10s
        ]
        
        split_result = enhanced_asr._split_segments_at_speaker_boundaries(result, diarization)
        
        # Should split into 2 segments
        assert len(split_result.segments) == 2
        
        # First segment: 0-5s with words before boundary
        assert split_result.segments[0]['start'] == 0.0
        assert split_result.segments[0]['end'] == 5.0
        assert 'hello world' in split_result.segments[0]['text']
        
        # Second segment: 5-10s with words after boundary
        assert split_result.segments[1]['start'] == 5.0
        assert split_result.segments[1]['end'] == 10.0
        assert 'goodbye friend' in split_result.segments[1]['text']
    
    def test_multiple_boundaries(self, enhanced_asr):
        """Test segment crossing multiple speaker boundaries"""
        words = [
            {'start': 0.0, 'end': 1.0, 'word': 'one'},
            {'start': 3.0, 'end': 4.0, 'word': 'two'},
            {'start': 6.0, 'end': 7.0, 'word': 'three'},
        ]
        
        result = TranscriptionResult(
            segments=[
                {'start': 0.0, 'end': 10.0, 'text': 'one two three', 'words': words},
            ],
            words=[],
            metadata={}
        )
        
        # Multiple speaker changes
        diarization = [
            (0.0, 2.0, 0),   # Speaker 0
            (2.0, 5.0, 1),   # Speaker 1
            (5.0, 10.0, 0),  # Speaker 0 again
        ]
        
        split_result = enhanced_asr._split_segments_at_speaker_boundaries(result, diarization)
        
        # Should split into 3 segments
        assert len(split_result.segments) == 3
    
    def test_segment_before_diarization_starts(self, enhanced_asr):
        """Test segment that exists before diarization starts"""
        words = [
            {'start': 0.0, 'end': 1.0, 'word': 'early'},
            {'start': 1.0, 'end': 2.0, 'word': 'bird'},
        ]
        
        result = TranscriptionResult(
            segments=[
                {'start': 0.0, 'end': 3.0, 'text': 'early bird', 'words': words},
            ],
            words=[],
            metadata={}
        )
        
        # Diarization starts at 5s (missing first 5 seconds)
        diarization = [
            (5.0, 10.0, 0),
        ]
        
        split_result = enhanced_asr._split_segments_at_speaker_boundaries(result, diarization)
        
        # Should handle segment before diarization
        # With 0.0 boundary added, should split at 5.0
        assert len(split_result.segments) >= 1
    
    def test_empty_segments(self, enhanced_asr):
        """Test with empty segment list"""
        result = TranscriptionResult(
            segments=[],
            words=[],
            metadata={}
        )
        
        diarization = [(0.0, 10.0, 0)]
        
        split_result = enhanced_asr._split_segments_at_speaker_boundaries(result, diarization)
        
        assert len(split_result.segments) == 0
    
    def test_empty_diarization(self, enhanced_asr):
        """Test with empty diarization"""
        result = TranscriptionResult(
            segments=[
                {'start': 0.0, 'end': 5.0, 'text': 'hello', 'words': []},
            ],
            words=[],
            metadata={}
        )
        
        split_result = enhanced_asr._split_segments_at_speaker_boundaries(result, [])
        
        # Should return unchanged
        assert len(split_result.segments) == 1
    
    def test_metadata_preserved(self, enhanced_asr):
        """Test that segment metadata is preserved after split"""
        words = [
            {'start': 0.0, 'end': 1.0, 'word': 'hello'},
            {'start': 6.0, 'end': 7.0, 'word': 'world'},
        ]
        
        result = TranscriptionResult(
            segments=[
                {
                    'start': 0.0,
                    'end': 10.0,
                    'text': 'hello world',
                    'words': words,
                    'avg_logprob': -0.5,
                    'compression_ratio': 1.8,
                    'no_speech_prob': 0.01
                },
            ],
            words=[],
            metadata={}
        )
        
        diarization = [
            (0.0, 5.0, 0),
            (5.0, 10.0, 1),
        ]
        
        split_result = enhanced_asr._split_segments_at_speaker_boundaries(result, diarization)
        
        # Check metadata preserved
        for seg in split_result.segments:
            assert 'avg_logprob' in seg
            assert 'compression_ratio' in seg
            assert 'no_speech_prob' in seg
    
    def test_word_assignment_accuracy(self, enhanced_asr):
        """Test that words are correctly assigned to split segments"""
        words = [
            {'start': 0.5, 'end': 1.5, 'word': 'before'},
            {'start': 2.0, 'end': 3.0, 'word': 'boundary'},
            {'start': 5.5, 'end': 6.5, 'word': 'after'},
        ]
        
        result = TranscriptionResult(
            segments=[
                {'start': 0.0, 'end': 10.0, 'text': 'before boundary after', 'words': words},
            ],
            words=[],
            metadata={}
        )
        
        # Boundary at 5.0s
        diarization = [
            (0.0, 5.0, 0),
            (5.0, 10.0, 1),
        ]
        
        split_result = enhanced_asr._split_segments_at_speaker_boundaries(result, diarization)
        
        # First segment should have words before 5.0s
        first_seg_words = split_result.segments[0]['words']
        assert all(w['start'] < 5.0 for w in first_seg_words)
        
        # Second segment should have words after 5.0s
        second_seg_words = split_result.segments[1]['words']
        assert all(w['start'] >= 5.0 for w in second_seg_words)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
