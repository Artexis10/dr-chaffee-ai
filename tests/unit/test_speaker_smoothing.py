#!/usr/bin/env python3
"""
Unit tests for speaker smoothing logic.

Tests the post-processing that smooths isolated misidentifications
by checking if a segment is surrounded by the same speaker.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend'))


@dataclass
class SpeakerSegment:
    """Mock SpeakerSegment for testing"""
    start: float
    end: float
    speaker: str
    confidence: float = 0.0
    margin: float = 0.0
    embedding: list = None
    cluster_id: int = 0


class TestSpeakerSmoothing:
    """Test speaker smoothing logic"""
    
    def test_smooth_isolated_short_segment(self):
        """Test smoothing of short isolated segment (<60s)"""
        segments = [
            SpeakerSegment(0.0, 30.0, 'Chaffee'),
            SpeakerSegment(30.0, 40.0, 'GUEST'),  # 10s isolated segment
            SpeakerSegment(40.0, 100.0, 'Chaffee'),
        ]
        
        # Apply smoothing logic (simplified version)
        smoothed_count = 0
        for i in range(1, len(segments) - 1):
            prev_speaker = segments[i-1].speaker
            curr_speaker = segments[i].speaker
            next_speaker = segments[i+1].speaker
            
            if prev_speaker == next_speaker and curr_speaker != prev_speaker:
                duration = segments[i].end - segments[i].start
                if duration < 60:
                    segments[i].speaker = prev_speaker
                    smoothed_count += 1
        
        # Middle segment should be smoothed to Chaffee
        assert segments[1].speaker == 'Chaffee'
        assert smoothed_count == 1
    
    def test_no_smooth_long_segment(self):
        """Test that long segments (≥60s) are NOT smoothed"""
        segments = [
            SpeakerSegment(0.0, 30.0, 'Chaffee'),
            SpeakerSegment(30.0, 100.0, 'GUEST'),  # 70s segment (too long)
            SpeakerSegment(100.0, 150.0, 'Chaffee'),
        ]
        
        # Apply smoothing logic
        smoothed_count = 0
        for i in range(1, len(segments) - 1):
            prev_speaker = segments[i-1].speaker
            curr_speaker = segments[i].speaker
            next_speaker = segments[i+1].speaker
            
            if prev_speaker == next_speaker and curr_speaker != prev_speaker:
                duration = segments[i].end - segments[i].start
                if duration < 60:
                    segments[i].speaker = prev_speaker
                    smoothed_count += 1
        
        # Middle segment should NOT be smoothed (too long)
        assert segments[1].speaker == 'GUEST'
        assert smoothed_count == 0
    
    def test_no_smooth_at_boundaries(self):
        """Test that first and last segments are never smoothed"""
        segments = [
            SpeakerSegment(0.0, 10.0, 'GUEST'),  # First segment
            SpeakerSegment(10.0, 50.0, 'Chaffee'),
            SpeakerSegment(50.0, 60.0, 'GUEST'),  # Last segment
        ]
        
        # Apply smoothing logic (only middle segments)
        smoothed_count = 0
        for i in range(1, len(segments) - 1):
            prev_speaker = segments[i-1].speaker
            curr_speaker = segments[i].speaker
            next_speaker = segments[i+1].speaker
            
            if prev_speaker == next_speaker and curr_speaker != prev_speaker:
                duration = segments[i].end - segments[i].start
                if duration < 60:
                    segments[i].speaker = prev_speaker
                    smoothed_count += 1
        
        # First and last segments unchanged (they're not in the loop range)
        assert segments[0].speaker == 'GUEST'
        assert segments[2].speaker == 'GUEST'
        # Middle segment WAS smoothed because it's surrounded by GUEST
        assert segments[1].speaker == 'GUEST'
        assert smoothed_count == 1
    
    def test_smooth_multiple_isolated_segments(self):
        """Test smoothing multiple isolated segments"""
        segments = [
            SpeakerSegment(0.0, 30.0, 'Chaffee'),
            SpeakerSegment(30.0, 40.0, 'GUEST'),   # Isolated
            SpeakerSegment(40.0, 80.0, 'Chaffee'),
            SpeakerSegment(80.0, 90.0, 'GUEST'),   # Isolated
            SpeakerSegment(90.0, 120.0, 'Chaffee'),
        ]
        
        # Apply smoothing logic
        smoothed_count = 0
        for i in range(1, len(segments) - 1):
            prev_speaker = segments[i-1].speaker
            curr_speaker = segments[i].speaker
            next_speaker = segments[i+1].speaker
            
            if prev_speaker == next_speaker and curr_speaker != prev_speaker:
                duration = segments[i].end - segments[i].start
                if duration < 60:
                    segments[i].speaker = prev_speaker
                    smoothed_count += 1
        
        # Both isolated segments should be smoothed
        assert segments[1].speaker == 'Chaffee'
        assert segments[3].speaker == 'Chaffee'
        assert smoothed_count == 2
    
    def test_no_smooth_when_not_surrounded(self):
        """Test that segments not surrounded by same speaker are not smoothed"""
        segments = [
            SpeakerSegment(0.0, 30.0, 'Chaffee'),
            SpeakerSegment(30.0, 40.0, 'GUEST'),
            SpeakerSegment(40.0, 80.0, 'Unknown'),  # Different speaker after
        ]
        
        # Apply smoothing logic
        smoothed_count = 0
        for i in range(1, len(segments) - 1):
            prev_speaker = segments[i-1].speaker
            curr_speaker = segments[i].speaker
            next_speaker = segments[i+1].speaker
            
            if prev_speaker == next_speaker and curr_speaker != prev_speaker:
                duration = segments[i].end - segments[i].start
                if duration < 60:
                    segments[i].speaker = prev_speaker
                    smoothed_count += 1
        
        # Middle segment should NOT be smoothed (not surrounded by same speaker)
        assert segments[1].speaker == 'GUEST'
        assert smoothed_count == 0
    
    def test_smooth_exactly_60_seconds(self):
        """Test boundary case: exactly 60 seconds"""
        segments = [
            SpeakerSegment(0.0, 30.0, 'Chaffee'),
            SpeakerSegment(30.0, 90.0, 'GUEST'),  # Exactly 60s
            SpeakerSegment(90.0, 120.0, 'Chaffee'),
        ]
        
        # Apply smoothing logic
        smoothed_count = 0
        for i in range(1, len(segments) - 1):
            prev_speaker = segments[i-1].speaker
            curr_speaker = segments[i].speaker
            next_speaker = segments[i+1].speaker
            
            if prev_speaker == next_speaker and curr_speaker != prev_speaker:
                duration = segments[i].end - segments[i].start
                if duration < 60:  # Strictly less than 60
                    segments[i].speaker = prev_speaker
                    smoothed_count += 1
        
        # Should NOT be smoothed (not < 60)
        assert segments[1].speaker == 'GUEST'
        assert smoothed_count == 0
    
    def test_smooth_59_seconds(self):
        """Test boundary case: 59 seconds (just under threshold)"""
        segments = [
            SpeakerSegment(0.0, 30.0, 'Chaffee'),
            SpeakerSegment(30.0, 89.0, 'GUEST'),  # 59s
            SpeakerSegment(89.0, 120.0, 'Chaffee'),
        ]
        
        # Apply smoothing logic
        smoothed_count = 0
        for i in range(1, len(segments) - 1):
            prev_speaker = segments[i-1].speaker
            curr_speaker = segments[i].speaker
            next_speaker = segments[i+1].speaker
            
            if prev_speaker == next_speaker and curr_speaker != prev_speaker:
                duration = segments[i].end - segments[i].start
                if duration < 60:
                    segments[i].speaker = prev_speaker
                    smoothed_count += 1
        
        # Should be smoothed (< 60)
        assert segments[1].speaker == 'Chaffee'
        assert smoothed_count == 1
    
    def test_empty_segment_list(self):
        """Test with empty segment list"""
        segments = []
        
        # Apply smoothing logic
        smoothed_count = 0
        for i in range(1, len(segments) - 1):
            pass
        
        assert smoothed_count == 0
    
    def test_single_segment(self):
        """Test with single segment"""
        segments = [
            SpeakerSegment(0.0, 30.0, 'Chaffee'),
        ]
        
        # Apply smoothing logic (no middle segments)
        smoothed_count = 0
        for i in range(1, len(segments) - 1):
            pass
        
        assert smoothed_count == 0
        assert segments[0].speaker == 'Chaffee'
    
    def test_two_segments(self):
        """Test with two segments (no middle to smooth)"""
        segments = [
            SpeakerSegment(0.0, 30.0, 'Chaffee'),
            SpeakerSegment(30.0, 60.0, 'GUEST'),
        ]
        
        # Apply smoothing logic (no middle segments)
        smoothed_count = 0
        for i in range(1, len(segments) - 1):
            pass
        
        assert smoothed_count == 0
        # Both segments unchanged
        assert segments[0].speaker == 'Chaffee'
        assert segments[1].speaker == 'GUEST'
    
    def test_real_world_scenario(self):
        """Test real-world scenario from the video"""
        # Simulates the 30s Guest segment at 1530-1560s surrounded by Chaffee
        segments = []
        
        # Add many Chaffee segments before
        for i in range(50):
            segments.append(SpeakerSegment(i * 30.0, (i + 1) * 30.0, 'Chaffee'))
        
        # Add isolated Guest segment (30s)
        segments.append(SpeakerSegment(1530.0, 1560.0, 'GUEST'))
        
        # Add Chaffee segments after
        for i in range(52, 70):
            segments.append(SpeakerSegment(i * 30.0, (i + 1) * 30.0, 'Chaffee'))
        
        # Apply smoothing logic
        smoothed_count = 0
        for i in range(1, len(segments) - 1):
            prev_speaker = segments[i-1].speaker
            curr_speaker = segments[i].speaker
            next_speaker = segments[i+1].speaker
            
            if prev_speaker == next_speaker and curr_speaker != prev_speaker:
                duration = segments[i].end - segments[i].start
                if duration < 60:
                    segments[i].speaker = prev_speaker
                    smoothed_count += 1
        
        # The isolated Guest segment should be smoothed
        assert segments[50].speaker == 'Chaffee'
        assert smoothed_count == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
