#!/usr/bin/env python3
"""
Unit tests for asr_diarize_v4 module

Tests the new faster-whisper + pyannote v4 pipeline that replaces WhisperX.
"""
import os
import sys
import pytest
import numpy as np
import tempfile
import soundfile as sf
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from backend.scripts.common.asr_diarize_v4 import (
    WordItem,
    Turn,
    TranscriptSegment,
    assign_speakers_to_words,
    words_to_segments,
    get_speaker_stats
)


class TestWordItem:
    """Test WordItem dataclass"""
    
    def test_word_item_creation(self):
        """Test creating a WordItem"""
        word = WordItem(start=0.0, end=1.0, word="hello", prob=0.95)
        
        assert word.start == 0.0
        assert word.end == 1.0
        assert word.word == "hello"
        assert word.prob == 0.95
        assert word.speaker is None
    
    def test_word_item_with_speaker(self):
        """Test WordItem with speaker label"""
        word = WordItem(start=0.0, end=1.0, word="hello", speaker="SPEAKER_0")
        
        assert word.speaker == "SPEAKER_0"


class TestTurn:
    """Test Turn dataclass"""
    
    def test_turn_creation(self):
        """Test creating a Turn"""
        turn = Turn(start=0.0, end=10.0, speaker="SPEAKER_0")
        
        assert turn.start == 0.0
        assert turn.end == 10.0
        assert turn.speaker == "SPEAKER_0"


class TestSpeakerAssignment:
    """Test assigning speakers to words"""
    
    def test_assign_speakers_basic(self):
        """Test basic speaker assignment"""
        words = [
            WordItem(start=0.0, end=1.0, word="hello"),
            WordItem(start=1.0, end=2.0, word="world"),
            WordItem(start=5.0, end=6.0, word="goodbye"),
        ]
        
        turns = [
            Turn(start=0.0, end=3.0, speaker="SPEAKER_0"),
            Turn(start=3.0, end=7.0, speaker="SPEAKER_1"),
        ]
        
        result = assign_speakers_to_words(words, turns)
        
        assert result[0].speaker == "SPEAKER_0"  # hello
        assert result[1].speaker == "SPEAKER_0"  # world
        assert result[2].speaker == "SPEAKER_1"  # goodbye
    
    def test_assign_speakers_word_midpoint(self):
        """Test that word midpoint is used for assignment"""
        words = [
            WordItem(start=2.5, end=3.5, word="test"),  # midpoint = 3.0
        ]
        
        turns = [
            Turn(start=0.0, end=3.0, speaker="SPEAKER_0"),
            Turn(start=3.0, end=6.0, speaker="SPEAKER_1"),
        ]
        
        result = assign_speakers_to_words(words, turns)
        
        # Midpoint is exactly 3.0, which is the boundary
        # Should be assigned to SPEAKER_1 (turn.start <= word_mid < turn.end)
        assert result[0].speaker == "SPEAKER_1"
    
    def test_assign_speakers_no_turns(self):
        """Test assignment with no diarization turns"""
        words = [
            WordItem(start=0.0, end=1.0, word="hello"),
        ]
        
        result = assign_speakers_to_words(words, [])
        
        assert result[0].speaker is None
    
    def test_assign_speakers_word_outside_turns(self):
        """Test word that doesn't fall in any turn"""
        words = [
            WordItem(start=10.0, end=11.0, word="orphan"),
        ]
        
        turns = [
            Turn(start=0.0, end=5.0, speaker="SPEAKER_0"),
        ]
        
        result = assign_speakers_to_words(words, turns)
        
        assert result[0].speaker is None


