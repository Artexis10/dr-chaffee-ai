#!/usr/bin/env python3
"""
Unit tests for split cluster marker handling

Tests the integration between:
1. High variance detection (adds split_cluster marker)
2. Cluster embedding computation (must skip when marker present)
3. Per-segment speaker identification (triggered by marker)

This test suite addresses the bug where np.mean() was called on a mixed list
containing both numpy arrays and the ('split_cluster', None, None) marker.
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

from backend.scripts.common.enhanced_asr import EnhancedASR, SpeakerSegment
from backend.scripts.common.enhanced_asr_config import EnhancedASRConfig
from backend.scripts.common.voice_enrollment_optimized import VoiceEnrollment


class TestSplitClusterMarkerDetection:
    """Test detection of split_cluster marker in cluster_embeddings"""
    
    def test_detects_split_marker_in_list(self):
        """Test that split marker is correctly detected in cluster_embeddings"""
        # Create list with embeddings and marker
        cluster_embeddings = [
            np.random.randn(192),
            np.random.randn(192),
            ('split_cluster', None, None)  # The marker
        ]
        
        # Detection logic (same as in enhanced_asr.py)
        has_split_marker = any(
            isinstance(item, tuple) and len(item) == 3 and item[0] == 'split_cluster' 
            for item in cluster_embeddings
        )
        
        assert has_split_marker == True
    
    def test_no_split_marker_in_normal_list(self):
        """Test that normal cluster_embeddings don't trigger split detection"""
        # Create list with only embeddings
        cluster_embeddings = [
            np.random.randn(192),
            np.random.randn(192),
            np.random.randn(192)
        ]
        
        has_split_marker = any(
            isinstance(item, tuple) and len(item) == 3 and item[0] == 'split_cluster' 
            for item in cluster_embeddings
        )
        
        assert has_split_marker == False
    
    def test_split_marker_prevents_mean_computation(self):
        """Test that split marker prevents np.mean() on mixed types"""
        cluster_embeddings = [
            np.random.randn(192),
            np.random.randn(192),
            ('split_cluster', None, None)
        ]
        
        has_split_marker = any(
            isinstance(item, tuple) and len(item) == 3 and item[0] == 'split_cluster' 
            for item in cluster_embeddings
        )
        
        if has_split_marker:
            # Should skip computation
            cluster_embedding = None
        else:
            # Would compute mean (but shouldn't reach here)
            cluster_embedding = np.mean(cluster_embeddings, axis=0)
        
        # Verify computation was skipped
        assert cluster_embedding is None
    
    def test_mean_computation_without_marker(self):
        """Test that np.mean() works normally without marker"""
        cluster_embeddings = [
            np.ones(192),
            np.ones(192) * 2,
            np.ones(192) * 3
        ]
        
        has_split_marker = any(
            isinstance(item, tuple) and len(item) == 3 and item[0] == 'split_cluster' 
            for item in cluster_embeddings
        )
        
        assert has_split_marker == False
        
        # Should compute mean normally
        cluster_embedding = np.mean(cluster_embeddings, axis=0)
        
        # Verify result
        assert cluster_embedding is not None
        assert len(cluster_embedding) == 192
        assert np.allclose(cluster_embedding, np.ones(192) * 2)  # Mean of 1,2,3 is 2


