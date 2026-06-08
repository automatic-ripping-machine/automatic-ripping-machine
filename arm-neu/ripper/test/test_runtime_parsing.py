"""Tests for runtime string parsing across metadata provider formats."""

import pytest

from arm.services.runtime_parsing import parse_runtime


@pytest.mark.parametrize("raw,expected", [
    ("95 min", 5700),
    ("142 min", 8520),
    ("1 min", 60),
    ("2 h 31 min", 9060),
    ("1 h 0 min", 3600),
    ("0 h 47 min", 2820),
    (95, 5700),  # integer minutes (TMDb shape)
    (142, 8520),
])
def test_parse_runtime_valid(raw, expected):
    assert parse_runtime(raw) == expected


@pytest.mark.parametrize("raw", [
    "N/A",
    "",
    None,
    "unknown",
    "abc",
    0,
    -5,
    "0 min",
])
def test_parse_runtime_invalid_returns_none(raw):
    assert parse_runtime(raw) is None


def test_parse_runtime_rejects_bool():
    """bool is a subclass of int in Python; True/False are not valid runtimes."""
    assert parse_runtime(True) is None
    assert parse_runtime(False) is None
