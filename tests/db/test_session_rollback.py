#!/usr/bin/env python3
"""
Pytest tests for database session rollback hygiene
Ensures "current transaction is aborted" errors don't cascade
"""

import pytest
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture
def db_connection():
    """Create a test database connection"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        pytest.skip("DATABASE_URL not set")
    
    conn = psycopg2.connect(db_url)
    yield conn
    
    # Cleanup
    try:
        conn.rollback()
        conn.close()
    except:
        pass


@pytest.fixture
def test_table(db_connection):
    """Create a temporary test table"""
    cur = db_connection.cursor()
    
    # Create temp table
    cur.execute("""
        CREATE TEMP TABLE test_rollback (
            id SERIAL PRIMARY KEY,
            value INTEGER NOT NULL CHECK (value > 0)
        )
    """)
    db_connection.commit()
    
    yield "test_rollback"
    
    # Cleanup happens automatically with temp table


@pytest.mark.pgvector
class TestSessionRollback:
    """Test session rollback hygiene"""
    
    def test_failed_insert_then_valid_insert(self, db_connection, test_table):
        """Test that failed insert doesn't prevent subsequent valid inserts"""
        cur = db_connection.cursor()
        
        # First, insert a valid row
        cur.execute(f"INSERT INTO {test_table} (value) VALUES (10)")
        db_connection.commit()
        
        # Try to insert invalid value (violates CHECK constraint)
        try:
            cur.execute(f"INSERT INTO {test_table} (value) VALUES (-5)")
            db_connection.commit()
            pytest.fail("Should have raised constraint violation")
        except psycopg2.IntegrityError:
            # Expected error - must rollback
            db_connection.rollback()
        
        # Now insert valid value - should succeed
        cur.execute(f"INSERT INTO {test_table} (value) VALUES (20)")
        db_connection.commit()
        
        # Verify both valid rows exist
        cur.execute(f"SELECT COUNT(*) FROM {test_table}")
        count = cur.fetchone()[0]
        assert count == 2, "Valid inserts after rollback should succeed"
    
    def test_transaction_status_after_error(self, db_connection, test_table):
        """Test transaction status is reset after error"""
        cur = db_connection.cursor()
        
        # Cause an error
        try:
            cur.execute(f"INSERT INTO {test_table} (value) VALUES (-1)")
            db_connection.commit()
        except psycopg2.IntegrityError:
            pass  # Don't rollback yet
        
        # Check transaction status
        status = db_connection.get_transaction_status()
        # TRANSACTION_STATUS_INERROR = 3
        assert status == 3, "Transaction should be in error state"
        
        # Rollback to reset
        db_connection.rollback()
        
        # Check status is reset
        status = db_connection.get_transaction_status()
        # TRANSACTION_STATUS_IDLE = 0
        assert status == 0, "Transaction should be idle after rollback"
    
    def test_multiple_errors_with_rollback(self, db_connection, test_table):
        """Test multiple errors with proper rollback between each"""
        cur = db_connection.cursor()
        
        for i in range(3):
            # Try invalid insert
            try:
                cur.execute(f"INSERT INTO {test_table} (value) VALUES (-{i})")
                db_connection.commit()
            except psycopg2.IntegrityError:
                db_connection.rollback()
            
            # Insert valid value
            cur.execute(f"INSERT INTO {test_table} (value) VALUES ({i + 1})")
            db_connection.commit()
        
        # Should have 3 valid rows
        cur.execute(f"SELECT COUNT(*) FROM {test_table}")
        count = cur.fetchone()[0]
        assert count == 3
    
    def test_nested_transaction_rollback(self, db_connection, test_table):
        """Test rollback in nested transaction scenario"""
        cur = db_connection.cursor()
        
        # Start transaction
        cur.execute(f"INSERT INTO {test_table} (value) VALUES (100)")
        
        # Cause error mid-transaction
        try:
            cur.execute(f"INSERT INTO {test_table} (value) VALUES (-100)")
        except psycopg2.IntegrityError:
            # Rollback entire transaction
            db_connection.rollback()
        
        # Verify nothing was committed
        cur.execute(f"SELECT COUNT(*) FROM {test_table}")
        count = cur.fetchone()[0]
        assert count == 0, "Rollback should undo all changes in transaction"
    
    def test_connection_recovery_after_error(self, db_connection, test_table):
        """Test connection can be reused after error and rollback"""
        cur = db_connection.cursor()
        
        # Cause error
        try:
            cur.execute(f"INSERT INTO {test_table} (value) VALUES (-1)")
            db_connection.commit()
        except psycopg2.IntegrityError:
            db_connection.rollback()
        
        # Connection should be usable
        cur.execute("SELECT 1")
        result = cur.fetchone()[0]
        assert result == 1
        
        # Can perform valid operations
        cur.execute(f"INSERT INTO {test_table} (value) VALUES (50)")
        db_connection.commit()
        
        cur.execute(f"SELECT value FROM {test_table}")
        values = [row[0] for row in cur.fetchall()]
        assert 50 in values


class TestSegmentsDatabaseRollback:
    """Test rollback hygiene in SegmentsDatabase class"""
    
    @pytest.fixture
    def segments_db(self):
        """Create SegmentsDatabase instance"""
        import sys
        from pathlib import Path
        
        backend_dir = Path(__file__).parent.parent.parent / 'backend'
        sys.path.insert(0, str(backend_dir))
        
        from scripts.common.segments_database import SegmentsDatabase
        
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        db = SegmentsDatabase(db_url)
        yield db
        
        # Cleanup
        try:
            if db.connection and not db.connection.closed:
                db.connection.rollback()
                db.connection.close()
        except:
            pass
    
    def test_get_connection_recovers_from_error(self, segments_db):
        """Test get_connection() recovers from failed transaction state"""
        conn = segments_db.get_connection()
        
        # Force connection into error state
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM nonexistent_table_xyz")
        except psycopg2.ProgrammingError:
            pass  # Expected error
        
        # get_connection should detect and fix error state
        conn = segments_db.get_connection()
        status = conn.get_transaction_status()
        
        # Should be idle (0) or in transaction (2), not in error (3)
        assert status != 3, "Connection should not be in error state after get_connection()"
    
    def test_check_video_exists_handles_errors(self, segments_db):
        """Test check_video_exists handles errors gracefully"""
        # Call with invalid video_id that might cause issues
        source_id, count = segments_db.check_video_exists("test_invalid_video_123")
        
        # Should return None, 0 without crashing
        assert source_id is None or isinstance(source_id, int)
        assert isinstance(count, int)
        
        # Connection should still be usable
        conn = segments_db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
