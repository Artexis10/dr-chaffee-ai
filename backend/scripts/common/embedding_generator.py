"""
Compatibility shim for embedding_generator imports.
The actual implementation is in embeddings.py
"""
from scripts.common.embeddings import EmbeddingGenerator

__all__ = ['EmbeddingGenerator']
