"""
Test embedding model detection and matching logic for production fix.

This tests the critical path:
1. Detect available embeddings in database
2. Match model config
3. Generate query embedding with correct model
4. Verify dimensions match

Prevents: "different vector dimensions 1536 and 768" error
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add backend to path
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backend')
sys.path.insert(0, backend_path)


class TestEmbeddingModelDetection:
    """Test the embedding model detection logic"""
    
    def test_detect_legacy_embeddings_1536_dims(self):
        """Test detecting 1536-dim embeddings from legacy segments table"""
        from api.main import get_available_embedding_models
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        
        # Setup mock responses
        # 1. Check for normalized table - doesn't exist
        mock_cursor.fetchone.side_effect = [
            {'exists': False},  # segment_embeddings table doesn't exist
            {'count': 1},  # legacy table has embeddings
            # Sample embedding (1536 dims represented as list)
            {'embedding': [0.1] * 1536},
            # Model info
            {'model_key': 'gte-qwen2-1.5b', 'count': 5000}
        ]
        
        mock_conn.cursor.return_value = mock_cursor
        
        with patch('api.main.get_db_connection', return_value=mock_conn):
            models = get_available_embedding_models()
        
        # Verify results
        assert len(models) == 1
        assert models[0]['model_key'] == 'gte-qwen2-1.5b'
        assert models[0]['dimensions'] == 1536
        assert models[0]['count'] == 5000
    
    def test_detect_legacy_embeddings_768_dims(self):
        """Test detecting 768-dim Nomic embeddings from legacy table"""
        from api.main import get_available_embedding_models
        
        mock_conn = Mock()
        mock_cursor = Mock()
        
        mock_cursor.fetchone.side_effect = [
            {'exists': False},
            {'count': 1},
            {'embedding': [0.1] * 768},  # Nomic dimensions
            {'model_key': 'nomic-v1.5', 'count': 3000}
        ]
        
        mock_conn.cursor.return_value = mock_cursor
        
        with patch('api.main.get_db_connection', return_value=mock_conn):
            models = get_available_embedding_models()
        
        assert len(models) == 1
        assert models[0]['model_key'] == 'nomic-v1.5'
        assert models[0]['dimensions'] == 768
    
    def test_detect_normalized_embeddings(self):
        """Test detecting embeddings from normalized segment_embeddings table"""
        from api.main import get_available_embedding_models
        
        mock_conn = Mock()
        mock_cursor = Mock()
        
        # Normalized table exists and has data
        mock_cursor.fetchone.side_effect = [
            {'exists': True},  # segment_embeddings exists
            {'count': 5000}  # has data
        ]
        
        mock_cursor.fetchall.return_value = [
            {'model_key': 'gte-qwen2-1.5b', 'dimensions': 1536, 'count': 5000},
            {'model_key': 'nomic-v1.5', 'dimensions': 768, 'count': 2000}
        ]
        
        mock_conn.cursor.return_value = mock_cursor
        
        with patch('api.main.get_db_connection', return_value=mock_conn):
            models = get_available_embedding_models()
        
        assert len(models) == 2
        assert models[0]['model_key'] == 'gte-qwen2-1.5b'
        assert models[0]['dimensions'] == 1536
        assert models[1]['model_key'] == 'nomic-v1.5'
        assert models[1]['dimensions'] == 768
    
    def test_no_embeddings_found(self):
        """Test when no embeddings exist in database"""
        from api.main import get_available_embedding_models
        
        mock_conn = Mock()
        mock_cursor = Mock()
        
        mock_cursor.fetchone.side_effect = [
            {'exists': False},
            {'count': 0}  # No embeddings
        ]
        
        mock_conn.cursor.return_value = mock_cursor
        
        with patch('api.main.get_db_connection', return_value=mock_conn):
            models = get_available_embedding_models()
        
        assert models == []
    
    def test_dimension_detection_from_string(self):
        """Test dimension detection when embedding is returned as string"""
        from api.main import get_available_embedding_models
        
        mock_conn = Mock()
        mock_cursor = Mock()
        
        # Simulate pgvector returning string representation
        embedding_str = '[' + ','.join(['0.1'] * 1536) + ']'
        
        mock_cursor.fetchone.side_effect = [
            {'exists': False},
            {'count': 1},
            {'embedding': embedding_str},  # String format
            {'model_key': 'gte-qwen2-1.5b', 'count': 5000}
        ]
        
        mock_conn.cursor.return_value = mock_cursor
        
        with patch('api.main.get_db_connection', return_value=mock_conn):
            models = get_available_embedding_models()
        
        assert models[0]['dimensions'] == 1536


class TestSearchEndpointModelMatching:
    """Test the search endpoint's model matching logic"""
    
    @pytest.mark.asyncio
    async def test_search_with_1536_dim_database(self):
        """Test search correctly uses 1536-dim model when database has 1536-dim embeddings"""
        from api.main import semantic_search, SearchRequest
        
        # Mock the detection to return 1536-dim model
        with patch('api.main.get_available_embedding_models') as mock_detect:
            mock_detect.return_value = [
                {'model_key': 'gte-qwen2-1.5b', 'dimensions': 1536, 'count': 5000}
            ]
            
            # Mock config loading
            config = {
                'models': {
                    'gte-qwen2-1.5b': {
                        'provider': 'local',
                        'model_name': 'Alibaba-NLP/gte-Qwen2-1.5B-instruct',
                        'dimensions': 1536
                    }
                }
            }
            
            # Mock embedding generator
            mock_generator = Mock()
            mock_generator.generate_embeddings.return_value = [[0.1] * 1536]
            
            # Mock database
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value = mock_cursor
            
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = str(config)
                
                with patch('json.load', return_value=config):
                    with patch('api.main.EmbeddingGenerator', return_value=mock_generator):
                        with patch('api.main.get_db_connection', return_value=mock_conn):
                            with patch('api.main.use_normalized_embeddings', return_value=False):
                                request = SearchRequest(query="test query")
                                
                                try:
                                    result = await semantic_search(request)
                                    # Should succeed without dimension mismatch error
                                    assert result is not None
                                except Exception as e:
                                    # Should NOT raise dimension mismatch error
                                    assert "dimension mismatch" not in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_search_dimension_mismatch_detected(self):
        """Test that dimension mismatch is detected and raises clear error"""
        from api.main import semantic_search, SearchRequest
        from fastapi import HTTPException
        
        with patch('api.main.get_available_embedding_models') as mock_detect:
            mock_detect.return_value = [
                {'model_key': 'gte-qwen2-1.5b', 'dimensions': 1536, 'count': 5000}
            ]
            
            config = {
                'models': {
                    'gte-qwen2-1.5b': {
                        'provider': 'local',
                        'model_name': 'Alibaba-NLP/gte-Qwen2-1.5B-instruct',
                        'dimensions': 1536
                    }
                }
            }
            
            # Mock generator returns WRONG dimensions (768 instead of 1536)
            mock_generator = Mock()
            mock_generator.generate_embeddings.return_value = [[0.1] * 768]  # WRONG!
            
            with patch('json.load', return_value=config):
                with patch('api.main.EmbeddingGenerator', return_value=mock_generator):
                    request = SearchRequest(query="test query")
                    
                    with pytest.raises(HTTPException) as exc_info:
                        await semantic_search(request)
                    
                    # Should raise dimension mismatch error
                    assert exc_info.value.status_code == 503
                    assert "dimension mismatch" in str(exc_info.value.detail).lower()
                    assert "768" in str(exc_info.value.detail)
                    assert "1536" in str(exc_info.value.detail)


