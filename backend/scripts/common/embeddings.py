"""
Embedding Generation Module
============================

ARCHITECTURE OVERVIEW (Dec 2025)
--------------------------------

This module provides the EmbeddingGenerator class which is the SINGLE source of
embedding generation for the entire application. There is NO separate "embedding
service" - all embeddings are generated IN-PROCESS.

EMBEDDING FLOW:
---------------
1. INGESTION: scripts/ingest_*.py → EmbeddingGenerator.generate_embeddings() → DB
2. SEARCH: /api/search → get_embedding_generator() → EmbeddingGenerator → query embedding
3. ANSWER: /api/answer → calls /api/search internally → same flow as above
4. /embed endpoint: Uses the same get_embedding_generator() singleton

KEY POINTS:
-----------
- EmbeddingGenerator is a SINGLETON (shared across all requests via get_embedding_generator())
- Model is loaded ONCE on first use and cached in class-level _shared_model
- No HTTP calls to external embedding services (unless using OpenAI/Nomic API providers)
- For sentence-transformers provider: model runs locally on CPU/GPU
- Configuration comes from resolve_embedding_config() which reads env vars

PROVIDERS:
----------
- 'sentence-transformers' (default): Local model, e.g., BAAI/bge-small-en-v1.5
- 'openai': OpenAI API (text-embedding-3-large)
- 'nomic': Nomic Atlas API
- 'huggingface': HuggingFace Inference API

DEVICE SELECTION:
-----------------
- FORCE_CPU_ONLY=1: Always use CPU (for CPU-only PyTorch builds)
- EMBEDDING_DEVICE=cuda: Use GPU if available
- EMBEDDING_DEVICE=cpu: Force CPU
- Auto-detect: Check torch.cuda.is_available()
"""

import os
from typing import List, Optional, Dict, Any
import logging
import threading

logger = logging.getLogger(__name__)

# =============================================================================
# FORCE_CPU_ONLY PATCH - MUST RUN BEFORE ANY TORCH IMPORTS
# =============================================================================
# This MUST be at the very top of the module, before any code that might
# import torch or sentence_transformers. On CPU-only PyTorch builds (Hetzner),
# even calling torch.cuda.is_available() can trigger CUDA initialization errors.

_force_cpu_applied = False

def _apply_force_cpu_mode() -> None:
    """
    If FORCE_CPU_ONLY=1, monkey-patch torch.cuda to prevent ANY CUDA access.
    This prevents CUDA initialization errors on CPU-only PyTorch builds (e.g., Hetzner).
    
    MUST be called before any torch imports in other modules.
    
    Patches:
    - torch.cuda.is_available() -> always returns False
    - torch.cuda.device_count() -> always returns 0
    - torch.cuda.current_device() -> raises RuntimeError
    - torch.cuda.get_device_name() -> raises RuntimeError
    - torch.cuda.empty_cache() -> no-op
    - torch.cuda.synchronize() -> no-op
    """
    global _force_cpu_applied
    if _force_cpu_applied:
        return
    
    force_cpu = os.getenv('FORCE_CPU_ONLY', '').lower() in ('1', 'true', 'yes')
    if not force_cpu:
        _force_cpu_applied = True
        return
    
    try:
        import torch
        
        # Monkey-patch all CUDA availability functions
        torch.cuda.is_available = lambda: False
        torch.cuda.device_count = lambda: 0
        
        def _raise_no_cuda(*args, **kwargs):
            raise RuntimeError("CUDA is disabled (FORCE_CPU_ONLY=1)")
        
        # Patch functions that would fail on CPU-only builds
        torch.cuda.current_device = _raise_no_cuda
        torch.cuda.get_device_name = _raise_no_cuda
        torch.cuda.get_device_properties = _raise_no_cuda
        torch.cuda.empty_cache = lambda: None  # No-op instead of error
        torch.cuda.synchronize = lambda device=None: None  # No-op
        
        logger.info("🔒 FORCE_CPU_ONLY=1: torch.cuda fully patched (is_available=False, device_count=0)")
        _force_cpu_applied = True
        
    except ImportError:
        logger.warning("torch not installed, FORCE_CPU_ONLY has no effect")
        _force_cpu_applied = True


# CRITICAL: Apply the patch IMMEDIATELY at module import time
# This ensures the patch is in place before any other code imports torch
_apply_force_cpu_mode()


# =============================================================================
# EMBEDDING CONFIGURATION - SINGLE SOURCE OF TRUTH
# =============================================================================

