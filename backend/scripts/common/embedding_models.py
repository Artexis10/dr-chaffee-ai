#!/usr/bin/env python3
"""
Embedding Model Registry - Configuration-driven model management
No database schema changes needed when switching between models with same dimensions
"""
import json
import os
from pathlib import Path
from typing import Dict, Any

class EmbeddingModelRegistry:
    """Manages embedding model configurations"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # New location: backend/config/models/embedding_models.json
            config_path = Path(__file__).parent.parent.parent / 'config' / 'models' / 'embedding_models.json'
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.models = self.config['models']
        self.active_model_key = os.getenv('EMBEDDING_MODEL_KEY', self.config['active_model'])
    
    def get_active_model(self) -> Dict[str, Any]:
        """Get configuration for the currently active model"""
        return self.models[self.active_model_key]
    
    def get_model(self, model_key: str) -> Dict[str, Any]:
        """Get configuration for a specific model"""
        return self.models.get(model_key)
    
    def can_switch_without_reembedding(self, from_model: str, to_model: str) -> bool:
        """Check if we can switch models without re-embedding (same dimensions)"""
        from_config = self.models.get(from_model)
        to_config = self.models.get(to_model)
        
        if not from_config or not to_config:
            return False
        
        return (
            from_config['dimensions'] == to_config['dimensions'] and
            from_config['db_column'] == to_config['db_column']
        )
    
    def list_compatible_models(self, current_model: str) -> list:
        """List all models compatible with current embeddings (same dimensions)"""
        current = self.models.get(current_model)
        if not current:
            return []
        
        compatible = []
        for key, model in self.models.items():
            if model['dimensions'] == current['dimensions']:
                compatible.append({
                    'key': key,
                    'name': model['model_name'],
                    'provider': model['provider'],
                    'cost': model['cost_per_1k']
                })
        
        return compatible

# Global registry instance
_registry = None

def get_registry() -> EmbeddingModelRegistry:
    """Get the global model registry"""
    global _registry
    if _registry is None:
        _registry = EmbeddingModelRegistry()
    return _registry
