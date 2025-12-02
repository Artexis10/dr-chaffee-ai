"""
Embedding Configuration Helper Module
======================================

ARCHITECTURE OVERVIEW (Dec 2025)
--------------------------------

This module is the single source of truth for embedding model configuration.
It drives the normalized embedding storage architecture introduced in migrations
021 (segment_embeddings) and 022 (answer_cache_embeddings).

STORAGE ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EMBEDDING STORAGE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PRIMARY (Normalized):              LEGACY (Fallback):                       │
│  ┌─────────────────────────┐       ┌─────────────────────────┐              │
│  │ segment_embeddings      │       │ segments.embedding      │              │
│  │ - segment_id (FK)       │       │ (single vector column)  │              │
│  │ - model_key             │       └─────────────────────────┘              │
│  │ - dimensions            │                                                 │
│  │ - embedding (VECTOR)    │       ┌─────────────────────────┐              │
│  │ - is_active             │       │ answer_cache.query_*    │              │
│  │ - UNIQUE(seg_id, model) │       │ (legacy dimension cols) │              │
│  └─────────────────────────┘       └─────────────────────────┘              │
│                                                                              │
│  ┌─────────────────────────┐                                                │
│  │ answer_cache_embeddings │                                                │
│  │ - answer_cache_id (FK)  │                                                │
│  │ - model_key             │                                                │
│  │ - dimensions            │                                                │
│  │ - embedding (VECTOR)    │                                                │
│  │ - is_active             │                                                │
│  └─────────────────────────┘                                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

CONFIGURATION PRIORITY (highest to lowest):
1. Environment variables (EMBEDDING_MODEL_KEY, EMBEDDING_STORAGE_STRATEGY, etc.)
2. embedding_models.json config file
3. Hardcoded defaults (bge-small-en-v1.5, 384 dims)

KEY CONFIG FLAGS:
- storage_strategy: "normalized" (use segment_embeddings) or "legacy" (use segments.embedding)
- use_dual_write: If true, write to BOTH normalized and legacy during ingestion
- use_fallback_read: If true, fall back to legacy if normalized has no results
- answer_cache_enabled: If true, enable answer cache for semantic recall (default: False)

WRITE PATH (ingestion):
1. segments_database.py::batch_insert_segments() writes to segments table
2. If use_dual_write=true, also writes to segment_embeddings via _dual_write_embeddings()

READ PATH (search):
1. If storage_strategy="normalized", query segment_embeddings first
2. If no results AND use_fallback_read=true, query segments.embedding
3. Log which source was used for debugging

MULTI-MODEL SUPPORT:
- segment_embeddings supports multiple embeddings per segment (different model_key)
- is_active flag allows switching models without deleting old embeddings
- ivfflat indexes are per-model with WHERE model_key = X AND is_active = TRUE

Provides helpers for:
- Loading embedding model configuration
- Getting active model key and dimensions
- Determining storage strategy (normalized vs legacy)
- Dual-write and fallback read settings
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from functools import lru_cache

logger = logging.getLogger(__name__)

# Cache for embedding config
_embedding_config_cache: Optional[Dict[str, Any]] = None


def _get_config_paths() -> List[str]:
    """Get list of possible config file paths"""
    return [
        os.path.join(os.path.dirname(__file__), '..', 'config', 'models', 'embedding_models.json'),
        '/app/config/models/embedding_models.json',  # Docker path
        os.path.join(os.getcwd(), 'backend', 'config', 'models', 'embedding_models.json'),
    ]


def load_embedding_config(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Load embedding configuration from embedding_models.json
    
    Returns a dict with:
    {
        "models": {...},
        "active_query_model": str,
        "active_ingestion_models": List[str],
        "storage_strategy": str,  # "normalized" or "legacy"
        "use_dual_write": bool,
        "use_fallback_read": bool,
    }
    """
    global _embedding_config_cache
    
    if _embedding_config_cache is not None and not force_refresh:
        return _embedding_config_cache.copy()
    
    config = None
    
    for config_path in _get_config_paths():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.debug(f"Loaded embedding config from {config_path}")
                break
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.debug(f"Could not load config from {config_path}: {e}")
            continue
    
    if config is None:
        # Fallback to defaults
        logger.warning("Could not load embedding_models.json, using defaults")
        config = {
            "models": {
                "bge-small-en-v1.5": {
                    "key": "bge-small-en-v1.5",
                    "provider": "sentence-transformers",
                    "model_name": "BAAI/bge-small-en-v1.5",
                    "dimensions": 384,
                }
            },
            "active_query_model": "bge-small-en-v1.5",
            "active_ingestion_models": ["bge-small-en-v1.5"],
            "storage_strategy": "normalized",
            "use_dual_write": True,
            "use_fallback_read": True,
        }
    
    # Apply environment variable overrides
    if os.getenv('EMBEDDING_MODEL_KEY'):
        config['active_query_model'] = os.getenv('EMBEDDING_MODEL_KEY')
    
    if os.getenv('EMBEDDING_STORAGE_STRATEGY'):
        config['storage_strategy'] = os.getenv('EMBEDDING_STORAGE_STRATEGY')
    
    if os.getenv('EMBEDDING_DUAL_WRITE'):
        config['use_dual_write'] = os.getenv('EMBEDDING_DUAL_WRITE', '').lower() in ('1', 'true', 'yes')
    
    if os.getenv('EMBEDDING_FALLBACK_READ'):
        config['use_fallback_read'] = os.getenv('EMBEDDING_FALLBACK_READ', '').lower() in ('1', 'true', 'yes')
    
    # Answer cache feature flag (default: disabled)
    # PRECEDENCE: ANSWER_CACHE_ENABLED env var > embedding_models.json > default (false)
    env_answer_cache = os.getenv('ANSWER_CACHE_ENABLED', '').lower()
    if env_answer_cache:
        config['answer_cache_enabled'] = env_answer_cache in ('1', 'true', 'yes')
    else:
        config['answer_cache_enabled'] = config.get('answer_cache_enabled', False)
    
    _embedding_config_cache = config
    return config.copy()


