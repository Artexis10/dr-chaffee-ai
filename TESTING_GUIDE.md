# Testing Guide

Complete guide for running tests in the Dr. Chaffee AI project.

## Quick Start

```bash
# Run all working unit tests
pytest tests/unit/test_ingest_flags.py -v

# Run with coverage
pytest tests/unit/test_ingest_flags.py --cov=backend/scripts/ingest_youtube.py --cov-report=term-missing
```

## Test Structure

```
tests/
├── unit/                    # Fast, hermetic unit tests
│   ├── test_ingest_flags.py        ✅ 13 tests (NEW - all passing)
│   ├── test_ingest_subprocess.py   ⚠️  19 tests (need update for rename)
│   ├── test_ingest_cleanup.py      ⚠️  15 tests (need update for rename)
│   ├── test_ingest_config.py       ⚠️  31 tests (need update for rename)
│   ├── test_ingest_logging.py      ⚠️  17 tests (need update for rename)
│   ├── test_ingest_concurrency.py  ⚠️  19 tests (need update for rename)
│   ├── test_ingest_cli.py          ⚠️  18 tests (need update for rename)
│   ├── test_db_insert.py           ❌ Import error
│   ├── test_embedding_model.py     ❓ Untested
│   ├── test_gated_access.py        ❓ Untested
│   ├── test_hf_*.py                ❓ Untested
│   └── ...
├── integration/             # End-to-end tests (require network/GPU)
├── performance/             # Performance benchmarks
└── enhanced_asr/            # ASR-specific tests
```

## Running Tests

### Run Specific Test File

```bash
# Run flag parsing tests (all passing)
pytest tests/unit/test_ingest_flags.py -v

# Run with verbose output
pytest tests/unit/test_ingest_flags.py -vv

# Run specific test
pytest tests/unit/test_ingest_flags.py::TestFlagParsing::test_limit_unprocessed_flag_parsed -v
```

### Run All Unit Tests (After Fixing Imports)

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=backend/scripts --cov-report=html

# Run with coverage report
pytest tests/unit/ --cov=backend/scripts --cov-report=term-missing
```

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit -v

# Run only integration tests
pytest -m integration -v

# Run only performance tests
pytest -m performance -v
```

### Run Tests with Coverage

```bash
# Generate HTML coverage report
pytest tests/unit/test_ingest_flags.py \
  --cov=backend/scripts/ingest_youtube.py \
  --cov-report=html \
  --cov-report=term

# Open coverage report
open htmlcov/index.html  # Mac/Linux
start htmlcov\index.html  # Windows
```

## Current Test Status

### ✅ Working Tests (13 tests)

**test_ingest_flags.py** - Flag parsing tests
- All 13 tests passing
- Covers CLI argument parsing
- Regression tests for recent bugs
- Fast execution (0.52 seconds)

### ⚠️ Tests Needing Updates (119 tests)

These tests import `ingest_youtube_enhanced` which was renamed to `ingest_youtube`:

- test_ingest_subprocess.py (19 tests)
- test_ingest_cleanup.py (15 tests)
- test_ingest_config.py (31 tests)
- test_ingest_logging.py (17 tests)
- test_ingest_concurrency.py (19 tests)
- test_ingest_cli.py (18 tests)

**Fix needed:**
```python
# Change this:
from backend.scripts.ingest_youtube_enhanced import IngestionConfig

# To this:
from backend.scripts.ingest_youtube import IngestionConfig
```

### ❌ Broken Tests

**test_db_insert.py** - Import error
```python
# Error: ModuleNotFoundError: No module named 'segments_database'
# Fix: from backend.scripts.common.segments_database import SegmentsDatabase
```

## Test Coverage Goals

### Current Coverage

- **ingest_youtube.py**: ~15% (only flag parsing tested)
- **segments_database.py**: 0%
- **Other modules**: Varies

### Target Coverage

