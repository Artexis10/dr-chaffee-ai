#!/usr/bin/env python3
"""
BGE-Small Embeddings Service with Optional Reranker
Replaces GTE-Qwen2-1.5B with BAAI/bge-small-en-v1.5 for 50x+ speedup
"""

import os
import logging
import numpy as np
from typing import List, Optional, Tuple
import threading

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """
    Singleton-style embeddings service with:
    - Retriever: BAAI/bge-small-en-v1.5 (384-dim, FP16 on CUDA)
    - Optional reranker: BAAI/bge-reranker-large (cross-encoder FP16)
    """
    
    # Class-level singleton state
    _lock = threading.Lock()
    _retriever_model = None
    _reranker_model = None
    _initialized = False
    _device = None
    _enable_reranker = False
    
    @staticmethod
    def init_from_env() -> None:
        """
        Initialize models from environment variables.
        Safe to call multiple times (idempotent).
        Supports profile-based configuration.
        """
        if EmbeddingsService._initialized:
            return
            
        with EmbeddingsService._lock:
            if EmbeddingsService._initialized:
                return
                
            try:
                import torch
                from sentence_transformers import SentenceTransformer, CrossEncoder
                
                # Determine device
                EmbeddingsService._device = "cuda" if torch.cuda.is_available() else "cpu"
                
                # Load profile-based configuration
                profile = os.getenv('EMBEDDING_PROFILE', 'quality').lower()
                profiles = {
                    'quality': {
                        'model': 'Alibaba-NLP/gte-Qwen2-1.5B-instruct',
                        'dimensions': 1536
                    },
                    'speed': {
                        'model': 'BAAI/bge-small-en-v1.5',
                        'dimensions': 384
                    }
                }
                profile_config = profiles.get(profile, profiles['quality'])
                
                # Load retriever model (allow env override)
                model_name = os.getenv('EMBEDDING_MODEL', profile_config['model'])
                logger.info(f"Loading retriever model: {model_name} on {EmbeddingsService._device}")
                
                EmbeddingsService._retriever_model = SentenceTransformer(
                    model_name,
                    device=EmbeddingsService._device
                )
                
                # Convert to FP16 on CUDA for speed
                if EmbeddingsService._device == "cuda":
                    EmbeddingsService._retriever_model = EmbeddingsService._retriever_model.half()
                    logger.info("✅ Retriever model converted to FP16")
                
                EmbeddingsService._retriever_model.eval()
                
                # Log CUDA memory usage
                if torch.cuda.is_available():
                    mem_allocated = torch.cuda.memory_allocated() / 1024**3
                    logger.info(f"📊 CUDA memory allocated: {mem_allocated:.2f} GB")
                
                # Load reranker if enabled
                EmbeddingsService._enable_reranker = os.getenv('ENABLE_RERANKER', 'false').lower() == 'true'
                
                if EmbeddingsService._enable_reranker:
                    reranker_name = 'BAAI/bge-reranker-large'
                    logger.info(f"Loading reranker model: {reranker_name} on {EmbeddingsService._device}")
                    
                    try:
                        EmbeddingsService._reranker_model = CrossEncoder(
                            reranker_name,
                            device=EmbeddingsService._device,
                            max_length=512
                        )
                        
                        # Test forward pass to detect OOM early
                        test_scores = EmbeddingsService._reranker_model.predict([
                            ("test query", "test document")
                        ])
                        
                        logger.info("✅ Reranker model loaded successfully")
                        
                        if torch.cuda.is_available():
                            mem_allocated = torch.cuda.memory_allocated() / 1024**3
                            logger.info(f"📊 CUDA memory after reranker: {mem_allocated:.2f} GB")
                            
                    except RuntimeError as e:
                        if 'out of memory' in str(e).lower():
                            logger.warning("⚠️  CUDA OOM loading bge-reranker-large, falling back to base")
                            
                            # Clear CUDA cache
                            if torch.cuda.is_available():
                                torch.cuda.empty_cache()
                            
                            # Fallback to base model
                            reranker_name = 'BAAI/bge-reranker-base'
                            EmbeddingsService._reranker_model = CrossEncoder(
                                reranker_name,
                                device=EmbeddingsService._device,
                                max_length=512
                            )
                            logger.info(f"✅ Fallback reranker loaded: {reranker_name}")
                        else:
                            raise
                
                EmbeddingsService._initialized = True
                logger.info("✅ EmbeddingsService initialized successfully")
                
            except ImportError as e:
                logger.error(f"Missing dependencies: {e}")
                logger.error("Install with: pip install sentence-transformers>=2.7.0 transformers>=4.41.0")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize EmbeddingsService: {e}")
                import traceback
                traceback.print_exc()
                raise
    
    @staticmethod
    def encode_texts(texts: List[str], batch_size: int = 256) -> np.ndarray:
        """
        Encode texts to 384-dim embeddings.
        
        Args:
            texts: List of text strings to encode
            batch_size: Batch size for encoding (default: 256)
            
        Returns:
            numpy array of shape (N, 384) with L2-normalized embeddings
        """
        if not texts:
            return np.array([])
        
        # Ensure initialized
        EmbeddingsService.init_from_env()
        
        try:
            import torch
            import time
            
            start_time = time.time()
            
            with EmbeddingsService._lock:
                with torch.inference_mode():
                    with torch.cuda.amp.autocast(enabled=(EmbeddingsService._device == "cuda")):
                        embeddings = EmbeddingsService._retriever_model.encode(
                            texts,
                            batch_size=batch_size,
                            device=EmbeddingsService._device,
                            convert_to_numpy=True,
                            normalize_embeddings=True,  # L2 normalize
                            show_progress_bar=len(texts) > 100
                        )
            
            elapsed = time.time() - start_time
            throughput = len(texts) / elapsed if elapsed > 0 else 0
            
            logger.info(f"Encoded {len(texts)} texts in {elapsed:.2f}s ({throughput:.1f} texts/sec)")
            
            # Clear CUDA cache to prevent memory buildup
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    @staticmethod
    def rerank(query: str, docs: List[str], top_k: int = 20) -> List[int]:
        """
        Rerank documents using cross-encoder.
        
        Args:
            query: Query string
            docs: List of document strings to rerank
            top_k: Number of top results to return (default: 20)
            
        Returns:
            List of indices in descending relevance order (length = min(top_k, len(docs)))
        """
        if not docs:
            return []
        
        if not EmbeddingsService._enable_reranker:
            logger.warning("Reranker not enabled, returning original order")
            return list(range(min(top_k, len(docs))))
        
        # Ensure initialized
        EmbeddingsService.init_from_env()
        
        try:
            import torch
            import time
            
            start_time = time.time()
            
            # Create query-doc pairs
            pairs = [(query, doc) for doc in docs]
            
            with EmbeddingsService._lock:
                with torch.inference_mode():
                    with torch.cuda.amp.autocast(enabled=(EmbeddingsService._device == "cuda")):
                        # Batch size for reranker (smaller than retriever)
                        batch_size = int(os.getenv('RERANK_BATCH_SIZE', '64'))
                        scores = EmbeddingsService._reranker_model.predict(
                            pairs,
                            batch_size=batch_size,
                            show_progress_bar=False
                        )
            
            # Get top-k indices
            ranked_indices = np.argsort(scores)[::-1][:top_k].tolist()
            
            elapsed = time.time() - start_time
            throughput = len(docs) / elapsed if elapsed > 0 else 0
            
            logger.info(f"Reranked {len(docs)} docs in {elapsed:.2f}s ({throughput:.1f} docs/sec)")
            
            # Clear CUDA cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            return ranked_indices
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to original order
            return list(range(min(top_k, len(docs))))
    
    @staticmethod
    def get_embedding_dimensions() -> int:
        """Get embedding dimensions (always 384 for bge-small)"""
        return 384
    
    @staticmethod
    def is_initialized() -> bool:
        """Check if service is initialized"""
        return EmbeddingsService._initialized
    
    @staticmethod
    def get_device() -> Optional[str]:
        """Get current device (cuda or cpu)"""
        return EmbeddingsService._device
    
    @staticmethod
    def shutdown() -> None:
        """Cleanup resources (useful for tests)"""
        with EmbeddingsService._lock:
            EmbeddingsService._retriever_model = None
            EmbeddingsService._reranker_model = None
            EmbeddingsService._initialized = False
            
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
            
            logger.info("EmbeddingsService shutdown complete")
