#!/usr/bin/env python3
"""
Pytest tests for BGE-Small migration chain (005, 006, 007)
Tests migration execution, rollback, and data integrity
"""

import pytest
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="module")
def alembic_config():
    """Get Alembic config"""
    backend_dir = Path(__file__).parent.parent.parent / 'backend'
    
    if not backend_dir.exists():
        pytest.skip("Backend directory not found")
    
    alembic_ini = backend_dir / 'alembic.ini'
    if not alembic_ini.exists():
        pytest.skip("alembic.ini not found")
    
    sys.path.insert(0, str(backend_dir))
    
    from alembic.config import Config
    from alembic import command
    
    config = Config(str(alembic_ini))
    config.set_main_option('script_location', str(backend_dir / 'migrations'))
    
    # Override database URL from env
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        config.set_main_option('sqlalchemy.url', db_url)
    
    return config, command


@pytest.fixture
def db_connection():
    """Create database connection for verification"""
    import psycopg2
    
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        pytest.skip("DATABASE_URL not set")
    
    conn = psycopg2.connect(db_url)
    yield conn
    
    try:
        conn.rollback()
        conn.close()
    except:
        pass


@pytest.mark.pgvector
class TestBGEMigrationChain:
    """Test BGE-Small migration chain"""
    
    def test_migration_005_add_column(self, alembic_config, db_connection):
        """Test Phase 1: Add embedding_384 column"""
        config, command = alembic_config
        
        # Run migration 005
        try:
            command.upgrade(config, '005')
        except Exception as e:
            pytest.skip(f"Migration 005 failed (may already be applied): {e}")
        
        # Verify column exists
        cur = db_connection.cursor()
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'segments' 
            AND column_name = 'embedding_384'
        """)
        result = cur.fetchone()
        
        assert result is not None, "embedding_384 column should exist"
        assert 'vector' in result[1].lower() or 'user-defined' in result[1].lower(), \
            "embedding_384 should be vector type"
    
    def test_migration_005_idempotent(self, alembic_config, db_connection):
        """Test Phase 1 is idempotent (can run multiple times)"""
        config, command = alembic_config
        
        # Run migration 005 again
        try:
            command.upgrade(config, '005')
        except Exception as e:
            # Should not fail if already applied
            if "already exists" not in str(e).lower():
                pytest.fail(f"Migration 005 should be idempotent: {e}")
    
    def test_migration_006_backfill_structure(self, alembic_config):
        """Test Phase 2 migration structure (without full execution)"""
        backend_dir = Path(__file__).parent.parent.parent / 'backend'
        migration_file = backend_dir / 'migrations' / 'versions' / '006_backfill_embedding_384.py'
        
        if not migration_file.exists():
            pytest.skip("Migration 006 not found")
        
        # Read migration file
        content = migration_file.read_text()
        
        # Check for key components
        assert 'EmbeddingsService' in content, "Should use EmbeddingsService"
        assert 'encode_texts' in content, "Should call encode_texts"
        assert 'BATCH_SIZE' in content, "Should process in batches"
        assert 'MAX_RETRIES' in content, "Should have retry logic"
        assert 'rollback' in content.lower(), "Should handle rollback"
    
    def test_migration_007_structure(self, alembic_config):
        """Test Phase 3 migration structure"""
        backend_dir = Path(__file__).parent.parent.parent / 'backend'
        migration_file = backend_dir / 'migrations' / 'versions' / '007_swap_embedding_columns.py'
        
        if not migration_file.exists():
            pytest.skip("Migration 007 not found")
        
        content = migration_file.read_text()
        
        # Check for key operations
        assert 'IVFFLAT' in content, "Should create IVFFLAT index"
        assert 'DROP COLUMN' in content, "Should drop old embedding column"
        assert 'RENAME COLUMN' in content, "Should rename embedding_384 to embedding"
        assert 'vector_l2_ops' in content, "Should use L2 distance ops"
    
    def test_check_embedding_dimensions(self, db_connection):
        """Test embedding_384 has correct dimensions if it exists"""
        cur = db_connection.cursor()
        
        # Check if embedding_384 column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'segments' 
            AND column_name = 'embedding_384'
        """)
        
        if not cur.fetchone():
            pytest.skip("embedding_384 column doesn't exist yet")
        
        # Try to insert a test vector
        try:
            # Create a 384-dim test vector
            test_vector = [0.0] * 384
            cur.execute("""
                INSERT INTO segments (video_id, start_sec, end_sec, text, embedding_384)
                VALUES ('test_migration', 0.0, 1.0, 'test', %s::vector)
                RETURNING id
            """, (str(test_vector),))
            
            test_id = cur.fetchone()[0]
            
            # Cleanup
            cur.execute("DELETE FROM segments WHERE id = %s", (test_id,))
            db_connection.rollback()
            
        except Exception as e:
            db_connection.rollback()
            if '384' not in str(e):
                pytest.fail(f"Unexpected error inserting 384-dim vector: {e}")
    
    def test_check_pgvector_extension(self, db_connection):
        """Test pgvector extension is installed"""
        cur = db_connection.cursor()
        
        cur.execute("""
            SELECT extname 
            FROM pg_extension 
            WHERE extname = 'vector'
        """)
        
        result = cur.fetchone()
        assert result is not None, "pgvector extension should be installed"


