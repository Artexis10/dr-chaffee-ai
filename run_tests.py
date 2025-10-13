#!/usr/bin/env python3
"""
Test runner for speaker identification fixes

Runs all tests and generates coverage report
"""
import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run all unit tests with coverage"""
    
    print("=" * 80)
    print("RUNNING SPEAKER IDENTIFICATION TESTS")
    print("=" * 80)
    print()
    
    # Test files
    test_files = [
        'tests/test_voice_enrollment_real_model.py',
        'tests/test_regenerate_speaker_labels.py'
    ]
    
    # Check test files exist
    for test_file in test_files:
        if not Path(test_file).exists():
            print(f"❌ Test file not found: {test_file}")
            return 1
    
    # Run tests with pytest
    print("Running tests with pytest...\n")
    
    cmd = [
        sys.executable, '-m', 'pytest',
        *test_files,
        '-v',  # Verbose
        '--tb=short',  # Short traceback
        '--color=yes',  # Colored output
        '--cov=backend/scripts/common',  # Coverage for voice_enrollment
        '--cov=.',  # Coverage for regenerate script
        '--cov-report=term-missing',  # Show missing lines
        '--cov-report=html:htmlcov',  # HTML report
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        
        print()
        print("=" * 80)
        
        if result.returncode == 0:
            print("✅ ALL TESTS PASSED!")
            print()
            print("Coverage report generated in: htmlcov/index.html")
        else:
            print("❌ SOME TESTS FAILED")
            print()
            print("Review the output above for details")
        
        print("=" * 80)
        
        return result.returncode
        
    except FileNotFoundError:
        print("❌ pytest not found. Install with: pip install pytest pytest-cov")
        return 1


def run_quick_validation():
    """Quick validation without full test suite"""
    
    print("\n" + "=" * 80)
    print("QUICK VALIDATION")
    print("=" * 80)
    print()
    
    # Check real model loads
    print("1. Checking real SpeechBrain model...")
    try:
        sys.path.insert(0, str(Path(__file__).parent / 'backend'))
        from backend.scripts.common.voice_enrollment_optimized import VoiceEnrollment
        
        enrollment = VoiceEnrollment(voices_dir='voices')
        model = enrollment._get_embedding_model()
        
        # Check it's real SpeechBrain
        if hasattr(model, 'mods') and hasattr(model, 'hparams'):
            print("   ✅ Real SpeechBrain ECAPA model loaded")
        else:
            print("   ❌ Model doesn't have SpeechBrain attributes")
            return 1
            
    except Exception as e:
        print(f"   ❌ Failed to load model: {e}")
        return 1
    
    # Check profile
    print("\n2. Checking Chaffee profile...")
    try:
        import json
        
        with open('voices/chaffee.json') as f:
            profile = json.load(f)
        
        dims = len(profile.get('centroid', []))
        num_emb = profile.get('metadata', {}).get('num_embeddings', 0)
        model_name = profile.get('metadata', {}).get('embedding_model', 'unknown')
        
        print(f"   Dimensions: {dims}")
        print(f"   Embeddings: {num_emb}")
        print(f"   Model: {model_name}")
        
        if dims == 192 and num_emb > 0 and 'speechbrain' in model_name:
            print("   ✅ Profile is valid (192-dim, real embeddings)")
        else:
            print("   ⚠️  Profile may have issues")
            
    except Exception as e:
        print(f"   ❌ Failed to load profile: {e}")
        return 1
    
    print("\n" + "=" * 80)
    print("✅ QUICK VALIDATION PASSED")
    print("=" * 80)
    
    return 0


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Run speaker identification tests")
    parser.add_argument('--quick', action='store_true',
                       help='Run quick validation only (no full test suite)')
    
    args = parser.parse_args()
    
    if args.quick:
        sys.exit(run_quick_validation())
    else:
        sys.exit(run_tests())
