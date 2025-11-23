import os
from typing import List, Optional
import logging
import threading

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """
    Enhanced embedding generator supporting OpenAI and local models
    
    NOTE: This class is being deprecated in favor of EmbeddingsService.
    For new code, use:
        from services.embeddings_service import EmbeddingsService
        EmbeddingsService.init_from_env()
        embeddings = EmbeddingsService.encode_texts(texts)
    
    This class now acts as a compatibility wrapper that can delegate to
    EmbeddingsService when using BGE-Small model.
    """
    # Class-level lock for thread safety
    _lock = threading.Lock()
    # Class-level model cache (shared across all instances)
    _shared_model = None
    _shared_model_name = None
    _shared_model_device = None  # Track device to force reload if changed
    _use_new_service = None  # Cache decision to use new service
    
    def __init__(self, model_name: str = None, embedding_provider: str = None):
        # Load profile-based configuration
        profile = os.getenv('EMBEDDING_PROFILE', 'quality').lower()
        
        # Define profiles
        profiles = {
            'quality': {
                'provider': 'local',
                'model': 'Alibaba-NLP/gte-Qwen2-1.5B-instruct',
                'dimensions': 1536,
                'batch_size': 256,
                'description': 'Best quality, 20-30 texts/sec'
            },
            'speed': {
                'provider': 'local',
                'model': 'BAAI/bge-small-en-v1.5',
                'dimensions': 384,
                'batch_size': 256,
                'description': '60-80x faster, 1500-2000 texts/sec'
            }
        }
        
        # Get profile config (default to quality if invalid)
        profile_config = profiles.get(profile, profiles['quality'])
        
        # Allow environment variable overrides
        self.provider = embedding_provider or os.getenv('EMBEDDING_PROVIDER', profile_config['provider'])
        
        if self.provider == 'openai':
            self.model_name = model_name or os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-large')
            # text-embedding-3-large produces 1536 dimensions by default
            self.embedding_dimensions = int(os.getenv('EMBEDDING_DIMENSIONS', '1536'))
            self.openai_client = None
        elif self.provider == 'nomic':
            self.model_name = model_name or os.getenv('NOMIC_MODEL', 'nomic-embed-text-v1.5')
            self.embedding_dimensions = int(os.getenv('EMBEDDING_DIMENSIONS', '768'))
            self.nomic_api_key = os.getenv('NOMIC_API_KEY')
            if not self.nomic_api_key:
                raise ValueError("NOMIC_API_KEY environment variable required for nomic provider")
        elif self.provider == 'huggingface':
            self.model_name = model_name or os.getenv('HUGGINGFACE_MODEL', 'Alibaba-NLP/gte-Qwen2-1.5B-instruct')
            self.embedding_dimensions = int(os.getenv('EMBEDDING_DIMENSIONS', '1536'))
            self.hf_api_key = os.getenv('HUGGINGFACE_API_KEY')
            if not self.hf_api_key:
                raise ValueError("HUGGINGFACE_API_KEY environment variable required for huggingface provider")
        else:
            # Local sentence-transformers - use profile or env override
            self.model_name = model_name or os.getenv('EMBEDDING_MODEL', profile_config['model'])
            self.embedding_dimensions = int(os.getenv('EMBEDDING_DIMENSIONS', profile_config['dimensions']))
            self.profile_batch_size = profile_config['batch_size']
        
        # Check if we should use new EmbeddingsService (for BGE-Small)
        if EmbeddingGenerator._use_new_service is None:
            EmbeddingGenerator._use_new_service = self._should_use_new_service()
        
        logger.info(f"Embedding provider: {self.provider}, model: {self.model_name}, dimensions: {self.embedding_dimensions}")
        if EmbeddingGenerator._use_new_service:
            logger.info("Using new EmbeddingsService for BGE-Small model")
        
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
                        
                        # DIAGNOSTIC: Verify actual device placement
                        # Check first module's device (more reliable than model.device)
                        first_param = next(EmbeddingGenerator._shared_model.parameters())
                        actual_device = str(first_param.device)
                        
                        logger.info(f"✅ Local embedding model loaded successfully")
                        logger.info(f"🔍 Requested device: {embedding_device}")
                        logger.info(f"🔍 Actual device: {actual_device}")
                        
                        # CRITICAL: If model ended up on CPU despite CUDA request, force reload
                        if embedding_device == 'cuda' and 'cpu' in actual_device.lower():
                            logger.error(f"⚠️  CRITICAL: Model loaded on CPU despite CUDA request!")
                            logger.error(f"⚠️  Attempting force reload to CUDA...")
                            
                            # Force reload with explicit device placement
                            del EmbeddingGenerator._shared_model
                            if torch.cuda.is_available():
                                torch.cuda.empty_cache()
                            
                            # Reload with explicit CUDA placement
                            EmbeddingGenerator._shared_model = SentenceTransformer(self.model_name)
                            EmbeddingGenerator._shared_model = EmbeddingGenerator._shared_model.to('cuda')
                            EmbeddingGenerator._shared_model.eval()
                            
                            # Verify again
                            first_param = next(EmbeddingGenerator._shared_model.parameters())
                            actual_device = str(first_param.device)
                            logger.info(f"🔍 After force reload, device: {actual_device}")
                            
                            if 'cpu' in actual_device.lower():
                                logger.error(f"❌ FAILED to load model on CUDA - falling back to CPU")
                                logger.error(f"❌ This will cause 30-50x slower embedding generation!")
                            else:
                                logger.info(f"✅ Force reload successful - model now on CUDA")
                        elif embedding_device == 'cuda' and 'cuda' in actual_device.lower():
                            logger.info(f"🚀 GPU acceleration enabled for embeddings (30-50x faster)")
                    except ImportError:
                        raise ImportError("sentence-transformers package not available. Install with: pip install sentence-transformers")
                    except Exception as e:
                        raise ValueError(f"Failed to load local model: {e}")
        
        return EmbeddingGenerator._shared_model
    
    def _should_use_new_service(self) -> bool:
        """Check if we should use new EmbeddingsService"""
        # Use new service for BGE-Small model (384-dim)
        if self.provider == 'local' and 'bge-small' in self.model_name.lower():
            try:
                # Check if EmbeddingsService is available
                import sys
                from pathlib import Path
                backend_dir = Path(__file__).parent.parent.parent
                if str(backend_dir) not in sys.path:
                    sys.path.insert(0, str(backend_dir))
                from services.embeddings_service import EmbeddingsService
                return True
            except ImportError:
                logger.warning("EmbeddingsService not available, using legacy implementation")
                return False
        return False
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        if not texts:
            return []
        
        # Use new service if available and appropriate
        if EmbeddingGenerator._use_new_service:
            return self._generate_with_new_service(texts)
        
        if self.provider == 'openai':
            return self._generate_openai_embeddings(texts)
        elif self.provider == 'nomic':
            return self._generate_nomic_embeddings(texts)
        elif self.provider == 'huggingface':
            return self._generate_huggingface_embeddings(texts)
        else:
            return self._generate_local_embeddings(texts)
    
    def _generate_with_new_service(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using new EmbeddingsService"""
        try:
            import sys
            from pathlib import Path
            backend_dir = Path(__file__).parent.parent.parent
            if str(backend_dir) not in sys.path:
                sys.path.insert(0, str(backend_dir))
            from services.embeddings_service import EmbeddingsService
            
            # Initialize service if needed
            if not EmbeddingsService.is_initialized():
                EmbeddingsService.init_from_env()
            
            # Generate embeddings
            batch_size = int(os.getenv('EMBEDDING_BATCH_SIZE', '256'))
            embeddings = EmbeddingsService.encode_texts(texts, batch_size=batch_size)
            
            # Convert to list of lists for compatibility (NumPy-free)
            return [emb.tolist() if hasattr(emb, 'tolist') else list(emb) for emb in embeddings]
            
        except Exception as e:
            logger.error(f"Failed to use new EmbeddingsService, falling back to legacy: {e}")
            # Fallback to legacy implementation
            EmbeddingGenerator._use_new_service = False
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
    
    def _generate_nomic_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Nomic Atlas API"""
        try:
            import requests
            
            API_URL = "https://api-atlas.nomic.ai/v1/embedding/text"
            headers = {"Authorization": f"Bearer {self.nomic_api_key}"}
            
            all_embeddings = []
            batch_size = 100  # Nomic supports up to 100 texts per request
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                logger.debug(f"Generating Nomic embeddings for batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
                
                response = requests.post(
                    API_URL,
                    headers=headers,
                    json={
                        "model": self.model_name,
                        "texts": batch_texts,
                        "task_type": "search_document"  # or "search_query" for queries
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"Nomic API error: {response.status_code} - {response.text}")
                
                result = response.json()
                batch_embeddings = result.get("embeddings", [])
                
                if not batch_embeddings:
                    raise Exception(f"No embeddings in Nomic response: {result}")
                
                all_embeddings.extend(batch_embeddings)
            
            logger.info(f"Generated {len(all_embeddings)} Nomic embeddings")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Nomic embedding generation failed: {e}")
            raise
    
    def _generate_huggingface_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Hugging Face Inference API"""
        try:
            import requests
            
            API_URL = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}"
            headers = {"Authorization": f"Bearer {self.hf_api_key}"}
            
            all_embeddings = []
            batch_size = 10  # HF API limit for free tier
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                logger.debug(f"Generating HF embeddings for batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
                
                response = requests.post(
                    API_URL,
                    headers=headers,
                    json={"inputs": batch_texts, "options": {"wait_for_model": True}}
                )
                
                if response.status_code != 200:
                    raise Exception(f"HF API error: {response.status_code} - {response.text}")
                
                batch_embeddings = response.json()
                
                # Handle different response formats
                if isinstance(batch_embeddings, list):
                    all_embeddings.extend(batch_embeddings)
                else:
                    raise Exception(f"Unexpected HF API response format: {type(batch_embeddings)}")
            
            logger.info(f"Generated {len(all_embeddings)} Hugging Face embeddings")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Hugging Face embedding generation failed: {e}")
            raise
    
    def _generate_local_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local SentenceTransformer model (NumPy-free)"""
        model = self._load_local_model()
        
        try:
            # NOTE: Lock removed for single-threaded ingestion (was causing serialization)
            # If you have multiple workers calling this simultaneously, re-enable the lock
            import time
            import torch
            start_time = time.time()
            
            # Generate embeddings in batches (larger batch size for GPU efficiency)
            # Use profile-specific batch size or env override
            default_batch = getattr(self, 'profile_batch_size', 256)
            batch_size = int(os.getenv('EMBEDDING_BATCH_SIZE', str(default_batch)))
            
            # DIAGNOSTIC: Log device before encoding
            logger.debug(f"🔍 Encoding {len(texts)} texts on device: {model.device}")
            
            # CRITICAL: Force GPU usage by converting to tensors on GPU
            # Some sentence-transformers versions ignore the device parameter
            embedding_device = os.getenv('EMBEDDING_DEVICE', 'cuda')
            
            # CRITICAL: Use convert_to_tensor=True to get PyTorch tensors (NO NumPy)
            # This avoids NumPy dependency entirely in the embedding pipeline
            embeddings_tensor = model.encode(
                texts, 
                batch_size=batch_size,
                show_progress_bar=len(texts) > 10,
                convert_to_numpy=False,  # CRITICAL: Do NOT convert to NumPy
                normalize_embeddings=True,  # Normalize for better similarity search
                convert_to_tensor=True,  # CRITICAL: Return PyTorch tensors
                device=embedding_device  # Explicitly specify device
            )
            
            # Calculate performance metrics
            elapsed = time.time() - start_time
            texts_per_sec = len(texts) / elapsed if elapsed > 0 else 0
            
            # Convert PyTorch tensor to list[list[float]] (NO NumPy involved)
            # .detach() removes gradient tracking, .cpu() moves to CPU, .tolist() converts to Python list
            result = embeddings_tensor.detach().cpu().tolist()
            
            # CRITICAL: Free GPU memory immediately after embedding generation
            del embeddings_tensor
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
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                
                # Retry with much smaller batch size
                try:
                    smaller_batch_size = 16  # Very conservative
                    logger.info(f"Retrying with batch_size={smaller_batch_size}")
                    
                    # Use PyTorch tensors (NO NumPy) for retry as well
                    embeddings_tensor = model.encode(
                        texts, 
                        batch_size=smaller_batch_size,
                        show_progress_bar=False,
                        convert_to_numpy=False,  # CRITICAL: No NumPy
                        normalize_embeddings=True,
                        convert_to_tensor=True,  # CRITICAL: PyTorch tensors
                        device=embedding_device
                    )
                    
                    result = embeddings_tensor.detach().cpu().tolist()
                    
                    del embeddings_tensor
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    
                    import time
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