_resolved_config_cache: Optional[Dict[str, Any]] = None


def resolve_embedding_config(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Single source of truth for embedding configuration.
    
    Returns a dict with:
    {
        "provider": str,        # 'sentence-transformers', 'openai', 'nomic', etc.
        "model": str,           # Full model name (e.g., 'BAAI/bge-small-en-v1.5')
        "dimensions": int,      # 384, 768, 1536, etc.
        "device": str           # 'cpu' or 'cuda'
    }
    
    Priority:
    1. FORCE_CPU_ONLY=1 → always CPU
    2. EMBEDDINGS_DEVICE env var (primary)
    3. EMBEDDING_DEVICE env var (fallback)
    4. Auto-detect CUDA availability
    
    Dimension priority:
    1. EMBEDDINGS_DIM env var (primary)
    2. EMBEDDINGS_DIMENSIONS env var (fallback)
    3. EMBEDDING_DIMENSIONS env var (legacy fallback)
    4. Profile default
    """
    global _resolved_config_cache
    
    # Apply FORCE_CPU_ONLY monkey-patch if needed
    _apply_force_cpu_mode()
    
    if _resolved_config_cache is not None and not force_refresh:
        return _resolved_config_cache.copy()
    
    # Profile-based defaults
    profile = os.getenv('EMBEDDING_PROFILE', 'speed').lower()  # Default to speed (BGE-small)
    
    profiles = {
        'quality': {
            'provider': 'sentence-transformers',
            'model': 'Alibaba-NLP/gte-Qwen2-1.5B-instruct',
            'dimensions': 1536,
        },
        'speed': {
            'provider': 'sentence-transformers',
            'model': 'BAAI/bge-small-en-v1.5',
            'dimensions': 384,
        }
    }
    
    profile_config = profiles.get(profile, profiles['speed'])
    
    # Resolve provider
    provider = (
        os.getenv('EMBEDDINGS_PROVIDER') or
        os.getenv('EMBEDDING_PROVIDER') or
        profile_config['provider']
    )
    
    # Resolve model
    model = (
        os.getenv('EMBEDDINGS_MODEL') or
        os.getenv('EMBEDDING_MODEL') or
        profile_config['model']
    )
    
    # Resolve dimensions (multiple fallbacks for compatibility)
    # CRITICAL: Model dimensions are fixed - env vars should match or be unset
    dim_str = (
        os.getenv('EMBEDDINGS_DIM') or
        os.getenv('EMBEDDINGS_DIMENSIONS') or
        os.getenv('EMBEDDING_DIMENSIONS') or
        ''
    )
    
    # Model-to-dimension mapping (fixed, cannot be overridden)
    model_dimensions = {
        'BAAI/bge-small-en-v1.5': 384,
        'BAAI/bge-large-en-v1.5': 1024,
        'Alibaba-NLP/gte-Qwen2-1.5B-instruct': 1536,
        'nomic-embed-text-v1.5': 768,
        'text-embedding-3-large': 3072,  # OpenAI default
        'text-embedding-3-small': 1536,  # OpenAI default
    }
    
    # Get correct dimensions for the model
    correct_dimensions = model_dimensions.get(model, profile_config['dimensions'])
    
    if dim_str:
        try:
            env_dimensions = int(dim_str)
            if env_dimensions != correct_dimensions:
                logger.warning(
                    f"⚠️  EMBEDDING_DIMENSIONS={env_dimensions} does not match model {model} "
                    f"(requires {correct_dimensions}). Using correct value: {correct_dimensions}"
                )
            dimensions = correct_dimensions  # Always use model's correct dimensions
        except ValueError:
            logger.warning(f"Invalid dimensions '{dim_str}', using model default {correct_dimensions}")
            dimensions = correct_dimensions
    else:
        dimensions = correct_dimensions
    
    logger.info(f"📐 Embedding dimensions: {dimensions} (model: {model})")
    
    # Resolve device with FORCE_CPU_ONLY override
    force_cpu = os.getenv('FORCE_CPU_ONLY', '').lower() in ('1', 'true', 'yes')
    
    if force_cpu:
        device = 'cpu'
        logger.info("🔒 FORCE_CPU_ONLY=1: Device forced to CPU")
    else:
        # Check env vars
        device_env = (
            os.getenv('EMBEDDINGS_DEVICE') or
            os.getenv('EMBEDDING_DEVICE') or
            ''
        ).lower()
        
        if device_env == 'cpu':
            device = 'cpu'
            logger.info("📍 Device set to CPU via environment variable")
        elif device_env == 'cuda':
            # Verify CUDA is actually available
            try:
                import torch
                if torch.cuda.is_available():
                    device = 'cuda'
                    logger.info(f"🚀 CUDA available: {torch.cuda.get_device_name(0)}")
                else:
                    device = 'cpu'
                    logger.warning("⚠️  CUDA requested but not available, falling back to CPU")
            except ImportError:
                device = 'cpu'
                logger.warning("⚠️  torch not installed, using CPU")
        else:
            # Auto-detect
            try:
                import torch
                if torch.cuda.is_available():
                    device = 'cuda'
                    logger.info(f"🚀 Auto-detected CUDA: {torch.cuda.get_device_name(0)}")
                else:
                    device = 'cpu'
                    logger.info("📍 Auto-detected: No CUDA, using CPU")
            except ImportError:
                device = 'cpu'
                logger.info("📍 torch not installed, using CPU")
    
    config = {
        'provider': provider,
        'model': model,
        'dimensions': dimensions,
        'device': device,
    }
    
    _resolved_config_cache = config
    
    # Log the final resolved configuration
    force_cpu_env = os.getenv('FORCE_CPU_ONLY', 'not set')
    logger.info("=" * 60)
    logger.info("📋 EMBEDDING CONFIGURATION")
    logger.info("=" * 60)
    logger.info(f"   Provider: {provider}")
    logger.info(f"   Model: {model}")
    logger.info(f"   Dimensions: {dimensions}")
    logger.info(f"   Device: {device}")
    logger.info(f"   FORCE_CPU_ONLY: {force_cpu_env}")
    logger.info("=" * 60)
    logger.info(f"Embedding provider: {provider}, model: {model}, dimensions: {dimensions}")
    
    return config.copy()


def get_embedding_dimensions() -> int:
    """Convenience function to get just the dimensions."""
    return resolve_embedding_config()['dimensions']


def get_embedding_device() -> str:
    """Convenience function to get just the device."""
    return resolve_embedding_config()['device']

class EmbeddingGenerator:
    """
    Enhanced embedding generator supporting OpenAI and local models.
    
    Uses resolve_embedding_config() as single source of truth for configuration.
    Supports FORCE_CPU_ONLY mode for CPU-only deployments.
    """
    # Class-level lock for thread safety
    _lock = threading.Lock()
    # Class-level model cache (shared across all instances)
    _shared_model = None
    _shared_model_name = None
    _shared_model_device = None  # Track device to force reload if changed
    _use_new_service = None  # Cache decision to use new service
    
    def __init__(self, model_name: str = None, embedding_provider: str = None):
        # Get resolved config (single source of truth)
        config = resolve_embedding_config()
        
        # Allow explicit overrides, but default to resolved config
        self.provider = embedding_provider or config['provider']
        self._resolved_device = config['device']  # Store resolved device
        
        if self.provider == 'openai':
            self.model_name = model_name or os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-large')
            # OpenAI dimensions: use config if provider matches, otherwise use model-specific default
            # text-embedding-3-large supports 256-3072 dims, default 3072
            # text-embedding-3-small supports 256-1536 dims, default 1536
            self.embedding_dimensions = config['dimensions'] if config['provider'] == 'openai' else 3072
            self.openai_client = None
        elif self.provider == 'nomic':
            self.model_name = model_name or os.getenv('NOMIC_MODEL', 'nomic-embed-text-v1.5')
            self.embedding_dimensions = 768  # Nomic is always 768
            self.nomic_api_key = os.getenv('NOMIC_API_KEY')
            if not self.nomic_api_key:
                raise ValueError("NOMIC_API_KEY environment variable required for nomic provider")
        elif self.provider == 'huggingface':
            self.model_name = model_name or os.getenv('HUGGINGFACE_MODEL', 'Alibaba-NLP/gte-Qwen2-1.5B-instruct')
            # HuggingFace models have fixed dimensions based on model
            # GTE-Qwen2-1.5B = 1536, but use config if available
            self.embedding_dimensions = config['dimensions'] if config['provider'] == 'huggingface' else 1536
            self.hf_api_key = os.getenv('HUGGINGFACE_API_KEY')
            if not self.hf_api_key:
                raise ValueError("HUGGINGFACE_API_KEY environment variable required for huggingface provider")
        else:
            # Local sentence-transformers - use resolved config (single source of truth)
            # This includes 'sentence-transformers' and 'local' providers
            self.model_name = model_name or config['model']
            self.embedding_dimensions = config['dimensions']
            self.profile_batch_size = 256  # Default batch size
        
        # Check if we should use new EmbeddingsService (for BGE-Small)
        if EmbeddingGenerator._use_new_service is None:
            EmbeddingGenerator._use_new_service = self._should_use_new_service()
        
        # Log configuration
        logger.info(f"📋 EmbeddingGenerator initialized:")
        logger.info(f"   Provider: {self.provider}")
        logger.info(f"   Model: {self.model_name}")
        logger.info(f"   Dimensions: {self.embedding_dimensions}")
        logger.info(f"   Device: {self._resolved_device}")
        
        if EmbeddingGenerator._use_new_service:
            logger.info("   Using EmbeddingsService for BGE-Small model")
        
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
        # Use resolved device from config (respects FORCE_CPU_ONLY)
        embedding_device = self._resolved_device
        
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
                        
                        # FORCE_CPU_ONLY is already handled by resolve_embedding_config()
                        # and torch.cuda.is_available() is monkey-patched if needed
                        
                        logger.info(f"Loading local embedding model: {self.model_name} on {embedding_device}")
                        
                        # Load model on specified device
                        EmbeddingGenerator._shared_model = SentenceTransformer(
                            self.model_name, 
                            device=embedding_device
                        )
                        
                        # For CPU mode, ensure model is on CPU
                        if embedding_device == 'cpu':
                            EmbeddingGenerator._shared_model = EmbeddingGenerator._shared_model.to('cpu')
                        elif embedding_device == 'cuda' and torch.cuda.is_available():
                            EmbeddingGenerator._shared_model = EmbeddingGenerator._shared_model.to('cuda')
                        
                        EmbeddingGenerator._shared_model.eval()
                        EmbeddingGenerator._shared_model_name = self.model_name
                        EmbeddingGenerator._shared_model_device = embedding_device
                        
                        # Verify actual device placement
                        first_param = next(EmbeddingGenerator._shared_model.parameters())
                        actual_device = str(first_param.device)
                        
                        logger.info(f"✅ Local embedding model loaded successfully")
                        logger.info(f"   Requested device: {embedding_device}")
                        logger.info(f"   Actual device: {actual_device}")
                        
                        if embedding_device == 'cpu' and 'cpu' in actual_device.lower():
                            logger.info(f"✅ CPU mode confirmed")
                        elif embedding_device == 'cuda' and 'cuda' in actual_device.lower():
                            logger.info(f"🚀 GPU acceleration enabled")
                        elif embedding_device == 'cuda' and 'cpu' in actual_device.lower():
                            logger.warning(f"⚠️  Requested CUDA but model is on CPU")
                            # Update tracked device to actual
                            EmbeddingGenerator._shared_model_device = 'cpu'
                            
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
            import time
            import torch
            start_time = time.time()
            
            # Use resolved device (respects FORCE_CPU_ONLY)
            embedding_device = self._resolved_device
            
            # Generate embeddings in batches
            default_batch = getattr(self, 'profile_batch_size', 256)
            batch_size = int(os.getenv('EMBEDDING_BATCH_SIZE', str(default_batch)))
            
            logger.debug(f"🔍 Encoding {len(texts)} texts on device: {embedding_device}")
            
            # CRITICAL: Use convert_to_tensor=True to get PyTorch tensors (NO NumPy)
            # Always use the resolved device - never hardcode 'cuda'
            embeddings_tensor = model.encode(
                texts, 
                batch_size=batch_size,
                show_progress_bar=len(texts) > 10,
                convert_to_numpy=False,  # CRITICAL: Do NOT convert to NumPy
                normalize_embeddings=True,  # Normalize for better similarity search
                convert_to_tensor=True,  # CRITICAL: Return PyTorch tensors
                device=embedding_device  # Use resolved device (cpu or cuda)
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
                    # Use CPU for OOM recovery to be safe
                    embeddings_tensor = model.encode(
                        texts, 
                        batch_size=smaller_batch_size,
                        show_progress_bar=False,
                        convert_to_numpy=False,  # CRITICAL: No NumPy
                        normalize_embeddings=True,
                        convert_to_tensor=True,  # CRITICAL: PyTorch tensors
                        device='cpu'  # Force CPU for OOM recovery
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
