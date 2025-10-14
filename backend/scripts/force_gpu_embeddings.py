#!/usr/bin/env python3
"""
Force embedding model to reload on GPU
Clears cached model and verifies GPU placement
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Force embedding model to GPU"""
    print("=" * 80)
    print("FORCE GPU EMBEDDINGS - Diagnostic & Fix Tool")
    print("=" * 80)
    
    # Check environment
    embedding_device = os.getenv('EMBEDDING_DEVICE', 'cpu')
    embedding_model = os.getenv('EMBEDDING_MODEL', 'Alibaba-NLP/gte-Qwen2-1.5B-instruct')
    
    print(f"\n📋 Configuration:")
    print(f"  EMBEDDING_DEVICE: {embedding_device}")
    print(f"  EMBEDDING_MODEL: {embedding_model}")
    
    # Check CUDA availability
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        print(f"\n🎮 CUDA Status:")
        print(f"  Available: {cuda_available}")
        if cuda_available:
            print(f"  Device: {torch.cuda.get_device_name(0)}")
            print(f"  CUDA Version: {torch.version.cuda}")
            print(f"  Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        else:
            print(f"  ❌ CUDA not available - embeddings will run on CPU!")
            print(f"  This will be 30-50x slower than GPU")
            return
    except ImportError:
        print(f"  ❌ PyTorch not installed")
        return
    
    # Clear any cached models
    print(f"\n🧹 Clearing cached models...")
    from scripts.common.embeddings import EmbeddingGenerator
    
    with EmbeddingGenerator._lock:
        if EmbeddingGenerator._shared_model is not None:
            print(f"  Found cached model, clearing...")
            del EmbeddingGenerator._shared_model
            EmbeddingGenerator._shared_model = None
            EmbeddingGenerator._shared_model_name = None
            EmbeddingGenerator._shared_model_device = None
            torch.cuda.empty_cache()
            print(f"  ✅ Cache cleared")
        else:
            print(f"  No cached model found")
    
    # Force reload on GPU
    print(f"\n🚀 Loading model on GPU...")
    try:
        generator = EmbeddingGenerator(
            model_name=embedding_model,
            embedding_provider='local'
        )
        
        # Trigger model load
        test_embeddings = generator.generate_embeddings(["test"])
        
        if test_embeddings and len(test_embeddings) > 0:
            print(f"  ✅ Model loaded successfully")
            
            # Verify device placement
            if EmbeddingGenerator._shared_model is not None:
                first_param = next(EmbeddingGenerator._shared_model.parameters())
                actual_device = str(first_param.device)
                print(f"\n📊 Device Verification:")
                print(f"  Actual device: {actual_device}")
                
                if 'cuda' in actual_device.lower():
                    print(f"  ✅ Model is on GPU - embeddings will be fast!")
                    print(f"  Expected speed: 30-50 texts/sec")
                else:
                    print(f"  ❌ Model is on CPU - embeddings will be slow!")
                    print(f"  Expected speed: 1-2 texts/sec")
                    print(f"\n🔧 Troubleshooting:")
                    print(f"  1. Check if another process is using GPU")
                    print(f"  2. Try: nvidia-smi")
                    print(f"  3. Restart Python process")
                    print(f"  4. Check CUDA drivers are up to date")
        else:
            print(f"  ❌ Model load failed")
            
    except Exception as e:
        print(f"  ❌ Error loading model: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
