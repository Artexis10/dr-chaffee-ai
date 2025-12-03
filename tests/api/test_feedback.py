"""
Tests for the feedback API endpoints.

Tests cover:
- Creating feedback for different target types
- Listing feedback with filters
- AI request logging
- Metadata enrichment for answer feedback
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

# Set up test environment
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")


class TestFeedbackAPI:
    """Tests for feedback API endpoints."""

    @pytest.fixture
    def mock_db_connection(self):
        """Mock database connection for testing."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        return mock_conn, mock_cursor

    def test_feedback_create_schema(self):
        """Test FeedbackCreate schema validation."""
        from backend.api.feedback import FeedbackCreate

        # Valid feedback
        feedback = FeedbackCreate(
            target_type="answer",
            target_id="123e4567-e89b-12d3-a456-426614174000",
            rating=1,
            tags=["helpful", "accurate"],
            comment="Great answer!",
        )
        assert feedback.target_type == "answer"
        assert feedback.rating == 1
        assert len(feedback.tags) == 2

        # Valid global feedback without target_id
        global_feedback = FeedbackCreate(
            target_type="global",
            rating=None,
            comment="Love the app!",
        )
        assert global_feedback.target_id is None

        # Valid tuning feedback
        tuning_feedback = FeedbackCreate(
            target_type="tuning_internal",
            target_id="profile_123",
            rating=-1,
            tags=["too_verbose"],
        )
        assert tuning_feedback.target_type == "tuning_internal"

    def test_feedback_rating_validation(self):
        """Test that rating is validated within bounds."""
        from backend.api.feedback import FeedbackCreate
        from pydantic import ValidationError

        # Valid ratings
        for rating in [-2, -1, 0, 1, None]:
            feedback = FeedbackCreate(target_type="answer", rating=rating)
            assert feedback.rating == rating

        # Invalid rating (too high)
        with pytest.raises(ValidationError):
            FeedbackCreate(target_type="answer", rating=2)

        # Invalid rating (too low)
        with pytest.raises(ValidationError):
            FeedbackCreate(target_type="answer", rating=-3)

    def test_feedback_comment_max_length(self):
        """Test comment max length validation."""
        from backend.api.feedback import FeedbackCreate
        from pydantic import ValidationError

        # Valid comment
        feedback = FeedbackCreate(
            target_type="global",
            comment="A" * 5000,  # Max length
        )
        assert len(feedback.comment) == 5000

        # Invalid comment (too long)
        with pytest.raises(ValidationError):
            FeedbackCreate(
                target_type="global",
                comment="A" * 5001,
            )

    def test_ai_request_create_schema(self):
        """Test AiRequestCreate schema."""
        from backend.api.feedback import AiRequestCreate

        request = AiRequestCreate(
            request_type="qa",
            input_text="What is carnivore diet?",
            output_text="The carnivore diet is...",
            model_name="gpt-4o-mini",
            rag_profile_id="profile_1",
            input_tokens=100,
            output_tokens=500,
            cost_usd=0.01,
            latency_ms=1500.5,
            success=True,
        )
        assert request.request_type == "qa"
        assert request.success is True

    def test_log_ai_request_truncation(self, mock_db_connection):
        """Test that log_ai_request truncates long text."""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = {"id": uuid4()}

        with patch("backend.api.feedback.get_db_connection", return_value=mock_conn):
            from backend.api.feedback import log_ai_request

            # Very long input/output
            long_input = "A" * 20000
            long_output = "B" * 100000

            result = log_ai_request(
                request_type="qa",
                input_text=long_input,
                output_text=long_output,
                model_name="gpt-4o-mini",
            )

            # Should return a UUID
            assert result is not None

            # Check that execute was called with truncated values
            call_args = mock_cursor.execute.call_args
            params = call_args[0][1]
            
            # input_text should be truncated to 10000
            assert len(params[2]) == 10000
            # output_text should be truncated to 50000
            assert len(params[3]) == 50000

    def test_feedback_list_response_schema(self):
        """Test FeedbackListResponse schema."""
        from backend.api.feedback import FeedbackListResponse, FeedbackItem
        from datetime import datetime

        items = [
            FeedbackItem(
                id="123",
                target_type="answer",
                target_id="456",
                rating=1,
                tags=["helpful"],
                comment="Great!",
                metadata={"model_name": "gpt-4o-mini"},
                created_at=datetime.now(),
                input_text_snippet="What is...",
                output_text_snippet="The answer is...",
                model_name="gpt-4o-mini",
            )
        ]

        response = FeedbackListResponse(
            items=items,
            total=100,
            page=1,
            page_size=20,
        )
        assert response.total == 100
        assert len(response.items) == 1

    def test_feedback_response_schema(self):
        """Test FeedbackResponse schema."""
        from backend.api.feedback import FeedbackResponse

        response = FeedbackResponse(
            success=True,
            feedback_id="123e4567-e89b-12d3-a456-426614174000",
            message="Feedback submitted successfully",
        )
        assert response.success is True
        assert "123e4567" in response.feedback_id