class TestSegmentCreation:
    """Test creating segments from words"""
    
    def test_words_to_segments_basic(self):
        """Test basic segment creation"""
        words = [
            WordItem(start=0.0, end=1.0, word="hello", speaker="SPEAKER_0"),
            WordItem(start=1.0, end=2.0, word="world", speaker="SPEAKER_0"),
        ]
        
        segments = words_to_segments(words)
        
        assert len(segments) == 1
        assert segments[0].start == 0.0
        assert segments[0].end == 2.0
        assert segments[0].text == "hello world"
        assert segments[0].speaker == "SPEAKER_0"
        assert len(segments[0].words) == 2
    
    def test_words_to_segments_speaker_change(self):
        """Test segment split on speaker change"""
        words = [
            WordItem(start=0.0, end=1.0, word="hello", speaker="SPEAKER_0"),
            WordItem(start=1.0, end=2.0, word="world", speaker="SPEAKER_0"),
            WordItem(start=2.0, end=3.0, word="goodbye", speaker="SPEAKER_1"),
        ]
        
        segments = words_to_segments(words)
        
        assert len(segments) == 2
        assert segments[0].speaker == "SPEAKER_0"
        assert segments[0].text == "hello world"
        assert segments[1].speaker == "SPEAKER_1"
        assert segments[1].text == "goodbye"
    
    def test_words_to_segments_max_length(self):
        """Test segment split on max length"""
        words = [
            WordItem(start=0.0, end=1.0, word=f"word{i}", speaker="SPEAKER_0")
            for i in range(100)
        ]
        
        # Update end times
        for i, word in enumerate(words):
            word.start = float(i)
            word.end = float(i + 1)
        
        segments = words_to_segments(words, max_segment_length=30.0)
        
        # Should split into multiple segments due to length
        assert len(segments) > 1
        
        # Verify no segment exceeds max length
        for seg in segments:
            assert (seg.end - seg.start) <= 30.0
    
    def test_words_to_segments_max_words(self):
        """Test segment split on max words"""
        words = [
            WordItem(start=float(i), end=float(i+0.5), word=f"word{i}", speaker="SPEAKER_0")
            for i in range(100)
        ]
        
        segments = words_to_segments(words, max_words_per_segment=20)
        
        # Should split into multiple segments
        assert len(segments) > 1
        
        # Verify no segment exceeds max words
        for seg in segments:
            assert len(seg.words) <= 20
    
    def test_words_to_segments_empty(self):
        """Test with empty word list"""
        segments = words_to_segments([])
        
        assert len(segments) == 0


class TestSpeakerStats:
    """Test speaker statistics"""
    
    def test_get_speaker_stats_basic(self):
        """Test basic speaker statistics"""
        segments = [
            TranscriptSegment(start=0.0, end=10.0, text="hello", speaker="SPEAKER_0"),
            TranscriptSegment(start=10.0, end=20.0, text="world", speaker="SPEAKER_1"),
            TranscriptSegment(start=20.0, end=30.0, text="goodbye", speaker="SPEAKER_0"),
        ]
        
        stats = get_speaker_stats(segments)
        
        assert stats["total_segments"] == 3
        assert stats["total_duration"] == 30.0
        assert stats["num_speakers"] == 2
        assert "SPEAKER_0" in stats["speakers"]
        assert "SPEAKER_1" in stats["speakers"]
        assert stats["speakers"]["SPEAKER_0"]["count"] == 2
        assert stats["speakers"]["SPEAKER_0"]["duration"] == 20.0
        assert stats["speakers"]["SPEAKER_1"]["count"] == 1
        assert stats["speakers"]["SPEAKER_1"]["duration"] == 10.0
    
    def test_get_speaker_stats_with_words(self):
        """Test speaker stats with word counts"""
        words1 = [WordItem(start=0.0, end=1.0, word="hello")]
        words2 = [WordItem(start=10.0, end=11.0, word="world"), WordItem(start=11.0, end=12.0, word="test")]
        
        segments = [
            TranscriptSegment(start=0.0, end=10.0, text="hello", speaker="SPEAKER_0", words=words1),
            TranscriptSegment(start=10.0, end=20.0, text="world test", speaker="SPEAKER_1", words=words2),
        ]
        
        stats = get_speaker_stats(segments)
        
        assert stats["speakers"]["SPEAKER_0"]["words"] == 1
        assert stats["speakers"]["SPEAKER_1"]["words"] == 2
    
    def test_get_speaker_stats_unknown_speaker(self):
        """Test stats with None speaker (treated as UNKNOWN)"""
        segments = [
            TranscriptSegment(start=0.0, end=10.0, text="hello", speaker=None),
        ]
        
        stats = get_speaker_stats(segments)
        
        assert "UNKNOWN" in stats["speakers"]
        assert stats["speakers"]["UNKNOWN"]["count"] == 1


class TestIntegration:
    """Integration tests for the pipeline"""
    
    def test_full_pipeline_mock(self):
        """Test full pipeline with mocked transcription and diarization"""
        # This would require mocking faster_whisper and pyannote
        # For now, just verify the functions can be called
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
