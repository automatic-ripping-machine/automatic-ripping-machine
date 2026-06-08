"""Tests for Job.media_metadata storage + merged-read property."""
from datetime import date

import pytest

from arm.database import db
from arm.models.job import Job
from arm_contracts import MediaMetadata
from arm_contracts.enums import VideoType


@pytest.fixture
def fresh_job(app_context):
    """A fresh Job with no metadata."""
    job = Job(devpath="/dev/sr0", _skip_hardware=True)
    db.session.add(job)
    db.session.commit()
    return job


def test_media_metadata_returns_empty_when_unset(fresh_job):
    """A Job with neither column populated returns an empty MediaMetadata."""
    m = fresh_job.media_metadata
    assert isinstance(m, MediaMetadata)
    assert m.title is None
    assert m.genres == []


def test_writes_to_auto_column(fresh_job):
    """Adapter writes go to media_metadata_auto."""
    fresh_job.set_metadata_auto(MediaMetadata(
        title="Auto Title",
        year="2024",
        directors=["Auto Director"],
    ))
    db.session.commit()

    db.session.expire_all()
    reloaded = Job.query.get(fresh_job.job_id)
    assert reloaded.media_metadata.title == "Auto Title"
    assert reloaded.media_metadata.directors == ["Auto Director"]


def test_manual_overrides_auto_field_by_field(fresh_job):
    """Manual overrides win field-by-field; unset manual fields fall through to auto."""
    fresh_job.set_metadata_auto(MediaMetadata(
        title="Auto Title",
        year="2024",
        directors=["Auto Director"],
        plot="Auto plot.",
    ))
    fresh_job.set_metadata_manual(MediaMetadata(
        title="Manual Title",  # overrides auto
        # year unset -> falls through to auto
        directors=[],          # empty list = unset -> falls through
        plot="",               # empty string treated as set if non-None? See below.
    ))
    db.session.commit()

    merged = fresh_job.media_metadata
    assert merged.title == "Manual Title"           # manual wins
    assert merged.year == "2024"                    # auto fills
    assert merged.directors == ["Auto Director"]    # empty manual list = unset


def test_set_metadata_manual_partial_payload(fresh_job):
    """UI overrides typically set one or two fields, not the full model."""
    fresh_job.set_metadata_auto(MediaMetadata(title="Auto", year="2024"))
    fresh_job.set_metadata_manual(MediaMetadata(year="2025"))  # only year
    db.session.commit()

    merged = fresh_job.media_metadata
    assert merged.title == "Auto"   # untouched manual field falls through
    assert merged.year == "2025"    # manual overrides
