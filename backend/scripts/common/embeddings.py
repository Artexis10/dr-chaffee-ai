import os
from typing import List, Optional
import logging
import threading

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """Enhanced embedding generator supporting OpenAI and local models"""
    # Class-level lock for thread safety
    _lock = threading.Lock()
    # Class-level model cache (shared across all instances)
    _shared_model = None
    _shared_model_name = None
    _shared_model_device = None  # Track device to force reload if changed
    
    def __init__(self, model_name: str = None, embedding_provider: str = None):
        # Determine embedding provider (openai or local)
        self.provider = embedding_provider or os.getenv('EMBEDDING_PROVIDER', 'openai')
        
        if self.provider == 'openai':
            self.model_name = model_name or os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-large')
            self.embedding_dimensions = int(os.getenv('EMBEDDING_DIMENSIONS', '384'))  # Reduced for pgvector compatibility
            self.openai_client = None
        else:
            # Local sentence-transformers - read dimensions from environment
            self.model_name = model_name or os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
            self.embedding_dimensions = int(os.getenv('EMBEDDING_DIMENSIONS', '384'))  # Read from .env
        
        logger.info(f"Embedding provider: {self.provider}, model: {self.model_name}, dimensions: {self.embedding_dimensions}")
        
    def _load_openai_client(self):
        """Load OpenAI client for embeddings"""
        if self.openai_client is None:
            with EmbeddingGenerator._lock:
                if self.openai_client is None:
                    try:
                        import openai
                        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                        logger.info("OpenAI client loaded successfully")
                    except ImportError:
                        raise ImportError("OpenAI package not available. Install with: pip install openai")
                    except Exception as e:
                        raise ValueError(f"Failed to initialize OpenAI client: {e}")
        
        return self.openai_client
    
    def _load_local_model(self):
        """Load local SentenceTransformer model (shared across all instances)"""
        # Read device from environment
        embedding_device = os.getenv('EMBEDDING_DEVICE', 'cpu')
        
        # Check if we need to load or reload the model (model name OR device changed)
        needs_reload = (
            EmbeddingGenerator._shared_model is None or 
            EmbeddingGenerator._shared_model_name != self.model_name or
            EmbeddingGenerator._shared_model_device != embedding_device
        )
        
        if needs_reload:
            with EmbeddingGenerator._lock:
                # Double-check after acquiring lock
                needs_reload = (
                    EmbeddingGenerator._shared_model is None or 
                    EmbeddingGenerator._shared_model_name != self.model_name or
                    EmbeddingGenerator._shared_model_device != embedding_device
                )
                
                if needs_reload:
                    try:
                        from sentence_transformers import SentenceTransformer
                        import torch
                        
                        # Verify CUDA availability if GPU requested
                        if embedding_device == 'cuda':
                            if not torch.cuda.is_available():
                                logger.error("❌ CUDA requested but not available! Falling back to CPU")
                                embedding_device = 'cpu'
                            else:
                                logger.info(f"✅ CUDA available: {torch.cuda.get_device_name(0)}")
                        
                        logger.info(f"Loading local embedding model: {self.model_name} on {embedding_device}")
                        EmbeddingGenerator._shared_model = SentenceTransformer(self.model_name, device=embedding_device)
                        
                        # CRITICAL: Explicitly move model to device (SentenceTransformer sometimes ignores device param)
                        if embedding_device == 'cuda':
                            EmbeddingGenerator._shared_model = EmbeddingGenerator._shared_model.to('cuda')
                        
                        EmbeddingGenerator._shared_model.eval()
                        EmbeddingGenerator._shared_model_name = self.model_name
                        EmbeddingGenerator._shared_model_device = embedding_device  # Track device
                        
                        # DIAGNOSTIC: Verify actual device
                        actual_device = str(EmbeddingGenerator._shared_model.device)
                        logger.info(f"✅ Local embedding model loaded successfully")
                        logger.info(f"🔍 Requested device: {embedding_device}")
                        logger.info(f"🔍 Actual device: {actual_device}")
                        
                        if embedding_device == 'cuda' and 'cpu' in actual_device.lower():
                            logger.error(f"⚠️  WARNING: Requested CUDA but model is on CPU!")
                            logger.error(f"⚠️  This will cause 5-10x slower embedding generation!")
                        elif embedding_device == 'cuda' and 'cuda' in actual_device.lower():
                            logger.info(f"🚀 GPU acceleration enabled for embeddings (5-10x faster)")
                    except ImportError:
                        raise ImportError("sentence-transformers package not available. Install with: pip install sentence-transformers")
                    except Exception as e:
                        raise ValueError(f"Failed to load local model: {e}")
        
        return EmbeddingGenerator._shared_model
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        if not texts:
            return []
        
        if self.provider == 'openai':
            return self._generate_openai_embeddings(texts)
        else:
            return self._generate_local_embeddings(texts)
    
    def _generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API"""
        client = self._load_openai_client()
        
        try:
            # Process in batches to handle API limits
            batch_size = 100  # OpenAI limit
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                logger.debug(f"Generating OpenAI embeddings for batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
                
                response = client.embeddings.create(
                    model=self.model_name,
                    input=batch_texts,
                    dimensions=self.embedding_dimensions  # Reduce dimensions to match pgvector schema
                )
                
                batch_embeddings = [embedding.embedding for embedding in response.data]
                all_embeddings.extend(batch_embeddings)
            
            logger.info(f"Generated {len(all_embeddings)} OpenAI embeddings")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            # Fallback to local model
            logger.warning("Falling back to local embedding model")
            return self._generate_local_embeddings(texts)
    
    def _generate_local_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local SentenceTransformer model"""
        model = self._load_local_model()
        
        try:
            # CRITICAL: Lock during embedding generation to prevent GPU contention
            # Multiple threads calling model.encode() simultaneously causes massive slowdown
            import time
            start_time = time.time()
            
            with EmbeddingGenerator._lock:
                # Generate embeddings in batches (larger batch size for GPU efficiency)
                # Read batch size from environment, default to 64 to prevent OOM (was 256)
                # Reduced from 256 to 64 to prevent CUDA OOM on large models
                batch_size = int(os.getenv('EMBEDDING_BATCH_SIZE', '64'))
                
                # DIAGNOSTIC: Log device before encoding
                logger.debug(f"🔍 Encoding {len(texts)} texts on device: {model.device}")
                
                # CRITICAL: Force GPU usage by converting to tensors on GPU
                # Some sentence-transformers versions ignore the device parameter
                import torch
                embedding_device = os.getenv('EMBEDDING_DEVICE', 'cpu')
                
                # Use convert_to_tensor=True to keep tensors on GPU during encoding
                embeddings = model.encode(
                    texts, 
                    batch_size=batch_size,
                    show_progress_bar=len(texts) > 10,
                    convert_to_numpy=True,
                    normalize_embeddings=True,  # Normalize for better similarity search
                    convert_to_tensor=False,  # We want numpy output, but process on GPU
                    device=embedding_device  # Explicitly specify device
                )
            
            # Calculate performance metrics
            elapsed = time.time() - start_time
            texts_per_sec = len(texts) / elapsed if elapsed > 0 else 0
            
            # Convert to list of lists for JSON serialization
            result = [embedding.tolist() if hasattr(embedding, 'tolist') else embedding for embedding in embeddings]
            
            # CRITICAL: Free GPU memory immediately after embedding generation
            del embeddings
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # DIAGNOSTIC: Log performance
            logger.info(f"Generated {len(result)} local embeddings in {elapsed:.2f}s ({texts_per_sec:.1f} texts/sec)")
            
            # Performance expectations vary by model size:
            # - Small models (MiniLM, 22M params): 300+ texts/sec on GPU
            # - Large models (GTE-Qwen2-1.5B, 1.5B params): 30-50 texts/sec on GPU
            # - CPU performance: 5-10x slower than GPU
            
            # Check if model name suggests large model
            is_large_model = 'qwen' in self.model_name.lower() or '1.5b' in self.model_name.lower() or 'large' in self.model_name.lower()
            expected_gpu_speed = 30 if is_large_model else 200
            
            if texts_per_sec < (expected_gpu_speed * 0.3) and len(texts) > 10:
                logger.warning(f"⚠️  Slow embedding generation ({texts_per_sec:.1f} texts/sec) - likely running on CPU!")
                logger.warning(f"⚠️  Expected GPU speed for {self.model_name}: ~{expected_gpu_speed} texts/sec")
            elif texts_per_sec >= expected_gpu_speed:
                logger.info(f"🚀 GPU acceleration active ({texts_per_sec:.1f} texts/sec - good for large model)")
            
            return result
            
        except RuntimeError as e:
            if 'out of memory' in str(e).lower():
                logger.error(f"CUDA OOM during embedding generation: {e}")
                logger.info("Attempting GPU recovery and retry with smaller batch...")
                
                # Emergency GPU cleanup
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                
                # Retry with much smaller batch size
                try:
                    smaller_batch_size = 16  # Very conservative
                    logger.info(f"Retrying with batch_size={smaller_batch_size}")
                    
                    embeddings = model.encode(
                        texts, 
                        batch_size=smaller_batch_size,
                        show_progress_bar=False,
                        convert_to_numpy=True,
                        normalize_embeddings=True,
                        convert_to_tensor=False,
                        device=embedding_device
                    )
                    
                    result = [embedding.tolist() if hasattr(embedding, 'tolist') else embedding for embedding in embeddings]
                    
                    del embeddings
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    
                    elapsed = time.time() - start_time
                    logger.info(f"✅ Recovery successful: {len(result)} embeddings in {elapsed:.2f}s")
                    return result
                    
                except Exception as retry_error:
                    logger.error(f"Recovery failed: {retry_error}")
                    return []
            else:
                logger.error(f"Local embedding generation failed: {e}")
                import traceback
                traceback.print_exc()
                return []
                
        except Exception as e:
            logger.error(f"Local embedding generation failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def generate_single_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text"""
        if not text or not text.strip():
            return None
            
        embeddings = self.generate_embeddings([text])
        return embeddings[0] if embeddings else None
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this generator"""
        return self.embedding_dimensions
