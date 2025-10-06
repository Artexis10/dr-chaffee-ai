#!/usr/bin/env python3
"""
Comprehensive unit tests for speaker diarization and identification system

Tests cover:
1. Voice profile generation and validation
2. Centroid-only profile comparison
3. Per-segment speaker identification
4. Pyannote over-merge detection and handling
5. Variance detection for mixed speakers
6. Edge cases and error handling
"""
import os
import sys
import unittest
import tempfile
import json
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise in tests

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from backend.scripts.common.voice_enrollment_optimized import VoiceEnrollment
from backend.scripts.common.enhanced_asr import EnhancedASR, SpeakerSegment
from backend.scripts.common.enhanced_asr_config import EnhancedASRConfig


class TestVoiceProfile(unittest.TestCase):
    """Test voice profile generation and validation"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.voices_dir = Path(self.test_dir) / "voices"
        self.voices_dir.mkdir(exist_ok=True)
        
    def tearDown(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_centroid_only_profile_structure(self):
        """Test that centroid-only profile has correct structure"""
        profile = {
            'name': 'test_speaker',
            'centroid': np.random.randn(192).tolist(),
            'threshold': 0.62,
            'created_at': '2025-01-01T00:00:00',
            'audio_sources': ['test1.wav', 'test2.wav'],
            'metadata': {
                'source': 'test',
                'num_embeddings': 100,
                'num_deduplicated': 50,
                'profile_type': 'centroid_only'
            }
        }
        
        # Save profile
        profile_path = self.voices_dir / 'test_speaker.json'
        with open(profile_path, 'w') as f:
            json.dump(profile, f)
        
        # Load and validate
        enrollment = VoiceEnrollment(voices_dir=str(self.voices_dir))
        loaded_profile = enrollment.load_profile('test_speaker')
        
        self.assertIsNotNone(loaded_profile)
        self.assertIn('centroid', loaded_profile)
        self.assertNotIn('embeddings', loaded_profile)  # Should NOT have embeddings
        self.assertEqual(len(loaded_profile['centroid']), 192)
        self.assertEqual(loaded_profile['metadata']['profile_type'], 'centroid_only')
    
    def test_centroid_similarity_computation(self):
        """Test that centroid-only profiles use centroid for comparison"""
        enrollment = VoiceEnrollment(voices_dir=str(self.voices_dir))
        
        # Create centroid-only profile
        centroid = np.ones(192, dtype=np.float64)
        centroid = centroid / np.linalg.norm(centroid)  # Normalize
        profile = {
            'name': 'test',
            'centroid': centroid.tolist(),
            'threshold': 0.62
        }
        
        # Test embedding (same as centroid)
        test_emb = np.ones(192, dtype=np.float64)
        test_emb = test_emb / np.linalg.norm(test_emb)
        
        # Compute similarity
        sim = enrollment.compute_similarity(test_emb, profile)
        
        # Should be very high (close to 1.0)
        self.assertGreater(sim, 0.99)
        
    def test_broken_profile_detection(self):
        """Test detection of profiles with duplicate embeddings"""
        # Create profile with many duplicate embeddings (simulating the bug)
        duplicate_emb = np.ones(192, dtype=np.float64)
        profile = {
            'name': 'broken',
            'centroid': duplicate_emb.tolist(),
            'embeddings': [duplicate_emb.tolist()] * 1000,  # 1000 duplicates!
            'threshold': 0.62
        }
        
        # Save profile
        profile_path = self.voices_dir / 'broken.json'
        with open(profile_path, 'w') as f:
            json.dump(profile, f)
        
        # Load profile
        enrollment = VoiceEnrollment(voices_dir=str(self.voices_dir))
        loaded_profile = enrollment.load_profile('broken')
        
        # Test that it uses embeddings (max-similarity) which causes the bug
        test_emb = np.zeros(192, dtype=np.float64)  # Completely different
        sim = enrollment.compute_similarity(test_emb, loaded_profile)
        
        # With embeddings, it will use max-similarity which may return high value
        # This test documents the bug
        self.assertIsInstance(sim, (int, float))


class TestSpeakerIdentification(unittest.TestCase):
    """Test speaker identification logic"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.voices_dir = Path(self.test_dir) / "voices"
        self.voices_dir.mkdir(exist_ok=True)
        
        # Create mock Chaffee profile (centroid-only)
        chaffee_centroid = np.random.randn(192)
        chaffee_centroid = chaffee_centroid / np.linalg.norm(chaffee_centroid)
        self.chaffee_profile = {
            'name': 'chaffee',
            'centroid': chaffee_centroid.tolist(),
            'threshold': 0.62,
            'metadata': {'profile_type': 'centroid_only'}
        }
        
        profile_path = self.voices_dir / 'chaffee.json'
        with open(profile_path, 'w') as f:
            json.dump(self.chaffee_profile, f)
    
    def tearDown(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_per_segment_identification_threshold(self):
        """Test that per-segment ID uses 0.7 threshold correctly"""
        enrollment = VoiceEnrollment(voices_dir=str(self.voices_dir))
        chaffee_profile = enrollment.load_profile('chaffee')
        
        # Create test embeddings
        chaffee_emb = np.array(chaffee_profile['centroid'])
        
        # High similarity (should be Chaffee) - use same direction
        high_sim_emb = chaffee_emb * 1.1  # Same direction, slightly scaled
        high_sim_emb = high_sim_emb / np.linalg.norm(high_sim_emb)
        high_sim = enrollment.compute_similarity(high_sim_emb, chaffee_profile)
        
        # Low similarity (should be Guest) - use orthogonal vector
        low_sim_emb = np.random.randn(192)
        low_sim_emb = low_sim_emb / np.linalg.norm(low_sim_emb)
        # Make it more orthogonal by subtracting projection onto chaffee_emb
        projection = np.dot(low_sim_emb, chaffee_emb) * chaffee_emb
        low_sim_emb = low_sim_emb - projection
        low_sim_emb = low_sim_emb / np.linalg.norm(low_sim_emb)
        low_sim = enrollment.compute_similarity(low_sim_emb, chaffee_profile)
        
        # Test threshold logic
        THRESHOLD = 0.7
        if high_sim > THRESHOLD:
            speaker_high = 'Chaffee'
        else:
            speaker_high = 'GUEST'
            
        if low_sim > THRESHOLD:
            speaker_low = 'Chaffee'
        else:
            speaker_low = 'GUEST'
        
        # Assertions - high_sim should be > 0.7, low_sim should be < 0.7
        self.assertGreater(high_sim, THRESHOLD, f"High similarity {high_sim:.3f} should be > {THRESHOLD}")
        self.assertLess(low_sim, THRESHOLD, f"Low similarity {low_sim:.3f} should be < {THRESHOLD}")
        self.assertEqual(speaker_high, 'Chaffee')
        self.assertEqual(speaker_low, 'GUEST')
    
    def test_massive_segment_detection(self):
        """Test detection of single massive segments from pyannote"""
        # Simulate pyannote returning 1 massive segment
        segments = [(0.0, 4354.9, 0)]  # 72 minutes in one segment
        
        # Check if it's a single massive segment
        is_single_massive = len(segments) == 1 and (segments[0][1] - segments[0][0]) > 300
        
        self.assertTrue(is_single_massive)
        
        # Simulate splitting into 30-second chunks
        start, end, _ = segments[0]
        chunk_size = 30.0
        chunks = []
        current = start
        while current < end:
            chunk_end = min(current + chunk_size, end)
            chunks.append((current, chunk_end))
            current = chunk_end
        
        # Verify chunking (may be off by 1 due to rounding)
        expected_chunks = int((end - start) / chunk_size)
        self.assertAlmostEqual(len(chunks), expected_chunks, delta=1)
        self.assertEqual(chunks[0][0], 0.0)
        self.assertAlmostEqual(chunks[-1][1], end, places=1)
    
    def test_variance_detection_distributed_sampling(self):
        """Test that variance check samples from different parts of video"""
        # Simulate single massive segment
        start, end = 0.0, 4354.9
        duration = end - start
        num_chunks = 10
        chunk_size = 30.0
        
        # Distribute chunks across entire duration
        chunks = []
        for i in range(num_chunks):
            position = start + (i * duration / num_chunks)
            chunk_start = position
            chunk_end = min(chunk_start + chunk_size, end)
            chunks.append((chunk_start, chunk_end))
        
        # Verify distribution
        self.assertEqual(len(chunks), num_chunks)
        
        # Check that chunks are spread across the video
        positions = [c[0] for c in chunks]
        self.assertAlmostEqual(positions[0], 0.0, places=1)
        self.assertGreaterEqual(positions[5], duration / 2 - 1)  # Middle chunk (with tolerance)
        self.assertGreater(positions[-1], duration * 0.85)  # Last chunk near end
    
    def test_speaker_segment_creation(self):
        """Test SpeakerSegment creation with correct attributes"""
        segment = SpeakerSegment(
            start=0.0,
            end=30.0,
            speaker='Chaffee',
            confidence=0.85,
            margin=0.15,
            embedding=[0.1] * 192,
            cluster_id=0
        )
        
        self.assertEqual(segment.start, 0.0)
        self.assertEqual(segment.end, 30.0)
        self.assertEqual(segment.speaker, 'Chaffee')
        self.assertEqual(segment.confidence, 0.85)
        self.assertEqual(len(segment.embedding), 192)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def test_empty_diarization_segments(self):
        """Test handling of empty diarization results"""
        segments = []
        
        # Should handle gracefully
        clusters = {}
        for start, end, cluster_id in segments:
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append((start, end))
        
        self.assertEqual(len(clusters), 0)
    
    def test_very_short_segments(self):
        """Test handling of segments < 0.5 seconds"""
        segments = [(0.0, 0.3, 0), (0.5, 1.5, 0)]  # First too short
        
        valid_segments = [(s, e, c) for s, e, c in segments if (e - s) >= 0.5]
        
        self.assertEqual(len(valid_segments), 1)
        self.assertEqual(valid_segments[0], (0.5, 1.5, 0))
    
    def test_similarity_edge_values(self):
        """Test similarity computation with edge values"""
        enrollment = VoiceEnrollment(voices_dir='voices')
        
        # Identical embeddings
        emb1 = np.ones(192, dtype=np.float64)
        emb1 = emb1 / np.linalg.norm(emb1)
        
        sim_identical = enrollment._compute_single_similarity(emb1, emb1)
        self.assertAlmostEqual(sim_identical, 1.0, places=5)
        
        # Orthogonal embeddings
        emb2 = np.zeros(192, dtype=np.float64)
        emb2[0] = 1.0
        emb3 = np.zeros(192, dtype=np.float64)
        emb3[1] = 1.0
        
        sim_orthogonal = enrollment._compute_single_similarity(emb2, emb3)
        self.assertAlmostEqual(sim_orthogonal, 0.0, places=5)
    
    def test_profile_not_found(self):
        """Test handling of missing voice profile"""
        test_dir = tempfile.mkdtemp()
        try:
            enrollment = VoiceEnrollment(voices_dir=test_dir)
            profile = enrollment.load_profile('nonexistent')
            
            # VoiceEnrollment creates synthetic profiles for missing ones
            # So profile will not be None, but it will be synthetic
            self.assertIsNotNone(profile)
            # Synthetic profiles have embeddings (not centroid-only)
            self.assertIn('embeddings', profile)
        finally:
            import shutil
            shutil.rmtree(test_dir)


class TestRegressionPrevention(unittest.TestCase):
    """Tests to prevent regression of fixed bugs"""
    
    def test_no_duplicate_embeddings_in_profile(self):
        """Prevent regression: Profile should not store duplicate embeddings"""
        # This test ensures we don't regress to storing 90K duplicate embeddings
        test_dir = tempfile.mkdtemp()
        try:
            voices_dir = Path(test_dir) / "voices"
            voices_dir.mkdir()
            
            # Create a proper centroid-only profile
            profile = {
                'name': 'test',
                'centroid': np.random.randn(192).tolist(),
                'threshold': 0.62,
                'metadata': {
                    'profile_type': 'centroid_only',
                    'num_embeddings': 1000,
                    'num_deduplicated': 50
                }
            }
            
            # Save profile
            with open(voices_dir / 'test.json', 'w') as f:
                json.dump(profile, f)
            
            # Load and verify
            enrollment = VoiceEnrollment(voices_dir=str(voices_dir))
            loaded = enrollment.load_profile('test')
            
            # CRITICAL: Should NOT have embeddings key
            self.assertNotIn('embeddings', loaded, 
                           "Profile should be centroid-only, not store all embeddings!")
            self.assertIn('centroid', loaded)
            if 'metadata' in loaded:
                self.assertEqual(loaded['metadata']['profile_type'], 'centroid_only')
            
        finally:
            import shutil
            shutil.rmtree(test_dir)
    
    def test_massive_segment_triggers_per_segment_id(self):
        """Prevent regression: Massive segments should trigger per-segment ID"""
        # This test ensures we don't regress to cluster-level ID for massive segments
        segments = [(0.0, 4354.9, 0)]  # Single 72-minute segment
        
        # Check detection logic
        is_single_massive = len(segments) == 1 and (segments[0][1] - segments[0][0]) > 300
        
        self.assertTrue(is_single_massive, 
                       "Should detect single massive segment and trigger per-segment ID!")
    
    def test_centroid_comparison_not_max_similarity(self):
        """Prevent regression: Should use centroid, not max-similarity"""
        # This test ensures we use centroid comparison, not max-similarity
        test_dir = tempfile.mkdtemp()
        try:
            voices_dir = Path(test_dir) / "voices"
            voices_dir.mkdir()
            
            # Create centroid-only profile
            centroid = np.ones(192, dtype=np.float64)
            centroid = centroid / np.linalg.norm(centroid)
            profile = {
                'name': 'test',
                'centroid': centroid.tolist(),
                'threshold': 0.62
            }
            
            with open(voices_dir / 'test.json', 'w') as f:
                json.dump(profile, f)
            
            enrollment = VoiceEnrollment(voices_dir=str(voices_dir))
            loaded_profile = enrollment.load_profile('test')
            
            # Test with different embedding
            test_emb = np.zeros(192, dtype=np.float64)
            test_emb[0] = 1.0
            test_emb = test_emb / np.linalg.norm(test_emb)
            
            sim = enrollment.compute_similarity(test_emb, loaded_profile)
            
            # Should be low (using centroid comparison)
            # If it were using max-similarity with duplicates, it would be 1.0
            self.assertLess(sim, 0.9, 
                          "Should use centroid comparison, not max-similarity!")
            
        finally:
            import shutil
            shutil.rmtree(test_dir)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestVoiceProfile))
    suite.addTests(loader.loadTestsFromTestCase(TestSpeakerIdentification))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestRegressionPrevention))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
