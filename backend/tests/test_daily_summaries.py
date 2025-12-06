"""
Tests for daily summaries aggregation with request_type and source_app breakdowns.
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from api.daily_summaries import DailyStats, FeedbackSummary


class TestDailyStats:
    """Tests for DailyStats dataclass."""

    def test_to_dict_basic(self):
        """Test basic to_dict without breakdowns."""
        stats = DailyStats(
            summary_date=date(2025, 12, 5),
            total_queries=10,
            total_answers=8,
            total_searches=2,
            distinct_sessions=5,
            total_input_tokens=5000,
            total_output_tokens=3000,
            total_cost_usd=0.05,
            avg_latency_ms=1500.5,
            success_count=9,
            error_count=1,
            top_queries=["test query 1", "test query 2"],
            error_messages=["error 1"],
        )
        
        result = stats.to_dict()
        
        assert result["queries"] == 10
        assert result["answers"] == 8
        assert result["searches"] == 2
        assert result["distinct_sessions"] == 5
        assert result["total_tokens"] == 8000
        assert result["avg_tokens"] == 800
        assert result["total_cost_usd"] == 0.05
        assert result["avg_latency_ms"] == 1500.5
        assert result["success_rate"] == 0.9
        assert result["success_count"] == 9
        assert result["error_count"] == 1
        # Breakdowns should not be present when None
        assert "stats_by_type" not in result
        assert "stats_by_source" not in result

    def test_to_dict_with_stats_by_type(self):
        """Test to_dict includes stats_by_type when present."""
        stats = DailyStats(
            summary_date=date(2025, 12, 5),
            total_queries=10,
            total_answers=8,
            total_searches=2,
            distinct_sessions=5,
            total_input_tokens=5000,
            total_output_tokens=3000,
            total_cost_usd=0.05,
            avg_latency_ms=1500.5,
            success_count=9,
            error_count=1,
            top_queries=[],
            error_messages=[],
            stats_by_type={
                "answer": {
                    "queries": 8,
                    "avg_latency_ms": 2000.0,
                    "avg_tokens": 1000,
                    "success_rate": 0.875,
                },
                "search": {
                    "queries": 2,
                    "avg_latency_ms": 500.0,
                    "avg_tokens": 0,
                    "success_rate": 1.0,
                },
            },
        )
        
        result = stats.to_dict()
        
        assert "stats_by_type" in result
        assert result["stats_by_type"]["answer"]["queries"] == 8
        assert result["stats_by_type"]["answer"]["avg_latency_ms"] == 2000.0
        assert result["stats_by_type"]["search"]["queries"] == 2
        assert result["stats_by_type"]["search"]["success_rate"] == 1.0

    def test_to_dict_with_stats_by_source(self):
        """Test to_dict includes stats_by_source when present."""
        stats = DailyStats(
            summary_date=date(2025, 12, 5),
            total_queries=10,
            total_answers=8,
            total_searches=2,
            distinct_sessions=5,
            total_input_tokens=5000,
            total_output_tokens=3000,
            total_cost_usd=0.05,
            avg_latency_ms=1500.5,
            success_count=9,
            error_count=1,
            top_queries=[],
            error_messages=[],
            stats_by_source={
                "main_app": {
                    "queries": 9,
                    "avg_latency_ms": 1600.0,
                    "avg_tokens": 850,
                    "success_rate": 0.889,
                },
                "tuning_dashboard": {
                    "queries": 1,
                    "avg_latency_ms": 800.0,
                    "avg_tokens": 500,
                    "success_rate": 1.0,
                },
            },
        )
        
        result = stats.to_dict()
        
        assert "stats_by_source" in result
        assert result["stats_by_source"]["main_app"]["queries"] == 9
        assert result["stats_by_source"]["tuning_dashboard"]["queries"] == 1

    def test_to_dict_with_both_breakdowns(self):
        """Test to_dict includes both breakdowns when present."""
        stats = DailyStats(
            summary_date=date(2025, 12, 5),
            total_queries=10,
            total_answers=8,
            total_searches=2,
            distinct_sessions=5,
            total_input_tokens=5000,
            total_output_tokens=3000,
            total_cost_usd=0.05,
            avg_latency_ms=1500.5,
            success_count=10,
            error_count=0,
            top_queries=[],
            error_messages=[],
            stats_by_type={
                "answer": {"queries": 8, "avg_latency_ms": 2000.0, "avg_tokens": 1000, "success_rate": 1.0},
                "search": {"queries": 2, "avg_latency_ms": 500.0, "avg_tokens": 0, "success_rate": 1.0},
            },
            stats_by_source={
                "main_app": {"queries": 10, "avg_latency_ms": 1500.0, "avg_tokens": 800, "success_rate": 1.0},
            },
        )
        
        result = stats.to_dict()
        
        # Top-level stats still correct
        assert result["queries"] == 10
        assert result["success_rate"] == 1.0
        
        # Both breakdowns present
        assert "stats_by_type" in result
        assert "stats_by_source" in result
        assert len(result["stats_by_type"]) == 2
        assert len(result["stats_by_source"]) == 1

    def test_success_rate_calculation(self):
        """Test success_rate property calculation."""
        # All success
        stats = DailyStats(
            summary_date=date(2025, 12, 5),
            total_queries=10, total_answers=10, total_searches=0,
            distinct_sessions=5, total_input_tokens=0, total_output_tokens=0,
            total_cost_usd=0, avg_latency_ms=0,
            success_count=10, error_count=0,
            top_queries=[], error_messages=[],
        )
        assert stats.success_rate == 1.0
        
        # Half success
        stats.success_count = 5
        stats.error_count = 5
        assert stats.success_rate == 0.5
        
        # No requests (edge case)
        stats.success_count = 0
        stats.error_count = 0
        assert stats.success_rate == 1.0  # Default to 1.0 when no data

    def test_backward_compatibility(self):
        """Test that old consumers without breakdown support still work."""
        stats = DailyStats(
            summary_date=date(2025, 12, 5),
            total_queries=5,
            total_answers=5,
            total_searches=0,
            distinct_sessions=3,
            total_input_tokens=2500,
            total_output_tokens=1500,
            total_cost_usd=0.025,
            avg_latency_ms=1200.0,
            success_count=5,
            error_count=0,
            top_queries=["query1"],
            error_messages=[],
            stats_by_type={"answer": {"queries": 5, "avg_latency_ms": 1200.0, "avg_tokens": 800, "success_rate": 1.0}},
            stats_by_source={"main_app": {"queries": 5, "avg_latency_ms": 1200.0, "avg_tokens": 800, "success_rate": 1.0}},
        )
        
        result = stats.to_dict()
        
        # All original fields present
        required_fields = [
            "queries", "answers", "searches", "distinct_sessions",
            "total_tokens", "avg_tokens", "total_cost_usd", "avg_latency_ms",
            "success_rate", "success_count", "error_count"
        ]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
