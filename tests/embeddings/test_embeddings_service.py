#!/usr/bin/env python3
"""
Pytest tests for EmbeddingsService
Tests encoding, reranking, and GPU/CPU fallback behavior
"""

import pytest
import numpy as np
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent / 'backend'
sys.path.insert(0, str(backend_dir))

from services.embeddings_service import EmbeddingsService


@pytest.fixture(scope="module")
def cuda_available():
    """Check if CUDA is available"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


@pytest.fixture(scope="module")
def service():
    """Initialize service once for all tests"""
    # Set environment for testing
    os.environ['EMBEDDING_MODEL'] = 'BAAI/bge-small-en-v1.5'
    os.environ['EMBEDDING_DIMENSIONS'] = '384'
    os.environ['ENABLE_RERANKER'] = 'false'  # Disable by default for speed
    
    EmbeddingsService.init_from_env()
    yield EmbeddingsService
    
    # Cleanup
    EmbeddingsService.shutdown()


@pytest.mark.cuda
class TestEmbeddingsServiceGPU:
    """Tests that require CUDA"""
    
    def test_initialization_cuda(self, cuda_available):
        """Test service initializes on CUDA"""
        if not cuda_available:
            pytest.skip("CUDA not available")
        
        os.environ['EMBEDDING_DEVICE'] = 'cuda'
        EmbeddingsService.shutdown()  # Reset
        EmbeddingsService.init_from_env()
        
        assert EmbeddingsService.is_initialized()
        assert EmbeddingsService.get_device() == 'cuda'
        
        EmbeddingsService.shutdown()
    
    def test_encoding_throughput_gpu(self, cuda_available, service):
        """Test GPU encoding throughput is reasonable"""
        if not cuda_available:
            pytest.skip("CUDA not available")
        
        if service.get_device() != 'cuda':
            pytest.skip("Service not on CUDA")
        
        texts = [
            "The carnivore diet involves eating only animal products.",
            "Dr. Chaffee recommends eliminating plant foods for better health.",
            "Many people report improved energy on a meat-based diet."
        ] * 100  # 300 texts
        
        import time
        start = time.time()
        embeddings = service.encode_texts(texts, batch_size=256)
        elapsed = time.time() - start
        
        throughput = len(texts) / elapsed
        
        # GPU should be reasonably fast (>100 texts/sec for bge-small)
        assert throughput > 100, f"GPU throughput too low: {throughput:.1f} texts/sec"
        print(f"GPU throughput: {throughput:.1f} texts/sec")


class TestEmbeddingsServiceBasic:
    """Basic tests that work on CPU or GPU"""
    
    def test_initialization(self, service):
        """Test service initializes successfully"""
        assert service.is_initialized()
        assert service.get_device() in ['cuda', 'cpu']
        assert service.get_embedding_dimensions() == 384
    
    def test_encode_empty_list(self, service):
        """Test encoding empty list returns empty array"""
        embeddings = service.encode_texts([])
        assert len(embeddings) == 0
    
    def test_encode_single_text(self, service):
        """Test encoding single text"""
        texts = ["The carnivore diet is a meat-based diet."]
        embeddings = service.encode_texts(texts)
        
        assert embeddings.shape == (1, 384)
        assert embeddings.dtype in [np.float32, np.float16]
        
        # Check L2 normalization (should be ~1.0)
        norm = np.linalg.norm(embeddings[0])
        assert 0.99 <= norm <= 1.01, f"Embedding not normalized: {norm}"
    
    def test_encode_multiple_texts(self, service):
        """Test encoding multiple texts"""
        texts = [
            "The carnivore diet involves eating only animal products.",
            "Dr. Chaffee recommends eliminating plant foods.",
            "Many people report improved energy levels."
        ]
        
        embeddings = service.encode_texts(texts)
        
        assert embeddings.shape == (3, 384)
        assert embeddings.dtype in [np.float32, np.float16]
        
        # Check all embeddings are normalized
        for i, emb in enumerate(embeddings):
            norm = np.linalg.norm(emb)
            assert 0.99 <= norm <= 1.01, f"Embedding {i} not normalized: {norm}"
    
    def test_encode_batch_behavior(self, service):
        """Test different batch sizes produce same results"""
        texts = ["Test text"] * 10
        
        emb_batch_32 = service.encode_texts(texts, batch_size=32)
        emb_batch_128 = service.encode_texts(texts, batch_size=128)
        
        # Results should be very similar (allowing for minor FP differences)
        assert emb_batch_32.shape == emb_batch_128.shape
        diff = np.abs(emb_batch_32 - emb_batch_128).max()
        assert diff < 0.01, f"Batch size affects results too much: max diff {diff}"
    
    def test_encode_large_batch(self, service):
        """Test encoding large batch doesn't crash"""
        texts = [f"Sample text number {i}" for i in range(1024)]
        
        embeddings = service.encode_texts(texts, batch_size=256)
        
        assert embeddings.shape == (1024, 384)
        assert not np.isnan(embeddings).any(), "NaN values in embeddings"
        assert not np.isinf(embeddings).any(), "Inf values in embeddings"
    
    def test_encode_similar_texts(self, service):
        """Test similar texts have high cosine similarity"""
        texts = [
            "The carnivore diet is a meat-based diet.",
            "A meat-based diet is called the carnivore diet.",
            "Python is a programming language."
        ]
        
        embeddings = service.encode_texts(texts)
        
        # Compute cosine similarities (embeddings are already normalized)
        sim_0_1 = np.dot(embeddings[0], embeddings[1])
        sim_0_2 = np.dot(embeddings[0], embeddings[2])
        
        # Similar texts should have higher similarity
        assert sim_0_1 > sim_0_2, "Similar texts don't have higher similarity"
        assert sim_0_1 > 0.7, f"Similar texts similarity too low: {sim_0_1}"