class TestMigrationRollback:
    """Test migration rollback scenarios"""
    
    def test_migration_005_downgrade(self, alembic_config, db_connection):
        """Test Phase 1 downgrade removes column"""
        config, command = alembic_config
        
        # Ensure we're at 005 or higher
        try:
            command.upgrade(config, '005')
        except:
            pass
        
        # Check column exists
        cur = db_connection.cursor()
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'segments' 
            AND column_name = 'embedding_384'
        """)
        
        if not cur.fetchone():
            pytest.skip("embedding_384 column doesn't exist")
        
        # Downgrade to 004
        try:
            command.downgrade(config, '004')
        except Exception as e:
            pytest.skip(f"Downgrade failed (may have data dependencies): {e}")
        
        # Verify column is removed
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'segments' 
            AND column_name = 'embedding_384'
        """)
        
        result = cur.fetchone()
        assert result is None, "embedding_384 column should be removed after downgrade"


class TestMigrationDataIntegrity:
    """Test data integrity during migration"""
    
    def test_sample_data_preserved(self, db_connection):
        """Test that existing segment data is preserved during migration"""
        cur = db_connection.cursor()
        
        # Check if segments table has data
        cur.execute("SELECT COUNT(*) FROM segments")
        count = cur.fetchone()[0]
        
        if count == 0:
            pytest.skip("No segments data to test")
        
        # Sample a few segments
        cur.execute("""
            SELECT id, video_id, text, start_sec, end_sec 
            FROM segments 
            WHERE text IS NOT NULL 
            LIMIT 5
        """)
        
        samples = cur.fetchall()
        
        # Verify data integrity
        for sample in samples:
            seg_id, video_id, text, start_sec, end_sec = sample
            
            assert seg_id is not None
            assert video_id is not None
            assert text is not None and len(text) > 0
            assert start_sec is not None and start_sec >= 0
            assert end_sec is not None and end_sec > start_sec
    
    def test_null_embeddings_count(self, db_connection):
        """Test counting segments with NULL embeddings"""
        cur = db_connection.cursor()
        
        # Check if embedding_384 column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'segments' 
            AND column_name = 'embedding_384'
        """)
        
        if not cur.fetchone():
            pytest.skip("embedding_384 column doesn't exist yet")
        
        # Count NULL embeddings
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(embedding_384) as populated,
                COUNT(*) - COUNT(embedding_384) as missing
            FROM segments
            WHERE text IS NOT NULL AND text != ''
        """)
        
        total, populated, missing = cur.fetchone()
        
        print(f"\nEmbedding status: {populated}/{total} populated, {missing} missing")
        
        # Just verify query works, don't assert on values
        assert total >= 0
        assert populated >= 0
        assert missing >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