class TestEmbeddingGeneratorModelSelection:
    """Test that EmbeddingGenerator uses the correct model"""
    
    def test_generator_uses_specified_model(self):
        """Test that generator respects model_name parameter"""
        from scripts.common.embeddings import EmbeddingGenerator
        
        # Test with GTE-Qwen model
        gen = EmbeddingGenerator(
            embedding_provider='local',
            model_name='Alibaba-NLP/gte-Qwen2-1.5B-instruct'
        )
        
        assert gen.provider == 'local'
        assert gen.model_name == 'Alibaba-NLP/gte-Qwen2-1.5B-instruct'
        assert gen.embedding_dimensions == 1536
    
    def test_generator_nomic_model(self):
        """Test Nomic model configuration"""
        from scripts.common.embeddings import EmbeddingGenerator
        
        with patch.dict(os.environ, {'NOMIC_API_KEY': 'test-key'}):
            gen = EmbeddingGenerator(
                embedding_provider='nomic',
                model_name='nomic-embed-text-v1.5'
            )
            
            assert gen.provider == 'nomic'
            assert gen.model_name == 'nomic-embed-text-v1.5'
            assert gen.embedding_dimensions == 768


class TestConfigModelDefinitions:
    """Test that config has correct model definitions"""
    
    def test_config_has_gte_qwen_model(self):
        """Test config defines gte-qwen2-1.5b correctly"""
        import json
        from pathlib import Path
        
        config_path = Path(backend_path) / 'config' / 'embedding_models.json'
        with open(config_path) as f:
            config = json.load(f)
        
        assert 'gte-qwen2-1.5b' in config['models']
        model = config['models']['gte-qwen2-1.5b']
        assert model['provider'] == 'local'
        assert model['model_name'] == 'Alibaba-NLP/gte-Qwen2-1.5B-instruct'
        assert model['dimensions'] == 1536
    
    def test_config_has_nomic_model(self):
        """Test config defines nomic-v1.5 correctly"""
        import json
        from pathlib import Path
        
        config_path = Path(backend_path) / 'config' / 'embedding_models.json'
        with open(config_path) as f:
            config = json.load(f)
        
        assert 'nomic-v1.5' in config['models']
        model = config['models']['nomic-v1.5']
        assert model['provider'] == 'nomic'
        assert model['model_name'] == 'nomic-embed-text-v1.5'
        assert model['dimensions'] == 768


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
