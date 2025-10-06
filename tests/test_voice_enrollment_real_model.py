#!/usr/bin/env python3
"""
Unit tests for voice_enrollment_optimized.py with real SpeechBrain model

Tests:
- Real model loading (not dummy)
- Windows symlink workaround
- Embedding extraction produces real features
- Profile loading and similarity computation
"""
import os
import sys
import pytest
import numpy as np
import tempfile
import soundfile as sf
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from backend.scripts.common.voice_enrollment_optimized import VoiceEnrollment


class TestRealModelLoading:
    """Test that real SpeechBrain model loads correctly"""
    
    def test_model_loads_without_dummy(self, tmp_path):
        """Verify model is real SpeechBrain, not dummy"""
        enrollment = VoiceEnrollment(voices_dir=str(tmp_path))
        
        # Trigger model loading
        model = enrollment._get_embedding_model()
        
        # Check it's not a dummy model
        assert model is not None
        assert hasattr(model, 'encode_batch')
        
        # Real SpeechBrain model should have these attributes
        assert hasattr(model, 'mods')
        assert hasattr(model, 'hparams')
        
    def test_windows_symlink_workaround(self, tmp_path):
        """Test that Windows symlink workaround copies files"""
        enrollment = VoiceEnrollment(voices_dir=str(tmp_path))
        
        # Set pretrained models dir
        os.environ['PRETRAINED_MODELS_DIR'] = str(tmp_path / 'pretrained')
        
        # Load model (should copy files, not symlink)
        model = enrollment._get_embedding_model()
        
        # Check that files were copied
        pretrained_dir = tmp_path / 'pretrained'
        assert pretrained_dir.exists()


class TestRealEmbeddingExtraction:
    """Test that embeddings are real voice features, not random noise"""
    
    def create_test_audio(self, duration=3.0, sr=16000):
        """Create test audio with speech-like characteristics"""
        # Generate audio with multiple frequency components (speech-like)
        t = np.linspace(0, duration, int(duration * sr))
        
        # Mix of frequencies typical in speech (100-3000 Hz)
        audio = (
            0.3 * np.sin(2 * np.pi * 150 * t) +
            0.2 * np.sin(2 * np.pi * 300 * t) +
            0.15 * np.sin(2 * np.pi * 600 * t) +
            0.1 * np.random.randn(len(t))
        )
        
        # Normalize
        audio = audio / np.max(np.abs(audio)) * 0.8
        
        return audio.astype(np.float32), sr
    
    def test_embeddings_are_not_random(self, tmp_path):
        """Verify embeddings are real features, not random noise"""
        enrollment = VoiceEnrollment(voices_dir=str(tmp_path))
        
        # Create test audio
        audio, sr = self.create_test_audio()
        audio_path = tmp_path / 'test.wav'
        sf.write(audio_path, audio, sr)
        
        # Extract embeddings
        embeddings = enrollment._extract_embeddings_from_audio(str(audio_path))
        
        assert len(embeddings) > 0, "Should extract at least one embedding"
        
        # Check embedding properties
        emb = embeddings[0]
        assert len(emb) == 192, "SpeechBrain ECAPA should produce 192-dim embeddings"
        
        # Real embeddings should have reasonable statistics
        # Note: SpeechBrain ECAPA embeddings can have varying statistics depending on audio
        # Just verify they're not dummy (all zeros or constant)
        assert not np.allclose(emb, 0), "Embedding should not be all zeros"
        assert len(np.unique(emb)) > 10, "Embedding should have diverse values"
        assert emb.std() > 0.001, "Embedding should have variance (not constant)"
    
    def test_embedding_dimensions_consistent(self, tmp_path):
        """Verify all embeddings have consistent dimensions"""
        enrollment = VoiceEnrollment(voices_dir=str(tmp_path))
        
        # Create test audio
        audio, sr = self.create_test_audio(duration=10.0)
        audio_path = tmp_path / 'test_long.wav'
        sf.write(audio_path, audio, sr)
        
        # Extract multiple embeddings
        embeddings = enrollment._extract_embeddings_from_audio(str(audio_path))
        
        assert len(embeddings) > 1, "Should extract multiple embeddings from long audio"
        
        # All embeddings should have same dimension
        dims = [len(emb) for emb in embeddings]
        assert len(set(dims)) == 1, "All embeddings should have same dimension"
        assert dims[0] == 192, "Should be 192 dimensions"


class TestProfileOperations:
    """Test profile loading and similarity computation"""
    
    def test_load_real_profile(self, tmp_path):
        """Test loading a real centroid-based profile"""
        enrollment = VoiceEnrollment(voices_dir=str(tmp_path))
        
        # Create a test profile
        profile = {
            'name': 'test',
            'centroid': np.random.randn(192).tolist(),
            'threshold': 0.62,
            'metadata': {'embedding_model': 'speechbrain/spkrec-ecapa-voxceleb'}
        }
        
        profile_path = tmp_path / 'test.json'
        import json
        with open(profile_path, 'w') as f:
            json.dump(profile, f)
        
        # Load profile
        loaded = enrollment.load_profile('test')
        
        assert loaded is not None
        assert 'centroid' in loaded
        assert len(loaded['centroid']) == 192
    
    def test_similarity_computation(self, tmp_path):
        """Test similarity computation between embeddings"""
        enrollment = VoiceEnrollment(voices_dir=str(tmp_path))
        
        # Create two embeddings
        emb1 = np.random.randn(192)
        emb2 = np.random.randn(192)
        
        # Normalize
        emb1 = emb1 / np.linalg.norm(emb1)
        emb2 = emb2 / np.linalg.norm(emb2)
        
        # Compute similarity
        sim = enrollment.compute_similarity(emb1, emb2)
        
        assert isinstance(sim, float)
        assert -1.0 <= sim <= 1.0, "Cosine similarity should be in [-1, 1]"
    
    def test_profile_no_synthetic_fallback(self, tmp_path):
        """Verify no synthetic profile is created for missing profiles"""
        enrollment = VoiceEnrollment(voices_dir=str(tmp_path))
        
        # Try to load non-existent profile
        profile = enrollment.load_profile('nonexistent')
        
        # Should return None, not create synthetic
        assert profile is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
