"""
Model Catalog - Unified model configuration loader

Loads RAG and embedding model configs from backend/config/models/*.json
with caching and fallback defaults.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# =============================================================================
# Config paths
# =============================================================================

CONFIG_DIR = Path(__file__).parent.parent / "config" / "models"
RAG_MODELS_PATH = CONFIG_DIR / "rag_models.json"
EMBEDDING_MODELS_PATH = CONFIG_DIR / "embedding_models.json"

# =============================================================================
# Module-level cache (loaded once, reused)
# =============================================================================

_rag_catalog_cache: Optional[Dict[str, Any]] = None
_embedding_catalog_cache: Optional[Dict[str, Any]] = None

# =============================================================================
# Fallback defaults (used if JSON files are missing/invalid)
# =============================================================================

DEFAULT_RAG_CATALOG = {
    "models": {
        "gpt-4.1": {
            "label": "GPT-4.1 (Best quality)",
            "max_tokens": 128000,
            "supports_json_mode": True,
            "supports_128k_context": True,
            "recommended": True
        },
        "gpt-4o-mini": {
            "label": "GPT-4o Mini (Cheapest)",
            "max_tokens": 128000,
            "supports_json_mode": True,
            "supports_128k_context": True,
            "recommended": True
        }
    },
    "default_model": "gpt-4.1"
}

DEFAULT_EMBEDDING_CATALOG = {
    "models": {
        "bge-small-en-v1.5": {
            "key": "bge-small-en-v1.5",
            "provider": "sentence-transformers",
            "model_name": "BAAI/bge-small-en-v1.5",
            "dimensions": 384,
            "cost_per_1k": 0.0,
            "description": "BGE-small model - lightweight, 384 dims, fast inference",
            "recommended": True,
            "production": True
        }
    },
    "active_query_model": "bge-small-en-v1.5",
    "active_ingestion_models": ["bge-small-en-v1.5"],
    "recommended_model": "bge-small-en-v1.5",
    "storage_strategy": "legacy"
}


# =============================================================================
# RAG Model Catalog
# =============================================================================

def get_rag_model_catalog(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Load RAG model catalog from JSON file.
    
    Returns the full catalog dict with 'models', 'default_model', etc.
    Caches result in module-level variable.
    Falls back to DEFAULT_RAG_CATALOG if file missing/invalid.
    """
    global _rag_catalog_cache
    
    if _rag_catalog_cache is not None and not force_refresh:
        return _rag_catalog_cache.copy()
    
    try:
        if RAG_MODELS_PATH.exists():
            with open(RAG_MODELS_PATH, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
            
            # Validate structure
            if 'models' not in catalog or not isinstance(catalog['models'], dict):
                raise ValueError("Invalid catalog structure: missing 'models' dict")
            
            _rag_catalog_cache = catalog
            logger.info(f"Loaded RAG model catalog: {len(catalog['models'])} models")
            return catalog.copy()
        else:
            logger.warning(f"RAG models config not found at {RAG_MODELS_PATH}, using defaults")
            _rag_catalog_cache = DEFAULT_RAG_CATALOG
            return DEFAULT_RAG_CATALOG.copy()
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {RAG_MODELS_PATH}: {e}")
        _rag_catalog_cache = DEFAULT_RAG_CATALOG
        return DEFAULT_RAG_CATALOG.copy()
    except Exception as e:
        logger.error(f"Failed to load RAG model catalog: {e}")
        _rag_catalog_cache = DEFAULT_RAG_CATALOG
        return DEFAULT_RAG_CATALOG.copy()


def get_rag_model(model_key: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific RAG model by key.
    
    Returns model dict with 'label', 'max_tokens', etc., or None if not found.
    """
    catalog = get_rag_model_catalog()
    model = catalog.get('models', {}).get(model_key)
    if model:
        # Include the key in the returned dict for convenience
        return {'key': model_key, **model}
    return None


def get_rag_model_keys() -> List[str]:
    """Get list of all valid RAG model keys."""
    catalog = get_rag_model_catalog()
    return list(catalog.get('models', {}).keys())


def get_default_rag_model_key() -> str:
    """Get the default RAG model key."""
    catalog = get_rag_model_catalog()
    return catalog.get('default_model', 'gpt-4.1')


def get_rag_models_list(sort_recommended_first: bool = True) -> List[Dict[str, Any]]:
    """
    Get RAG models as a flat list for API responses.
    
    Returns list of dicts with 'key', 'label', 'max_tokens', etc.
    Optionally sorts recommended models first.
    """
    catalog = get_rag_model_catalog()
    models = []
    
    for key, model in catalog.get('models', {}).items():
        models.append({
            'key': key,
            'label': model.get('label', key),
            'max_tokens': model.get('max_tokens', 128000),
            'supports_json_mode': model.get('supports_json_mode', True),
            'supports_128k_context': model.get('supports_128k_context', True),
            'recommended': model.get('recommended', False)
        })
    
    if sort_recommended_first:
        models.sort(key=lambda m: (not m['recommended'], m['label']))
    
    return models


def validate_rag_model_key(model_key: str) -> bool:
    """Check if a model key exists in the RAG catalog."""
    return model_key in get_rag_model_keys()


# =============================================================================
# Embedding Model Catalog
# =============================================================================

def get_embedding_model_catalog(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Load embedding model catalog from JSON file.
    
    Returns the full catalog dict with 'models', 'active_query_model', etc.
    Caches result in module-level variable.
    Falls back to DEFAULT_EMBEDDING_CATALOG if file missing/invalid.
    """
    global _embedding_catalog_cache
    
    if _embedding_catalog_cache is not None and not force_refresh:
        return _embedding_catalog_cache.copy()
    
    try:
        if EMBEDDING_MODELS_PATH.exists():
            with open(EMBEDDING_MODELS_PATH, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
            
            # Validate structure
            if 'models' not in catalog or not isinstance(catalog['models'], dict):
                raise ValueError("Invalid catalog structure: missing 'models' dict")
            
            _embedding_catalog_cache = catalog
            logger.info(f"Loaded embedding model catalog: {len(catalog['models'])} models")
            return catalog.copy()
        else:
            logger.warning(f"Embedding models config not found at {EMBEDDING_MODELS_PATH}, using defaults")
            _embedding_catalog_cache = DEFAULT_EMBEDDING_CATALOG
            return DEFAULT_EMBEDDING_CATALOG.copy()
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {EMBEDDING_MODELS_PATH}: {e}")
        _embedding_catalog_cache = DEFAULT_EMBEDDING_CATALOG
        return DEFAULT_EMBEDDING_CATALOG.copy()
    except Exception as e:
        logger.error(f"Failed to load embedding model catalog: {e}")
        _embedding_catalog_cache = DEFAULT_EMBEDDING_CATALOG
        return DEFAULT_EMBEDDING_CATALOG.copy()


def get_embedding_model(model_key: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific embedding model by key.
    
    Returns model dict with 'provider', 'model_name', 'dimensions', etc., or None if not found.
    """
    catalog = get_embedding_model_catalog()
    model = catalog.get('models', {}).get(model_key)
    if model:
        return {'key': model_key, **model}
    return None


def get_embedding_model_keys() -> List[str]:
    """Get list of all valid embedding model keys."""
    catalog = get_embedding_model_catalog()
    return list(catalog.get('models', {}).keys())


def get_embedding_models_list(sort_recommended_first: bool = True) -> List[Dict[str, Any]]:
    """
    Get embedding models as a flat list for API responses.
    
    Returns list of dicts with 'key', 'model_name', 'dimensions', etc.
    Optionally sorts recommended/production models first.
    """
    catalog = get_embedding_model_catalog()
    models = []
    
    for key, model in catalog.get('models', {}).items():
        models.append({
            'key': key,
            'provider': model.get('provider', 'unknown'),
            'model_name': model.get('model_name', key),
            'dimensions': model.get('dimensions', 384),
            'cost_per_1k': model.get('cost_per_1k', 0.0),
            'description': model.get('description', ''),
            'recommended': model.get('recommended', False),
            'production': model.get('production', False)
        })
    
    if sort_recommended_first:
        # Sort by: production first, then recommended, then by name
        models.sort(key=lambda m: (not m['production'], not m['recommended'], m['model_name']))
    
    return models


def save_embedding_model_catalog(catalog: Dict[str, Any]) -> None:
    """
    Save embedding model catalog to JSON file.
    
    Used by tuning endpoints to update active models.
    """
    try:
        # Ensure directory exists
        EMBEDDING_MODELS_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with open(EMBEDDING_MODELS_PATH, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, indent=2)
        
        # Clear cache to force reload
        global _embedding_catalog_cache
        _embedding_catalog_cache = None
        
        logger.info("Embedding model catalog saved")
    except Exception as e:
        logger.error(f"Failed to save embedding model catalog: {e}")
        raise