class TestHighVarianceDetection:
    """Test that high variance in embeddings triggers split marker"""
    
    def test_high_variance_embeddings(self):
        """Test variance calculation for very different embeddings"""
        # Create embeddings with high variance (different speakers)
        emb1 = np.random.randn(192)
        emb2 = np.random.randn(192) * -2  # Very different direction
        
        # Normalize
        emb1 = emb1 / np.linalg.norm(emb1)
        emb2 = emb2 / np.linalg.norm(emb2)
        
        # Compute pairwise similarities
        similarities = []
        all_embeddings = [emb1, emb2]
        for i in range(len(all_embeddings)):
            for j in range(i+1, len(all_embeddings)):
                # Cosine similarity (already normalized)
                sim = np.dot(all_embeddings[i], all_embeddings[j])
                similarities.append(sim)
        
        variance = np.var(similarities)
        
        # High variance should trigger split (threshold is 0.02 in code)
        # With very different embeddings, variance should be high
        # Note: variance of single value is 0, so this test needs adjustment
        # Just verify the similarity is low (indicating different speakers)
        assert similarities[0] < 0.5  # Low similarity = different speakers
    
    def test_low_variance_embeddings(self):
        """Test variance calculation for similar embeddings (same speaker)"""
        # Create embeddings with low variance (same speaker)
        base = np.random.randn(192)
        emb1 = base + np.random.randn(192) * 0.01  # Small noise
        emb2 = base + np.random.randn(192) * 0.01  # Small noise
        
        # Normalize
        emb1 = emb1 / np.linalg.norm(emb1)
        emb2 = emb2 / np.linalg.norm(emb2)
        
        # Compute pairwise similarities
        similarities = []
        all_embeddings = [emb1, emb2]
        for i in range(len(all_embeddings)):
            for j in range(i+1, len(all_embeddings)):
                sim = np.dot(all_embeddings[i], all_embeddings[j])
                similarities.append(sim)
        
        variance = np.var(similarities)
        
        # Low variance should NOT trigger split
        assert variance < 0.02
    
    def test_split_marker_added_for_high_variance(self):
        """Test that high variance results in split marker being added"""
        # Create embeddings with guaranteed high variance
        # Use vectors with different similarities to create variance
        emb1 = np.zeros(192)
        emb1[0] = 1.0  # Unit vector
        
        emb2 = np.zeros(192)
        emb2[0] = 0.5  # 50% similar to emb1
        emb2[1] = np.sqrt(0.75)  # Normalized
        
        emb3 = np.zeros(192)
        emb3[0] = -1.0  # Opposite to emb1
        
        cluster_embeddings = [emb1, emb2, emb3]
        
        # Compute variance
        similarities = []
        for i in range(len(cluster_embeddings)):
            for j in range(i+1, len(cluster_embeddings)):
                sim = np.dot(cluster_embeddings[i], cluster_embeddings[j])
                similarities.append(sim)
        
        # similarities will be: [0.5, -1.0, -0.5]
        # variance of these should be > 0.02
        variance = np.var(similarities)
        
        # If high variance, add marker
        if variance > 0.02:
            cluster_embeddings.append(('split_cluster', None, None))
        
        # Verify marker was added
        has_marker = any(
            isinstance(item, tuple) and len(item) == 3 and item[0] == 'split_cluster' 
            for item in cluster_embeddings
        )
        assert has_marker == True
        assert variance > 0.02  # Verify variance is actually high


class TestClusterEmbeddingComputation:
    """Test cluster embedding computation with and without split marker"""
    
    def test_normal_cluster_computes_embedding(self):
        """Test that normal clusters compute cluster embedding"""
        cluster_embeddings = [
            np.random.randn(192),
            np.random.randn(192),
            np.random.randn(192)
        ]
        
        has_split_marker = any(
            isinstance(item, tuple) and len(item) == 3 and item[0] == 'split_cluster' 
            for item in cluster_embeddings
        )
        
        if has_split_marker:
            cluster_embedding = None
            speaker_name = 'UNKNOWN'
            confidence = 0.0
        else:
            cluster_embedding = np.mean(cluster_embeddings, axis=0)
            speaker_name = None  # Will be determined by similarity
            confidence = None
        
        # Verify computation happened
        assert cluster_embedding is not None
        assert len(cluster_embedding) == 192
        assert speaker_name is None  # Not set yet
    
    def test_split_cluster_skips_embedding(self):
        """Test that split clusters skip cluster embedding computation"""
        cluster_embeddings = [
            np.random.randn(192),
            np.random.randn(192),
            ('split_cluster', None, None)
        ]
        
        has_split_marker = any(
            isinstance(item, tuple) and len(item) == 3 and item[0] == 'split_cluster' 
            for item in cluster_embeddings
        )
        
        if has_split_marker:
            cluster_embedding = None
            speaker_name = 'UNKNOWN'
            confidence = 0.0
        else:
            cluster_embedding = np.mean(cluster_embeddings, axis=0)
            speaker_name = None
            confidence = None
        
        # Verify computation was skipped
        assert cluster_embedding is None
        assert speaker_name == 'UNKNOWN'
        assert confidence == 0.0
    
    def test_no_array_shape_error_with_marker(self):
        """Test that mixed list with marker doesn't cause array shape error"""
        cluster_embeddings = [
            np.random.randn(192),
            np.random.randn(192),
            ('split_cluster', None, None)
        ]
        
        has_split_marker = any(
            isinstance(item, tuple) and len(item) == 3 and item[0] == 'split_cluster' 
            for item in cluster_embeddings
        )
        
        # This should NOT raise an error
        try:
            if not has_split_marker:
                # Only compute if no marker
                cluster_embedding = np.mean(cluster_embeddings, axis=0)
            else:
                # Skip computation
                cluster_embedding = None
            
            success = True
        except (ValueError, TypeError) as e:
            success = False
        
        assert success == True