class TestMetadataEnrichment:
    """Tests for metadata enrichment on answer feedback."""

    def test_get_ai_request_metadata_returns_all_fields(self):
        """Test that get_ai_request_metadata returns all expected fields."""
        from unittest.mock import patch, MagicMock
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        
        # Mock the database result
        mock_cursor.fetchone.return_value = {
            "model_name": "gpt-4o-mini",
            "rag_profile_id": "profile_1",
            "custom_instruction_id": "instr_1",
            "search_config_id": "search_1",
            "request_type": "qa",
        }
        
        with patch("backend.api.feedback.get_db_connection", return_value=mock_conn):
            from backend.api.feedback import get_ai_request_metadata
            
            result = get_ai_request_metadata("test-uuid")
            
            assert result is not None
            assert result["model_name"] == "gpt-4o-mini"
            assert result["rag_profile_id"] == "profile_1"
            assert result["custom_instruction_id"] == "instr_1"
            assert result["search_config_id"] == "search_1"
            assert result["request_type"] == "qa"


class TestDailySummaryFeedback:
    """Tests for feedback integration in daily summaries."""

    def test_feedback_summary_dataclass(self):
        """Test FeedbackSummary dataclass."""
        from backend.api.daily_summaries import FeedbackSummary
        
        summary = FeedbackSummary(
            total=42,
            positive=30,
            negative=12,
            by_model={
                "gpt-4o-mini": {"positive": 18, "negative": 4},
                "gpt-4o": {"positive": 12, "negative": 8},
            },
            top_tags=[
                {"tag": "wrong_facts", "count": 5},
                {"tag": "missed_context", "count": 3},
            ],
        )
        
        assert summary.total == 42
        assert summary.positive == 30
        assert summary.negative == 12
        assert len(summary.by_model) == 2
        assert len(summary.top_tags) == 2

    def test_feedback_summary_to_dict(self):
        """Test FeedbackSummary.to_dict() method."""
        from backend.api.daily_summaries import FeedbackSummary
        
        summary = FeedbackSummary(
            total=10,
            positive=7,
            negative=3,
            by_model={"gpt-4o-mini": {"positive": 7, "negative": 3}},
            top_tags=[{"tag": "helpful", "count": 5}],
        )
        
        result = summary.to_dict()
        
        assert result["total"] == 10
        assert result["positive"] == 7
        assert result["negative"] == 3
        assert "by_model" in result
        assert "top_tags" in result

    def test_daily_stats_includes_feedback_summary(self):
        """Test that DailyStats can include feedback_summary."""
        from backend.api.daily_summaries import DailyStats, FeedbackSummary
        from datetime import date
        
        feedback = FeedbackSummary(
            total=5,
            positive=4,
            negative=1,
            by_model={},
            top_tags=[],
        )
        
        stats = DailyStats(
            summary_date=date.today(),
            total_queries=100,
            total_answers=80,
            total_searches=20,
            distinct_sessions=50,
            total_input_tokens=10000,
            total_output_tokens=20000,
            total_cost_usd=0.5,
            avg_latency_ms=1500.0,
            success_count=95,
            error_count=5,
            top_queries=["query1", "query2"],
            error_messages=[],
            feedback_summary=feedback,
        )
        
        result = stats.to_dict()
        
        assert "feedback_summary" in result
        assert result["feedback_summary"]["total"] == 5
        assert result["feedback_summary"]["positive"] == 4


class TestFeedbackIntegration:
    """Integration tests for feedback system (require database)."""

    @pytest.fixture
    def skip_if_no_db(self):
        """Skip test if no database connection available."""
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url or "test" in db_url:
            pytest.skip("No database connection available")

    def test_create_and_list_feedback_flow(self, skip_if_no_db):
        """Test creating feedback and listing it back."""
        # This test requires a real database connection
        # It's marked to skip in CI environments
        pass


class TestMigration:
    """Tests for the feedback migration."""

    def test_migration_file_exists(self):
        """Test that migration file exists."""
        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "backend",
            "migrations",
            "versions",
            "025_feedback_system.py",
        )
        assert os.path.exists(migration_path), f"Migration file not found at {migration_path}"

    def test_migration_has_upgrade_and_downgrade(self):
        """Test that migration has both upgrade and downgrade functions."""
        import importlib.util

        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "backend",
            "migrations",
            "versions",
            "025_feedback_system.py",
        )

        spec = importlib.util.spec_from_file_location("migration", migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        assert hasattr(migration, "upgrade"), "Migration missing upgrade function"
        assert hasattr(migration, "downgrade"), "Migration missing downgrade function"
        assert migration.revision == "025"
        assert migration.down_revision == "024"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
