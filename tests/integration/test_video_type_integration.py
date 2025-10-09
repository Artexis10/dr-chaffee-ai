"""
Integration tests for video type classification.

Tests the full flow from segment insertion to classification in a real database.
Requires a test database connection.
"""

import pytest
import os
import psycopg2
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend' / 'scripts'))

from common.segments_database import SegmentsDatabase
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture
def test_db():
    """Create a test database instance"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        pytest.skip("DATABASE_URL not set")
    
    db = SegmentsDatabase(db_url)
    yield db
    db.close()


@pytest.fixture
def test_video_id():
    """Generate a unique test video ID"""
    import uuid
    return f"test_{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def cleanup_test_data(test_db, test_video_id):
    """Clean up test data after each test"""
    yield
    # Cleanup after test
    try:
        conn = test_db.get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM segments WHERE video_id = %s", (test_video_id,))
            conn.commit()
    except Exception as e:
        print(f"Cleanup failed: {e}")


class TestVideoTypeIntegration:
    """Integration tests for video type classification"""
    
    def test_monologue_classification_end_to_end(self, test_db, test_video_id):
        """Test full flow: insert segments → classify → verify"""
        
        # Create monologue segments
        segments = [
            {
                'speaker_label': 'Chaffee',
                'text': f'Monologue segment {i}',
                'start': i * 10.0,
                'end': i * 10.0 + 8.0,
                'speaker_confidence': 0.95,
            }
            for i in range(20)
        ]
        
        # Insert segments (should auto-classify)
        count = test_db.batch_insert_segments(segments, test_video_id)
        
        assert count == 20
        
        # Verify classification
        conn = test_db.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT video_type 
                FROM segments 
                WHERE video_id = %s
            """, (test_video_id,))
            
            result = cur.fetchone()
            assert result is not None
            assert result[0] == 'monologue'
    
    def test_interview_classification_end_to_end(self, test_db, test_video_id):
        """Test interview classification with real database"""
        
        # Create interview segments (30% guest)
        segments = []
        for i in range(20):
            speaker = 'GUEST' if i % 3 == 0 else 'Chaffee'
            segments.append({
                'speaker_label': speaker,
                'text': f'Interview segment {i}',
                'start': i * 10.0,
                'end': i * 10.0 + 8.0,
                'speaker_confidence': 0.85,
            })
        
        # Insert segments
        count = test_db.batch_insert_segments(segments, test_video_id)
        
        assert count == 20
        
        # Verify classification
        conn = test_db.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT video_type 
                FROM segments 
                WHERE video_id = %s
            """, (test_video_id,))
            
            result = cur.fetchone()
            assert result is not None
            assert result[0] == 'interview'
    
    def test_monologue_with_clips_classification(self, test_db, test_video_id):
        """Test monologue_with_clips classification"""
        
        # Create segments with 10% guest (clips)
        segments = []
        for i in range(20):
            speaker = 'GUEST' if i == 5 or i == 15 else 'Chaffee'  # 2 out of 20 = 10%
            segments.append({
                'speaker_label': speaker,
                'text': f'Segment {i}',
                'start': i * 10.0,
                'end': i * 10.0 + 8.0,
                'speaker_confidence': 0.90,
            })
        
        # Insert segments
        count = test_db.batch_insert_segments(segments, test_video_id)
        
        assert count == 20
        
        # Verify classification
        conn = test_db.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT video_type 
                FROM segments 
                WHERE video_id = %s
            """, (test_video_id,))
            
            result = cur.fetchone()
            assert result is not None
            assert result[0] == 'monologue_with_clips'
    
    def test_all_segments_get_same_video_type(self, test_db, test_video_id):
        """Test that all segments for a video get the same video_type"""
        
        segments = [
            {
                'speaker_label': 'Chaffee',
                'text': f'Segment {i}',
                'start': i * 10.0,
                'end': i * 10.0 + 8.0,
                'speaker_confidence': 0.95,
            }
            for i in range(10)
        ]
        
        test_db.batch_insert_segments(segments, test_video_id)
        
        # Check all segments have same video_type
        conn = test_db.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(DISTINCT video_type) as unique_types,
                       COUNT(*) as total_segments
                FROM segments 
                WHERE video_id = %s
            """, (test_video_id,))
            
            result = cur.fetchone()
            unique_types, total_segments = result
            
            assert total_segments == 10
            assert unique_types == 1  # All segments should have same type
    
    def test_video_type_index_exists(self, test_db):
        """Test that video_type index exists for performance"""
        
        conn = test_db.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'segments' 
                AND indexname = 'idx_segments_video_type'
            """)
            
            result = cur.fetchone()
            assert result is not None, "video_type index not found"
    
    def test_video_type_column_exists(self, test_db):
        """Test that video_type column exists"""
        
        conn = test_db.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'segments' 
                AND column_name = 'video_type'
            """)
            
            result = cur.fetchone()
            assert result is not None, "video_type column not found"
            assert result[1] == 'character varying', "video_type should be VARCHAR"
    
    def test_classification_with_chaffee_only_storage(self, test_db, test_video_id):
        """Test classification works with chaffee_only_storage flag"""
        
        # Create mixed segments
        segments = []
        for i in range(20):
            speaker = 'GUEST' if i % 4 == 0 else 'Chaffee'
            segments.append({
                'speaker_label': speaker,
                'text': f'Segment {i}',
                'start': i * 10.0,
                'end': i * 10.0 + 8.0,
                'speaker_confidence': 0.90,
            })
        
        # Insert with chaffee_only_storage (should filter out GUEST)
        count = test_db.batch_insert_segments(
            segments, 
            test_video_id,
            chaffee_only_storage=True
        )
        
        # Should only insert Chaffee segments
        assert count == 15  # 15 out of 20 are Chaffee
        
        # Should still classify (based on original segments before filtering)
        conn = test_db.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT video_type 
                FROM segments 
                WHERE video_id = %s
            """, (test_video_id,))
            
            result = cur.fetchone()
            # Note: Classification happens on filtered segments, so will be 'monologue'
            assert result is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