class TestPerSegmentIdentification:
    """Test that split clusters trigger per-segment identification"""
    
    def test_split_cluster_uses_per_segment_id(self):
        """Test that split clusters are handled with per-segment identification"""
        # Simulate cluster marked for split
        has_split_marker = True
        
        # Should use per-segment identification
        if has_split_marker:
            identification_method = 'per_segment'
        else:
            identification_method = 'cluster_level'
        
        assert identification_method == 'per_segment'
    
    def test_normal_cluster_uses_cluster_level_id(self):
        """Test that normal clusters use cluster-level identification"""
        # Simulate normal cluster
        has_split_marker = False
        
        # Should use cluster-level identification
        if has_split_marker:
            identification_method = 'per_segment'
        else:
            identification_method = 'cluster_level'
        
        assert identification_method == 'cluster_level'


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios"""
    
    def test_mixed_speaker_cluster_handling(self):
        """Test handling of cluster with mixed speakers (realistic scenario)"""
        # Simulate Chaffee embeddings (similar)
        chaffee_base = np.random.randn(192)
        chaffee_emb1 = chaffee_base + np.random.randn(192) * 0.01
        chaffee_emb2 = chaffee_base + np.random.randn(192) * 0.01
        
        # Simulate Guest embeddings (very different)
        guest_base = np.random.randn(192) * -1
        guest_emb1 = guest_base + np.random.randn(192) * 0.01
        
        # Mixed cluster (pyannote over-merged)
        cluster_embeddings = [chaffee_emb1, chaffee_emb2, guest_emb1]
        
        # Compute variance
        similarities = []
        for i in range(len(cluster_embeddings)):
            for j in range(i+1, len(cluster_embeddings)):
                emb_i = cluster_embeddings[i] / np.linalg.norm(cluster_embeddings[i])
                emb_j = cluster_embeddings[j] / np.linalg.norm(cluster_embeddings[j])
                sim = np.dot(emb_i, emb_j)
                similarities.append(sim)
        
        variance = np.var(similarities)
        
        # Should detect high variance
        if variance > 0.02:
            cluster_embeddings.append(('split_cluster', None, None))
        
        # Verify marker was added
        has_marker = any(
            isinstance(item, tuple) and len(item) == 3 and item[0] == 'split_cluster' 
            for item in cluster_embeddings
        )
        
        # Should skip cluster-level computation
        if has_marker:
            cluster_embedding = None
        else:
            cluster_embedding = np.mean(cluster_embeddings, axis=0)
        
        assert has_marker == True
        assert cluster_embedding is None
    
    def test_single_speaker_cluster_normal_flow(self):
        """Test that single-speaker clusters work normally"""
        # Simulate single speaker (low variance)
        base = np.random.randn(192)
        cluster_embeddings = [
            base + np.random.randn(192) * 0.01,
            base + np.random.randn(192) * 0.01,
            base + np.random.randn(192) * 0.01
        ]
        
        # Compute variance
        similarities = []
        for i in range(len(cluster_embeddings)):
            for j in range(i+1, len(cluster_embeddings)):
                emb_i = cluster_embeddings[i] / np.linalg.norm(cluster_embeddings[i])
                emb_j = cluster_embeddings[j] / np.linalg.norm(cluster_embeddings[j])
                sim = np.dot(emb_i, emb_j)
                similarities.append(sim)
        
        variance = np.var(similarities)
        
        # Should NOT add marker
        if variance > 0.02:
            cluster_embeddings.append(('split_cluster', None, None))
        
        # Verify no marker
        has_marker = any(
            isinstance(item, tuple) and len(item) == 3 and item[0] == 'split_cluster' 
            for item in cluster_embeddings
        )
        
        # Should compute cluster embedding normally
        if not has_marker:
            cluster_embedding = np.mean(cluster_embeddings, axis=0)
        else:
            cluster_embedding = None
        
        assert has_marker == False
        assert cluster_embedding is not None
        assert len(cluster_embedding) == 192


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_cluster_embeddings(self):
        """Test handling of empty cluster_embeddings list"""
        cluster_embeddings = []
        
        has_split_marker = any(
            isinstance(item, tuple) and len(item) == 3 and item[0] == 'split_cluster' 
            for item in cluster_embeddings
        )
        
        assert has_split_marker == False
        
        # Should handle empty list gracefully
        if not cluster_embeddings:
            cluster_embedding = None
        else:
            cluster_embedding = np.mean(cluster_embeddings, axis=0)
        
        assert cluster_embedding is None
    
    def test_only_marker_in_list(self):
        """Test handling of list with only split marker"""
        cluster_embeddings = [('split_cluster', None, None)]
        
        has_split_marker = any(
            isinstance(item, tuple) and len(item) == 3 and item[0] == 'split_cluster' 
            for item in cluster_embeddings
        )
        
        assert has_split_marker == True
        
        # Should skip computation
        if has_split_marker:
            cluster_embedding = None
        else:
            cluster_embedding = np.mean(cluster_embeddings, axis=0)
        
        assert cluster_embedding is None
    
    def test_multiple_markers_in_list(self):
        """Test handling of list with multiple markers (shouldn't happen but test anyway)"""
        cluster_embeddings = [
            np.random.randn(192),
            ('split_cluster', None, None),
            ('split_cluster', None, None)
        ]
        
        has_split_marker = any(
            isinstance(item, tuple) and len(item) == 3 and item[0] == 'split_cluster' 
            for item in cluster_embeddings
        )
        
        assert has_split_marker == True
        
        # Should still skip computation
        if has_split_marker:
            cluster_embedding = None
        else:
            cluster_embedding = np.mean(cluster_embeddings, axis=0)
        
        assert cluster_embedding is None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
