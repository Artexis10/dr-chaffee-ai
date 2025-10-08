#!/usr/bin/env python3
"""
Integration test for speaker identification accuracy.

Tests that speaker identification correctly attributes segments to the right speaker,
especially in interview scenarios with two speakers.
"""
import pytest
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend'))

from scripts.common.enhanced_asr import EnhancedASR, EnhancedASRConfig
from scripts.common.voice_enrollment_optimized import VoiceEnrollment


class TestSpeakerAccuracy:
    """Test speaker identification accuracy"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        config = EnhancedASRConfig()
        config.chaffee_min_sim = 0.62
        config.device = 'cpu'  # Use CPU for testing
        return config
    
    def test_interview_speaker_attribution(self):
        """
        Test that interview videos correctly identify both speakers.
        
        Video 1oKru2X3AvU is an interview with Pascal Johns.
        Expected: ~50% Chaffee, ~50% Guest (rough estimate)
        
        This test catches regressions where Chaffee segments are mislabeled as Guest.
        """
        # This is a regression test for the issue where segments #97-105
        # were incorrectly labeled as GUEST when they should be Chaffee
        
        # Load segments from database
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        video_id = '1oKru2X3AvU'
        
        cur.execute("""
            SELECT start_sec, end_sec, text, speaker_label, speaker_conf
            FROM segments
            WHERE video_id = %s
            ORDER BY start_sec
        """, (video_id,))
        
        segments = cur.fetchall()
        cur.close()
        conn.close()
        
        if not segments:
            pytest.skip(f"Video {video_id} not in database")
        
        # Analyze speaker distribution
        chaffee_count = sum(1 for s in segments if s[3] == 'Chaffee')
        guest_count = sum(1 for s in segments if s[3] == 'GUEST')
        total = len(segments)
        
        chaffee_pct = (chaffee_count / total) * 100
        guest_pct = (guest_count / total) * 100
        
        print(f"\nSpeaker distribution for {video_id}:")
        print(f"  Chaffee: {chaffee_count}/{total} ({chaffee_pct:.1f}%)")
        print(f"  Guest: {guest_count}/{total} ({guest_pct:.1f}%)")
        
        # Check for suspicious patterns
        # 1. Long stretches of low-confidence GUEST labels
        suspicious_guest_segments = []
        for i, seg in enumerate(segments):
            start, end, text, speaker, conf = seg
            if speaker == 'GUEST' and conf and conf < 0.6:
                suspicious_guest_segments.append((i, start, end, conf, text[:80]))
        
        if suspicious_guest_segments:
            print(f"\nWARNING: Found {len(suspicious_guest_segments)} suspicious GUEST segments (conf < 0.6):")
            for i, start, end, conf, text in suspicious_guest_segments[:5]:
                print(f"  Segment #{i}: {start:.1f}-{end:.1f}s (conf={conf:.2f}): {text}...")
        
        # 2. Check for unrealistic distributions
        # In an interview, neither speaker should dominate > 80%
        assert chaffee_pct < 80, f"Chaffee dominates {chaffee_pct:.1f}% - likely misattribution"
        assert guest_pct < 80, f"Guest dominates {guest_pct:.1f}% - likely misattribution"
        
        # 3. Both speakers should be present
        assert chaffee_count > 0, "No Chaffee segments found"
        assert guest_count > 0, "No Guest segments found"
        
        # 4. Check for low-confidence segments
        low_conf_threshold = 0.5
        low_conf_segments = [s for s in segments if s[4] and s[4] < low_conf_threshold]
        low_conf_pct = (len(low_conf_segments) / total) * 100
        
        print(f"  Low confidence (<{low_conf_threshold}): {len(low_conf_segments)}/{total} ({low_conf_pct:.1f}%)")
        
        # Warn if > 10% of segments have low confidence
        if low_conf_pct > 10:
            pytest.fail(f"Too many low-confidence segments: {low_conf_pct:.1f}% (threshold: 10%)")
    
    def test_monologue_speaker_attribution(self):
        """
        Test that monologue videos correctly identify 100% Chaffee.
        
        This catches regressions where solo Chaffee content is mislabeled as Guest.
        """
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Find a monologue video (no guest in title)
        cur.execute("""
            SELECT s.source_id, s.title, COUNT(*) as seg_count,
                   SUM(CASE WHEN seg.speaker_label = 'Chaffee' THEN 1 ELSE 0 END) as chaffee_count,
                   SUM(CASE WHEN seg.speaker_label = 'GUEST' THEN 1 ELSE 0 END) as guest_count
            FROM sources s
            JOIN segments seg ON s.source_id = seg.video_id
            WHERE s.title NOT LIKE '%interview%'
              AND s.title NOT LIKE '%with %'
              AND s.title NOT LIKE '%| %'  -- Usually indicates guest name
            GROUP BY s.source_id, s.title
            HAVING COUNT(*) > 10
            LIMIT 1
        """)
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if not result:
            pytest.skip("No monologue videos found in database")
        
        video_id, title, total, chaffee_count, guest_count = result
        
        chaffee_pct = (chaffee_count / total) * 100
        guest_pct = (guest_count / total) * 100
        
        print(f"\nMonologue video: {video_id} - {title}")
        print(f"  Chaffee: {chaffee_count}/{total} ({chaffee_pct:.1f}%)")
        print(f"  Guest: {guest_count}/{total} ({guest_pct:.1f}%)")
        
        # Monologue should be > 95% Chaffee
        assert chaffee_pct > 95, f"Monologue should be >95% Chaffee, got {chaffee_pct:.1f}%"
        assert guest_pct < 5, f"Monologue should have <5% Guest, got {guest_pct:.1f}%"
    
    def test_segment_splitting_at_boundaries(self):
        """
        Test that segments are properly split at speaker boundaries.
        
        This catches the regression where segments span multiple speakers.
        """
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Check for suspiciously long segments (> 90s) in interview videos
        cur.execute("""
            SELECT seg.video_id, seg.start_sec, seg.end_sec, 
                   (seg.end_sec - seg.start_sec) as duration,
                   seg.speaker_label, seg.text
            FROM segments seg
            JOIN sources s ON seg.video_id = s.source_id
            WHERE (seg.end_sec - seg.start_sec) > 90
              AND (s.title LIKE '%interview%' OR s.title LIKE '%| %')
            LIMIT 10
        """)
        
        long_segments = cur.fetchall()
        cur.close()
        conn.close()
        
        if long_segments:
            print(f"\nWARNING: Found {len(long_segments)} suspiciously long segments (>90s) in interviews:")
            for video_id, start, end, duration, speaker, text in long_segments:
                print(f"  {video_id}: {start:.1f}-{end:.1f}s ({duration:.1f}s) - {speaker}")
                print(f"    Text: {text[:100]}...")
            
            # Long segments in interviews likely span multiple speakers
            pytest.fail(f"Found {len(long_segments)} segments >90s in interview videos - likely not split at speaker boundaries")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '-s'])
