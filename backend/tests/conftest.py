#!/usr/bin/env python3
"""
Pytest configuration for ingestion tests
"""
import pytest


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require network)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (may take minutes)"
    )


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (require network)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --run-integration is passed"""
    if config.getoption("--run-integration"):
        return
    
    skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
