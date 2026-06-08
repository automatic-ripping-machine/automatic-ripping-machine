"""Track contract: process and skip_reason fields."""

import pytest
from pydantic import ValidationError

from arm_contracts import Track


def test_track_default_process_true():
    t = Track(track_id=1, job_id=1)
    assert t.process is True
    assert t.skip_reason is None


def test_track_skip_reason_too_short():
    t = Track(track_id=1, job_id=1, process=False, skip_reason="too_short")
    assert t.process is False
    assert t.skip_reason == "too_short"


def test_track_skip_reason_makemkv_skipped():
    t = Track(track_id=1, job_id=1, process=False, skip_reason="makemkv_skipped")
    assert t.process is False
    assert t.skip_reason == "makemkv_skipped"


def test_track_explicit_process_true_accepted():
    t = Track(track_id=1, job_id=1, process=True)
    assert t.process is True


def test_track_process_none_rejected():
    """`process` is a non-Optional bool; None must not coerce to False."""
    with pytest.raises(ValidationError):
        Track(track_id=1, job_id=1, process=None)


def test_track_invalid_skip_reason_rejected():
    with pytest.raises(ValidationError):
        Track(track_id=1, job_id=1, skip_reason="bogus_reason")


def test_skip_reason_type_alias_exported():
    """SkipReason is exported for consumers to type-annotate their own fields."""
    from arm_contracts import SkipReason  # noqa: F401