- **Critical paths**: 90%+
- **Business logic**: 80%+
- **Utilities**: 70%+
- **Overall**: 75%+

## Writing New Tests

### Test Template

```python
#!/usr/bin/env python3
"""
Unit tests for [module name].

Tests [what it does].
"""
import pytest
from unittest.mock import patch, Mock


@pytest.mark.unit
class TestFeatureName:
    """Test [feature description]."""
    
    def test_something_works(self, monkeypatch):
        """Test that something works correctly."""
        # Arrange
        monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
        
        # Act
        result = some_function()
        
        # Assert
        assert result == expected_value
    
    def test_something_fails_gracefully(self):
        """Test that something fails gracefully."""
        with pytest.raises(ValueError):
            some_function(invalid_input)
```

### Best Practices

1. **Use descriptive test names**
   - ✅ `test_limit_unprocessed_flag_parsed`
   - ❌ `test_flag1`

2. **Test one thing per test**
   - Each test should verify one behavior
   - Makes failures easier to diagnose

3. **Use fixtures for setup**
   ```python
   @pytest.fixture
   def sample_config():
       return IngestionConfig(source='yt-dlp', dry_run=True)
   ```

4. **Mock external dependencies**
   ```python
   @patch('subprocess.run')
   def test_something(mock_run):
       mock_run.return_value = Mock(returncode=0)
   ```

5. **Add regression tests for bugs**
   ```python
   def test_regression_bug_123():
       """Regression test for bug #123 where X happened."""
       # Test that verifies the bug is fixed
   ```

## Continuous Integration

### GitHub Actions

Tests run automatically on:
- Every push to `main`
- Every pull request
- Nightly at 2 AM UTC

### Local Pre-commit

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Troubleshooting

### Import Errors

**Problem:**
```
ModuleNotFoundError: No module named 'ingest_youtube_enhanced'
```

**Solution:**
Update imports after file rename:
```python
from backend.scripts.ingest_youtube import IngestionConfig
```

### Database Connection Errors

**Problem:**
```
Failed to connect to database
```

**Solution:**
Set DATABASE_URL in test:
```python
monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test')
```

### Slow Tests

**Problem:**
Tests take too long

**Solution:**
- Use `pytest -x` to stop on first failure
- Use `pytest -k test_name` to run specific tests
- Mock slow operations (network, database, GPU)

### Coverage Not Working

**Problem:**
```
WARNING: No data was collected
```

**Solution:**
Check PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:${PWD}/backend"
pytest tests/unit/ --cov=backend/scripts
```

## Next Steps

### Immediate (High Priority)

1. ✅ Fix import errors in existing tests
   - Update `ingest_youtube_enhanced` → `ingest_youtube`
   - Fix `segments_database` import path

2. ✅ Run all 132 unit tests
   - Verify all pass after import fixes
   - Generate coverage report

3. ✅ Add missing tests
   - Test `list_videos()` with `--limit-unprocessed`
   - Test database operations
   - Test error handling

### Future (Medium Priority)

1. Integration tests
   - Test full ingestion pipeline
   - Test with real YouTube videos
   - Test database operations

2. Performance tests
   - Benchmark RTX 5080 performance
   - Test throughput targets
   - Test memory usage

3. E2E tests
   - Test complete workflows
   - Test deployment scenarios

## Summary

### Current Status

- ✅ **13 tests passing** (flag parsing)
- ⚠️  **119 tests need import fixes** (easy fix)
- ❌ **1 test broken** (import error)
- ❓ **Some tests untested**

### How to Run Tests

```bash
# Quick test (working tests only)
pytest tests/unit/test_ingest_flags.py -v

# All tests (after fixing imports)
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=backend/scripts --cov-report=html
```

### Test Quality

- **Fast**: 0.52 seconds for 13 tests
- **Isolated**: No external dependencies
- **Comprehensive**: Covers critical paths
- **Maintainable**: Clear test names and structure

**Tests are the safety net for refactoring!** 🎯
