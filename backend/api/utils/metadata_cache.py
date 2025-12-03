"""
Metadata Cache - Centralized caching for expensive metadata lookups

Caches:
- Embedding model stats (from database)
- Search configuration (from database)
- Model catalogs (RAG and embedding)

All caches have TTL-based expiration and support manual refresh.
This module is the single source of truth for cached metadata access
in both the main RAG pipeline and tuning endpoints.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from .cache import TTLCache

logger = logging.getLogger(__name__)

# =============================================================================
# Cache Configuration
# =============================================================================

# TTL for metadata caches (seconds)
# - Embedding stats: 60s (DB query, changes rarely)
# - Search config: 60s (DB query, changes via tuning dashboard)
# - Model catalogs: 300s (file-based, changes on deploy)
EMBEDDING_STATS_TTL = 60.0
SEARCH_CONFIG_TTL = 60.0
MODEL_CATALOG_TTL = 300.0

# Shared caches
_embedding_stats_cache = TTLCache(ttl_seconds=EMBEDDING_STATS_TTL)
_search_config_cache = TTLCache(ttl_seconds=SEARCH_CONFIG_TTL)
_model_catalog_cache = TTLCache(ttl_seconds=MODEL_CATALOG_TTL)


# =============================================================================
# Embedding Stats Cache
# =============================================================================

def get_cached_embedding_stats(refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Get embedding model stats from database with caching.
    
    Returns list of dicts with:
    - model_key: str
    - dimensions: int
    - count: int
    - storage: str (table name)
    
    Args:
        refresh: If True, bypass cache and fetch fresh data
        
    Returns:
        List of embedding model stats, or empty list on error
    """
    cache_key = "embedding_stats"
    
    if refresh:
        _embedding_stats_cache.invalidate(cache_key)
        logger.debug("Embedding stats cache invalidated")
    
    def fetch_stats():
        # Import here to avoid circular imports
        from ..main import get_available_embedding_models
        stats = get_available_embedding_models()
        logger.info(f"Cached embedding stats: {len(stats)} models")
        return stats
    
    return _embedding_stats_cache.get_or_compute(cache_key, fetch_stats)


def invalidate_embedding_stats():
    """Invalidate embedding stats cache (call after ingestion)."""
    _embedding_stats_cache.invalidate("embedding_stats")
    logger.debug("Embedding stats cache invalidated")


# =============================================================================
# Search Config Cache
# =============================================================================

def get_cached_search_config(refresh: bool = False):
    """
    Get search configuration from database with caching.
    
    Returns SearchConfigDB object with:
    - top_k: int
    - min_similarity: float
    - enable_reranker: bool
    - rerank_top_k: int
    - return_top_k: int
    
    Args:
        refresh: If True, bypass cache and fetch fresh data
        
    Returns:
        SearchConfigDB object (defaults if table missing)
    """
    cache_key = "search_config"
    
    if refresh:
        _search_config_cache.invalidate(cache_key)
        logger.debug("Search config cache invalidated")
    
    def fetch_config():
        # Import here to avoid circular imports
        from ..tuning import get_search_config_from_db
        config = get_search_config_from_db()
        logger.debug(f"Cached search config: top_k={config.top_k}, min_sim={config.min_similarity}")
        return config
    
    return _search_config_cache.get_or_compute(cache_key, fetch_config)


def invalidate_search_config():
    """
    Invalidate search config cache.
    
    Call this after updating search config via tuning dashboard
    to ensure the next request gets fresh values.
    """
    _search_config_cache.invalidate("search_config")
    logger.info("Search config cache invalidated")


# =============================================================================
# Model Catalog Cache (extends existing module-level cache with TTL)
# =============================================================================

def get_cached_rag_catalog(refresh: bool = False) -> Dict[str, Any]:
    """
    Get RAG model catalog with TTL caching.
    
    Args:
        refresh: If True, bypass cache and fetch fresh data
        
    Returns:
        RAG catalog dict with 'models', 'default_model', etc.
    """
    cache_key = "rag_catalog"
    
    if refresh:
        _model_catalog_cache.invalidate(cache_key)
    
    def fetch_catalog():
        from ..model_catalog import get_rag_model_catalog
        catalog = get_rag_model_catalog(force_refresh=refresh)
        return catalog
    
    return _model_catalog_cache.get_or_compute(cache_key, fetch_catalog)


def get_cached_embedding_catalog(refresh: bool = False) -> Dict[str, Any]:
    """
    Get embedding model catalog with TTL caching.
    
    Args:
        refresh: If True, bypass cache and fetch fresh data
        
    Returns:
        Embedding catalog dict with 'models', 'active_query_model', etc.
    """
    cache_key = "embedding_catalog"
    
    if refresh:
        _model_catalog_cache.invalidate(cache_key)
    
    def fetch_catalog():
        from ..model_catalog import get_embedding_model_catalog
        catalog = get_embedding_model_catalog(force_refresh=refresh)
        return catalog
    
    return _model_catalog_cache.get_or_compute(cache_key, fetch_catalog)


def invalidate_model_catalogs():
    """Invalidate both model catalogs (call after config changes)."""
    _model_catalog_cache.invalidate("rag_catalog")
    _model_catalog_cache.invalidate("embedding_catalog")
    logger.info("Model catalogs cache invalidated")


# =============================================================================
# Cache Status (for debugging/monitoring)
# =============================================================================

def get_cache_status() -> Dict[str, Any]:
    """
    Get status of all metadata caches for debugging.
    
    Returns dict with cache names and their current state.
    """
    return {
        "embedding_stats": {
            "ttl_seconds": EMBEDDING_STATS_TTL,
            "has_value": _embedding_stats_cache.get("embedding_stats") is not None
        },
        "search_config": {
            "ttl_seconds": SEARCH_CONFIG_TTL,
            "has_value": _search_config_cache.get("search_config") is not None
        },
        "model_catalogs": {
            "ttl_seconds": MODEL_CATALOG_TTL,
            "rag_cached": _model_catalog_cache.get("rag_catalog") is not None,
            "embedding_cached": _model_catalog_cache.get("embedding_catalog") is not None
        }
    }
