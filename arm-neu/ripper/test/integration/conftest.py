"""Mark all tests in this directory as integration tests.

These require a running ARM instance and are excluded from CI
via ``addopts = -m "not integration"`` in setup.cfg.

Run manually with: ``pytest -m integration test/integration/``
"""
import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
