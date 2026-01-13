"""Pytest configuration for e2e tests."""

import pytest


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
