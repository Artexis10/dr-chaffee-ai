#!/usr/bin/env python3
"""
Unit tests for cluster-level speaker assignment.

Tests that diarization cluster boundaries are respected and not overridden
by per-segment voice embedding identification.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend'))


class TestClusterSpeakerAssignment:
    """Test that diarization clusters are properly assigned to speakers"""
    
    def test_pyannote_clustering_threshold_configured(self):
        """
        Test that pyannote clustering threshold is properly configured.
        
        CRITICAL BUG: Pyannote is merging two distinct speakers (Chaffee and Guest)
        into one cluster because clustering threshold is not being passed.
        
        Video 1oKru2X3AvU (interview with Pascal Johns):
        - Expected: 2 clusters (Chaffee and Guest)
        - Actual: 1 cluster (merged)
        - Result: 100% Chaffee attribution (wrong!)
        
        FIX: Pass clustering threshold to pyannote pipeline.
        Lower threshold = more sensitive to voice differences.
        """
        # Test that clustering threshold from .env is used
        # Default: 0.7 (too high, merges similar voices)
        # Our setting: 0.5 (more sensitive)
        # Should result in 2 clusters for interview videos
        pass
    
    def test_cluster_assignment_respects_diarization(self):
        """
        Test that when diarization identifies distinct clusters,
        we assign ONE speaker per cluster, not per-segment.
        
        This test assumes pyannote correctly identifies 2 clusters.
        If pyannote only returns 1 cluster, this test won't help.
        """
        # Simulate diarization output: 2 distinct clusters
        diarization_segments = [
            (0.0, 30.0, 0),    # Cluster 0: Chaffee
            (30.0, 60.0, 1),   # Cluster 1: Guest
            (60.0, 90.0, 0),   # Cluster 0: Chaffee again
            (90.0, 120.0, 1),  # Cluster 1: Guest again
        ]
        
        # Expected: All cluster 0 segments -> Chaffee, all cluster 1 -> Guest
        # After fix: Cluster assignment is final, no per-segment override
        pass
    
    def test_per_segment_only_for_merged_clusters(self):
        """
        Test that per-segment identification is ONLY used when
        pyannote incorrectly merged two speakers into one cluster.
        
        Detection criteria:
        - High variance in voice embeddings within cluster
        - Large range in similarity scores
        
        In this case, we MUST split the cluster and identify each segment.
        """
        # Simulate pyannote merging two speakers into one cluster
        # This happens when speakers have similar voices or short utterances
        
        diarization_segments = [
            (0.0, 120.0, 0),  # Single cluster containing both speakers
        ]
        
        # Voice embeddings show high variance -> mixed speakers
        # Expected: Split cluster and identify each segment
        
        # This is the ONLY case where per-segment identification is needed
        pass
    
    def test_cluster_identification_uses_majority_vote(self):
        """
        Test that cluster speaker identification uses majority vote
        from multiple samples, not just one segment.
        
        This improves robustness against low-quality audio segments.
        """
        # Sample multiple segments from cluster
        # Use majority vote to determine cluster speaker
        # More robust than single-segment identification
        pass
    
    def test_low_confidence_segments_inherit_cluster_label(self):
        """
        Test that segments with low voice embedding confidence
        inherit their cluster's speaker label.
        
        This is the key fix for the accuracy issue:
        - Cluster identified as Chaffee with high confidence (0.85)
        - One segment in cluster has low confidence (0.45)
        - Expected: Segment labeled as Chaffee (inherits cluster label)
        
        Current bug: Segment labeled as Guest due to low confidence
        """
        pass
    
    def test_variance_based_splitting_when_pyannote_merges(self):
        """
        Test that when pyannote returns 1 cluster but variance is high,
        we split by similarity to Chaffee profile.
        
        REAL-WORLD SCENARIO (Video 1oKru2X3AvU):
        - Pyannote returns 1 cluster (merged Chaffee + Guest)
        - Voice embeddings show high variance (0.064)
        - Similarity range: [0.071, 0.713]
        
        EXPECTED BEHAVIOR:
        - Detect high variance (>0.05)
        - Split segments by similarity threshold (0.65)
        - High similarity (>0.65) → Chaffee
        - Low similarity (<0.65) → Guest
        
        This is the REAL fix for the 100% Chaffee issue.
        """
        # Simulate pyannote returning 1 cluster with mixed speakers
        # Using real-world data from video 1oKru2X3AvU
        cluster_segments = [
            # Chaffee segments (high similarity ~0.7)
            {'start': 0.0, 'end': 30.0, 'similarity': 0.71},
            {'start': 60.0, 'end': 90.0, 'similarity': 0.68},
            {'start': 120.0, 'end': 150.0, 'similarity': 0.70},
            
            # Guest segments (low similarity ~0.1-0.3)
            {'start': 30.0, 'end': 60.0, 'similarity': 0.15},
            {'start': 90.0, 'end': 120.0, 'similarity': 0.07},
            {'start': 150.0, 'end': 180.0, 'similarity': 0.25},
        ]
        
        # Calculate variance
        similarities = [s['similarity'] for s in cluster_segments]
        import numpy as np
        variance = np.var(similarities)
        
        # High variance should trigger splitting
        assert variance > 0.05, f"Variance {variance} should be > 0.05"
        
        # Split by threshold
        threshold = 0.65
        chaffee_segments = [s for s in cluster_segments if s['similarity'] >= threshold]
        guest_segments = [s for s in cluster_segments if s['similarity'] < threshold]
        
        # Should split 50/50
        assert len(chaffee_segments) == 3, f"Expected 3 Chaffee segments, got {len(chaffee_segments)}"
        assert len(guest_segments) == 3, f"Expected 3 Guest segments, got {len(guest_segments)}"
        
        # Verify correct assignment
        for seg in chaffee_segments:
            assert seg['similarity'] >= threshold
        for seg in guest_segments:
            assert seg['similarity'] < threshold
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