def get_active_model_key() -> str:
    """Get the active embedding model key for queries"""
    config = load_embedding_config()
    return config.get('active_query_model', 'bge-small-en-v1.5')


def get_active_ingestion_models() -> List[str]:
    """Get list of model keys to use during ingestion"""
    config = load_embedding_config()
    return config.get('active_ingestion_models', ['bge-small-en-v1.5'])


def get_model_config(model_key: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific model"""
    config = load_embedding_config()
    models = config.get('models', {})
    return models.get(model_key)


def get_model_dimensions(model_key: str) -> int:
    """Get dimensions for a specific model"""
    model_config = get_model_config(model_key)
    if model_config:
        return model_config.get('dimensions', 384)
    return 384  # Default


def get_active_model_dimensions() -> int:
    """Get dimensions for the active query model"""
    return get_model_dimensions(get_active_model_key())


def use_normalized_storage() -> bool:
    """Check if normalized storage (segment_embeddings table) should be used"""
    config = load_embedding_config()
    return config.get('storage_strategy', 'normalized') == 'normalized'


def use_dual_write() -> bool:
    """Check if dual-write is enabled (write to both normalized and legacy)"""
    config = load_embedding_config()
    return config.get('use_dual_write', True)


def use_fallback_read() -> bool:
    """Check if fallback read is enabled (fall back to legacy if normalized empty)"""
    config = load_embedding_config()
    return config.get('use_fallback_read', True)


def is_answer_cache_enabled() -> bool:
    """
    Check if answer cache feature is enabled.
    
    When disabled (default), all answer cache operations are skipped:
    - Cache lookups return None immediately
    - Cache saves are no-ops
    - No database queries to answer_cache or answer_cache_embeddings tables
    
    Precedence (highest to lowest):
    1. ANSWER_CACHE_ENABLED environment variable
    2. "answer_cache_enabled" in embedding_models.json
    3. Default: false
    """
    config = load_embedding_config()
    return config.get('answer_cache_enabled', False)


def get_all_models() -> Dict[str, Dict[str, Any]]:
    """Get all available embedding models"""
    config = load_embedding_config()
    return config.get('models', {})


def get_model_list() -> List[Dict[str, Any]]:
    """Get list of all models with their configurations"""
    models = get_all_models()
    result = []
    for key, model in models.items():
        result.append({
            'key': key,
            'provider': model.get('provider', 'unknown'),
            'model_name': model.get('model_name', key),
            'dimensions': model.get('dimensions', 384),
            'description': model.get('description', ''),
            'recommended': model.get('recommended', False),
            'production': model.get('production', False),
            'cost_per_1k': model.get('cost_per_1k', 0.0),
        })
    
    # Sort: recommended first, then by name
    result.sort(key=lambda x: (not x['recommended'], x['key']))
    return result


def validate_model_key(model_key: str) -> bool:
    """Check if a model key is valid"""
    models = get_all_models()
    return model_key in models


def model_name_to_key(model_name: str) -> str:
    """Convert a full model name to its key"""
    model_to_key = {
        'BAAI/bge-small-en-v1.5': 'bge-small-en-v1.5',
        'BAAI/bge-large-en-v1.5': 'bge-large-en',
        'Alibaba-NLP/gte-Qwen2-1.5B-instruct': 'gte-qwen2-1.5b',
        'nomic-embed-text-v1.5': 'nomic-v1.5',
        'text-embedding-3-large': 'openai-3-large',
        'text-embedding-3-small': 'openai-3-small',
    }
    return model_to_key.get(model_name, 'bge-small-en-v1.5')


def clear_config_cache():
    """Clear the configuration cache (useful for testing)"""
    global _embedding_config_cache
    _embedding_config_cache = None


# Log configuration on module load
def _log_config():
    """Log the current embedding configuration"""
    try:
        config = load_embedding_config()
        logger.info("=" * 50)
        logger.info("📋 EMBEDDING CONFIGURATION")
        logger.info("=" * 50)
        logger.info(f"   Active Query Model: {config.get('active_query_model')}")
        logger.info(f"   Active Ingestion Models: {config.get('active_ingestion_models')}")
        logger.info(f"   Storage Strategy: {config.get('storage_strategy')}")
        logger.info(f"   Dual Write: {config.get('use_dual_write')}")
        logger.info(f"   Fallback Read: {config.get('use_fallback_read')}")
        logger.info(f"   Answer Cache: {'ENABLED' if config.get('answer_cache_enabled') else 'DISABLED'}")
        logger.info("=" * 50)
    except Exception as e:
        logger.warning(f"Could not log embedding config: {e}")
