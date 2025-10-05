# Testing Safety Guidelines

**CRITICAL: Never run tests against production database!**

## What Happened

A test file (`test_db_insert.py`) executed `TRUNCATE segments, sources CASCADE` against the **production database**, deleting all data.

**This must never happen again.**

## Safety Rules

### 1. **Tests MUST Use Test Database**

All tests that touch the database must use a separate test database:

```python
# ❌ WRONG - Uses production database
from dotenv import load_dotenv
load_dotenv()  # Loads production DATABASE_URL
db = SegmentsDatabase()

# ✅ CORRECT - Uses test database
@pytest.fixture
def test_db(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test_db')
    return SegmentsDatabase()
```

### 2. **Never TRUNCATE in Tests**

```python
# ❌ FORBIDDEN
cur.execute('TRUNCATE segments, sources CASCADE')

# ✅ Use fixtures with rollback
@pytest.fixture
def db_session():
    conn = psycopg2.connect(TEST_DATABASE_URL)
    yield conn
    conn.rollback()  # Rollback after test
    conn.close()
```

### 3. **Never DELETE in Tests**

```python
# ❌ FORBIDDEN
cur.execute('DELETE FROM segments')

# ✅ Use transactions
with conn:
    # Test operations
    conn.rollback()  # Always rollback
```

### 4. **Use Markers for Dangerous Tests**

```python
@pytest.mark.integration
@pytest.mark.requires_test_db
def test_database_operation():
    # Only runs when explicitly requested
    pass
```

## Safe Test Structure

### Example: Safe Database Test

```python
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_db(monkeypatch):
    """Mock database - never touches real DB"""
    monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost/test_db')
    return SegmentsDatabase()

def test_insert_segment(mock_db):
    """Test using mocked database"""
    # This won't touch production
    result = mock_db.insert_segment(...)
    assert result is not None
```

### Example: Integration Test (Isolated)

```python
@pytest.mark.integration
def test_real_db_operation():
    """Integration test with real test database"""
    # Use separate test database
    test_db_url = "postgresql://test:test@localhost/test_db_integration"
    db = SegmentsDatabase(db_url=test_db_url)
    
    # Setup test data
    db.insert_test_data()
    
    # Run test
    result = db.query()
    
    # Cleanup
    db.cleanup_test_data()
```

## pytest.ini Configuration

The `pytest.ini` file now sets a test database by default:

```ini
[pytest]
env =
    DATABASE_URL=postgresql://test:test@localhost:5432/test_db
```

**This prevents tests from accidentally using production.**

## Running Tests Safely

### Safe Commands

```bash
# Unit tests (no database)
pytest tests/unit/ -m unit -v

# With test database override
DATABASE_URL=postgresql://test:test@localhost/test_db pytest tests/unit/ -v

# Integration tests (explicit)
pytest tests/integration/ -m integration -v
```

### Dangerous Commands (AVOID)

```bash
# ❌ Don't run all tests without checking
pytest tests/ -v

# ❌ Don't run without database override
pytest tests/unit/test_db_*.py
```

## Checklist Before Running Tests

- [ ] Check test file doesn't have TRUNCATE/DELETE
- [ ] Verify test uses test database or mocks
- [ ] Confirm DATABASE_URL points to test DB
- [ ] Review test code for destructive operations
- [ ] Run with `-v` to see what's executing

## Files Removed

The following dangerous test was removed:

- ❌ `tests/unit/test_db_insert.py` - TRUNCATED production database

## Prevention Measures

1. ✅ Deleted dangerous test file
2. ✅ Updated pytest.ini with test database
3. ✅ Created this safety guide
4. ✅ Added to .gitignore: `**/test_db_*.py` (dangerous test patterns)

## Recovery Plan

If database is accidentally wiped:

1. **Check for backups** (Supabase/Railway auto-backups)
2. **Point-in-time recovery** (if available)
3. **Re-run ingestion** with `--limit-unprocessed`

## Summary

**Golden Rule:** Tests should NEVER modify production data.

- Use test databases
- Use mocks
- Use transactions with rollback
- Never TRUNCATE or DELETE in tests
- Always review test code before running

**When in doubt, don't run it against production!**
