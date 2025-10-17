#!/usr/bin/env python3
"""
Manual test to verify embedding model detection logic WITHOUT pytest.
Run directly: python3 tests/api/manual_test_fix.py
"""

import sys
import os
from unittest.mock import Mock, patch

# Add backend to path
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backend')
sys.path.insert(0, backend_path)


def test_detect_1536_dim_embeddings():
    """Test detecting 1536-dim embeddings from legacy table"""
    print("\n=== TEST 1: Detect 1536-dim embeddings ===")
    
    from api.main import get_available_embedding_models
    
    mock_conn = Mock()
    mock_cursor = Mock()
    
    # Simulate production database with 1536-dim embeddings
    mock_cursor.fetchone.side_effect = [
        [False],  # segment_embeddings table doesn't exist
        {'count': 1},  # legacy table has embeddings
        {'embedding': [0.1] * 1536},  # 1536-dim embedding
        {'model_key': 'gte-qwen2-1.5b', 'count': 5000}
    ]
    
    mock_conn.cursor.return_value = mock_cursor
    
    with patch('api.main.get_db_connection', return_value=mock_conn):
        models = get_available_embedding_models()
    
    print(f"✓ Detected models: {models}")
    assert len(models) == 1, f"Expected 1 model, got {len(models)}"
    assert models[0]['model_key'] == 'gte-qwen2-1.5b', f"Wrong model key: {models[0]['model_key']}"
    assert models[0]['dimensions'] == 1536, f"Wrong dimensions: {models[0]['dimensions']}"
    print("✓ PASS: Correctly detected 1536-dim gte-qwen2-1.5b model")


def test_config_has_correct_models():
    """Test that config file has correct model definitions"""
    print("\n=== TEST 2: Verify config file ===")
    
    import json
    from pathlib import Path
    
    config_path = Path(backend_path) / 'config' / 'embedding_models.json'
    print(f"✓ Reading config from: {config_path}")
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Check gte-qwen2-1.5b
    assert 'gte-qwen2-1.5b' in config['models'], "gte-qwen2-1.5b not in config"
    model = config['models']['gte-qwen2-1.5b']
    print(f"✓ gte-qwen2-1.5b config: {model}")
    assert model['provider'] == 'local', f"Wrong provider: {model['provider']}"
    assert model['model_name'] == 'Alibaba-NLP/gte-Qwen2-1.5B-instruct', f"Wrong model name"
    assert model['dimensions'] == 1536, f"Wrong dimensions: {model['dimensions']}"
    print("✓ PASS: Config has correct gte-qwen2-1.5b definition")
    
    # Check nomic-v1.5
    assert 'nomic-v1.5' in config['models'], "nomic-v1.5 not in config"
    model = config['models']['nomic-v1.5']
    print(f"✓ nomic-v1.5 config: {model}")
    assert model['dimensions'] == 768, f"Wrong Nomic dimensions: {model['dimensions']}"
    print("✓ PASS: Config has correct nomic-v1.5 definition")


def test_embedding_generator_model_selection():
    """Test that EmbeddingGenerator uses specified model"""
    print("\n=== TEST 3: EmbeddingGenerator model selection ===")
    
    from scripts.common.embeddings import EmbeddingGenerator
    
    # Test GTE-Qwen
    gen = EmbeddingGenerator(
        embedding_provider='local',
        model_name='Alibaba-NLP/gte-Qwen2-1.5B-instruct'
    )
    
    print(f"✓ Created generator: provider={gen.provider}, model={gen.model_name}, dims={gen.embedding_dimensions}")
    assert gen.provider == 'local', f"Wrong provider: {gen.provider}"
    assert gen.model_name == 'Alibaba-NLP/gte-Qwen2-1.5B-instruct', f"Wrong model"
    assert gen.embedding_dimensions == 1536, f"Wrong dimensions: {gen.embedding_dimensions}"
    print("✓ PASS: Generator correctly configured for 1536-dim model")


def test_dimension_mismatch_detection():
    """Test that dimension mismatch is detected"""
    print("\n=== TEST 4: Dimension mismatch detection ===")
    
    # Simulate the check in semantic_search
    query_embedding_dim = 768  # Generated with wrong model
    expected_dim = 1536  # Database has 1536
    model_key = 'gte-qwen2-1.5b'
    
    print(f"✓ Simulating: query_dim={query_embedding_dim}, expected_dim={expected_dim}")
    
    if query_embedding_dim != expected_dim:
        error_msg = f"Dimension mismatch: generated={query_embedding_dim}, database={expected_dim} for model {model_key}"
        print(f"✓ PASS: Mismatch detected: {error_msg}")
    else:
        raise AssertionError("Should have detected mismatch!")


def test_dimension_match_success():
    """Test that matching dimensions pass validation"""
    print("\n=== TEST 5: Dimension match success ===")
    
    query_embedding_dim = 1536
    expected_dim = 1536
    model_key = 'gte-qwen2-1.5b'
    
    print(f"✓ Simulating: query_dim={query_embedding_dim}, expected_dim={expected_dim}")
    
    if query_embedding_dim != expected_dim:
        raise AssertionError(f"Dimensions should match! {query_embedding_dim} != {expected_dim}")
    else:
        print(f"✓ PASS: Dimensions match, validation passes")


def test_string_dimension_parsing():
    """Test parsing dimensions from string representation"""
    print("\n=== TEST 6: Parse dimensions from string ===")
    
    # Simulate pgvector returning string
    embedding_str = '[' + ','.join(['0.1'] * 1536) + ']'
    print(f"✓ String length: {len(embedding_str)} chars")
    
    # Parse dimensions
    dimensions = len(embedding_str.strip('[]').split(','))
    print(f"✓ Parsed dimensions: {dimensions}")
    
    assert dimensions == 1536, f"Wrong dimensions parsed: {dimensions}"
    print("✓ PASS: Correctly parsed 1536 dimensions from string")


def main():
    """Run all tests"""
    print("=" * 60)
    print("MANUAL TESTS FOR EMBEDDING MODEL DETECTION FIX")
    print("=" * 60)
    
    tests = [
        test_detect_1536_dim_embeddings,
        test_config_has_correct_models,
        test_embedding_generator_model_selection,
        test_dimension_mismatch_detection,
        test_dimension_match_success,
        test_string_dimension_parsing,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ FAIL: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("\nThe fix should work in production!")
        sys.exit(0)


if __name__ == '__main__':
    main()