class TestReranker:
    """Tests for optional reranker"""
    
    @pytest.fixture(scope="class")
    def reranker_service(self):
        """Initialize service with reranker enabled"""
        os.environ['ENABLE_RERANKER'] = 'true'
        EmbeddingsService.shutdown()
        
        try:
            EmbeddingsService.init_from_env()
            yield EmbeddingsService
        finally:
            EmbeddingsService.shutdown()
            os.environ['ENABLE_RERANKER'] = 'false'
    
    def test_reranker_disabled(self, service):
        """Test reranking with disabled reranker returns original order"""
        if service._enable_reranker:
            pytest.skip("Reranker is enabled")
        
        query = "carnivore diet benefits"
        docs = ["doc1", "doc2", "doc3"]
        
        indices = service.rerank(query, docs, top_k=3)
        
        # Should return original order when disabled
        assert indices == [0, 1, 2]
    
    @pytest.mark.cuda
    def test_reranker_enabled(self, reranker_service):
        """Test reranking with enabled reranker"""
        if not reranker_service._enable_reranker:
            pytest.skip("Reranker not enabled")
        
        query = "What are the health benefits of eating only meat?"
        docs = [
            "Python is a programming language used for web development.",
            "The carnivore diet has many health benefits including reduced inflammation.",
            "JavaScript is commonly used for frontend development.",
            "Eating only animal products can improve metabolic health and energy levels.",
            "Machine learning models require large datasets for training."
        ]
        
        indices = reranker_service.rerank(query, docs, top_k=3)
        
        assert len(indices) == 3
        # Relevant docs (indices 1, 3) should be ranked higher
        assert 1 in indices[:3] or 3 in indices[:3], "Relevant docs not in top 3"
    
    def test_reranker_empty_docs(self, reranker_service):
        """Test reranking with empty doc list"""
        indices = reranker_service.rerank("query", [], top_k=10)
        assert indices == []
    
    def test_reranker_top_k(self, reranker_service):
        """Test reranking respects top_k parameter"""
        if not reranker_service._enable_reranker:
            pytest.skip("Reranker not enabled")
        
        query = "test query"
        docs = [f"doc {i}" for i in range(100)]
        
        indices = reranker_service.rerank(query, docs, top_k=20)
        
        assert len(indices) == 20
        assert all(0 <= idx < 100 for idx in indices)


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_encode_none_text(self, service):
        """Test encoding with None in list"""
        texts = ["valid text", None, "another valid text"]
        
        # Should handle gracefully or raise clear error
        try:
            embeddings = service.encode_texts(texts)
            # If it succeeds, check shape
            assert embeddings.shape[0] == 3
        except (TypeError, ValueError) as e:
            # Expected error for None values
            assert "None" in str(e) or "null" in str(e).lower()
    
    def test_encode_empty_string(self, service):
        """Test encoding empty strings"""
        texts = ["", "valid text", ""]
        
        embeddings = service.encode_texts(texts)
        
        # Should produce embeddings even for empty strings
        assert embeddings.shape == (3, 384)
    
    def test_multiple_initialization(self, service):
        """Test multiple init calls are safe"""
        # Should be idempotent
        service.init_from_env()
        service.init_from_env()
        service.init_from_env()
        
        assert service.is_initialized()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
