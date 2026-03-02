#!/usr/bin/env python3
"""Test runner for ARM unit tests.

Usage:
    pytest test/run_test.py -v       # Run via pytest
    python test/run_test.py          # Run directly
"""
import sys
import os

# Ensure the project root is on the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Also add /opt/arm if it exists (production install path)
if os.path.isdir('/opt/arm') and '/opt/arm' not in sys.path:
    sys.path.insert(0, '/opt/arm')


def test_disc_label_tv():
    """Discover and run disc label TV tests (pytest-compatible entry point)."""
    import unittest
    loader = unittest.TestLoader()
    test_dir = os.path.join(project_root, 'test', 'unittest')
    suite = loader.discover(test_dir, pattern='test_disc_label_tv.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    assert result.wasSuccessful(), f"{len(result.failures)} test(s) failed"


def test_group_tv_discs():
    """Discover and run group TV discs tests (pytest-compatible entry point)."""
    import unittest
    loader = unittest.TestLoader()
    test_dir = os.path.join(project_root, 'test', 'unittest')
    suite = loader.discover(test_dir, pattern='test_group_tv_discs.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    assert result.wasSuccessful(), f"{len(result.failures)} test(s) failed"


def test_ripper_utils_file_matching():
    """Discover and run ripper utils file matching tests."""
    import unittest
    loader = unittest.TestLoader()
    test_dir = os.path.join(project_root, 'test', 'unittest')
    suite = loader.discover(test_dir, pattern='test_ripper_utils_file_matching.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    assert result.wasSuccessful(), f"{len(result.failures)} test(s) failed"


if __name__ == '__main__':
    import unittest
    loader = unittest.TestLoader()
    test_dir = os.path.join(project_root, 'test', 'unittest')
    suite = loader.discover(test_dir, pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
