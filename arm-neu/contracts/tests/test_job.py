"""Tests for Job, JobSummary, Track, TrackCounts, JobProgressState contracts."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from arm_contracts import (
    Job,
    JobProgressState,
    JobSummary,
    Track,
    TrackCounts,
    TranscodeJobConfig,
)


# --- TrackCounts ---


def test_track_counts_defaults_to_zero():
    tc = TrackCounts()
    assert tc.total == 0
    assert tc.ripped == 0


def test_track_counts_round_trip():
    tc = TrackCounts(total=5, ripped=2)
    assert TrackCounts.model_validate(tc.model_dump()) == tc


def test_track_counts_ignores_extras():
    """extra='ignore' so producer can add fields without breaking older consumers."""
    tc = TrackCounts.model_validate({"total": 3, "ripped": 1, "_unknown": "x"})
    assert tc.total == 3
    assert tc.ripped == 1


# --- Track ---


def test_track_minimum_valid():
    t = Track(track_id=1, job_id=42)
    assert t.track_id == 1
    assert t.enabled is None  # producer-folded; None means "not stored yet"


def test_track_round_trip_full():
    src = {
        "track_id": 7,
        "job_id": 42,
        "track_number": "01",
        "length": 5400,
        "aspect_ratio": "16:9",
        "fps": 23.976,
        "enabled": True,
        "basename": "title_t01",
        "filename": "Episode 1.mkv",
        "orig_filename": "title_t01.mkv",
        "new_filename": "Episode 1.mkv",
        "ripped": True,
        "status": "success",
        "error": None,
        "source": "MakeMKV",
        "title": "Episode 1",
        "year": "2024",
        "imdb_id": "tt1234567",
        "poster_url": "https://example.com/p.jpg",
        "video_type": "series",
        "episode_number": "01",
        "episode_name": "Pilot",
        "custom_filename": "S01E01_pilot.mkv",
    }
    t = Track.model_validate(src)
    assert t.custom_filename == "S01E01_pilot.mkv"
    assert t.episode_name == "Pilot"
    # Round trip preserves every field.
    dumped = t.model_dump()
    for key, value in src.items():
        assert dumped[key] == value


def test_track_main_feature_is_not_on_the_wire():
    """main_feature is folded into `enabled` producer-side; the contract
    intentionally omits it so consumers can't accidentally read stale data."""
    with pytest.raises(ValidationError, match="track_id"):
        Track()  # track_id is required
    # main_feature is silently dropped via extra="ignore"
    t = Track.model_validate({"track_id": 1, "job_id": 1, "main_feature": True})
    assert not hasattr(t, "main_feature")


# --- Job ---


def test_job_minimum_valid():
    """job_id is the only required field; everything else is nullable so a
    just-created Job (no metadata yet) round-trips cleanly."""
    j = Job(job_id=99)
    assert j.job_id == 99
    assert j.title is None
    assert j.transcode_overrides is None


def test_job_round_trip_with_datetimes():
    """ISO datetime strings on the wire (mode='json' on the producer) parse
    back into Job.start_time / stop_time as datetime objects."""
    src = {
        "job_id": 1,
        "title": "The Matrix",
        "year": "1999",
        "video_type": "movie",
        "status": "success",
        "stage": "",
        "start_time": "2026-04-29T01:23:45+00:00",
        "stop_time": "2026-04-29T02:34:56+00:00",
        "disctype": "bluray",
    }
    j = Job.model_validate(src)
    assert j.start_time == datetime(2026, 4, 29, 1, 23, 45, tzinfo=timezone.utc)
    # mode='json' dump emits ISO strings again. Pydantic v2 normalises +00:00
    # to the shorter `Z` suffix; both are valid ISO 8601 and parse back the
    # same way, so the contract accepts either form on the way in.
    dumped = j.model_dump(mode="json")
    assert dumped["start_time"] == "2026-04-29T01:23:45Z"
    assert Job.model_validate(dumped).start_time == j.start_time


def test_job_carries_pattern_overrides():
    """Audit gap fix: title_pattern_override and folder_pattern_override
    were on the wire from arm-neu but stripped by arm-ui's old JobSchema.
    They MUST be on the contract so the frontend gets them."""
    j = Job(
        job_id=5,
        title_pattern_override="{title} ({year}) [{disctype}]",
        folder_pattern_override="{video_type}/{title}",
    )
    assert j.title_pattern_override.startswith("{title}")
    assert j.folder_pattern_override == "{video_type}/{title}"
    dumped = j.model_dump()
    assert dumped["title_pattern_override"] == "{title} ({year}) [{disctype}]"


def test_job_transcode_overrides_accepts_typed_dict():
    """The contract types transcode_overrides as a plain dict; the consumer
    (arm-ui) attaches its own field validator to gate against
    TranscodeJobConfig and strip legacy keys. Verify the dict round-trips
    untouched at the contract level."""
    overrides = {"preset_slug": "software-balanced", "overrides": {"shared": {}}}
    j = Job(job_id=1, transcode_overrides=overrides)
    assert j.transcode_overrides == overrides
    # Sanity check: the dict matches a real TranscodeJobConfig shape.
    assert TranscodeJobConfig.model_validate(overrides).preset_slug == "software-balanced"


def test_job_carries_track_counts_when_present():
    """track_counts is None on /jobs/paginated rows, populated on /jobs/active
    and /jobs/{id}/detail."""
    j = Job(job_id=1, track_counts=TrackCounts(total=5, ripped=2))
    assert j.track_counts is not None
    assert j.track_counts.ripped == 2
    j2 = Job(job_id=1)
    assert j2.track_counts is None


def test_job_extra_keys_silently_ignored():
    """A producer that adds a column doesn't break older consumers."""
    j = Job.model_validate({"job_id": 1, "_brand_new_field": "hello"})
    assert j.job_id == 1
    assert not hasattr(j, "_brand_new_field")


# --- JobSummary ---


def test_job_summary_round_trip():
    src = {
        "job_id": 42,
        "title": "Inception",
        "year": "2010",
        "video_type": "movie",
        "status": "transcoding",
        "stage": "video_transcoding",
        "disctype": "bluray",
        "label": "INCEPTION_BD",
        "poster_url": "https://example.com/p.jpg",
        "no_of_titles": 3,
    }
    s = JobSummary.model_validate(src)
    assert s.job_id == 42
    assert s.no_of_titles == 3
    dumped = s.model_dump()
    assert dumped == src


def test_job_summary_strips_extra_columns():
    """JobSummary is intentionally narrower than Job; passing a full Job dict
    drops the extras silently rather than failing."""
    s = JobSummary.model_validate({
        "job_id": 1,
        "title": "X",
        "logfile": "/path/to.log",  # not in JobSummary
        "transcode_overrides": {"preset_slug": "x"},  # also not here
    })
    assert s.title == "X"
    assert not hasattr(s, "logfile")
    assert not hasattr(s, "transcode_overrides")


# --- JobProgressState ---


def test_progress_state_requires_track_counts():
    """track_counts is the one non-optional sub-model; the rest are sentinel
    values for 'not yet started'."""
    with pytest.raises(ValidationError, match="track_counts"):
        JobProgressState()
    p = JobProgressState(track_counts=TrackCounts(total=3, ripped=1))
    assert p.rip_progress is None
    assert p.music_stage is None


def test_progress_state_round_trip():
    src = {
        "track_counts": {"total": 3, "ripped": 1},
        "disctype": "bluray",
        "logfile": "JOB_5_Rip.log",
        "no_of_titles": 3,
        "rip_progress": 67,
        "rip_stage": "Saving to MKV file",
        "tracks_ripped_realtime": 1,
        "music_progress": None,
        "music_stage": None,
    }
    p = JobProgressState.model_validate(src)
    assert p.track_counts.total == 3
    assert p.tracks_ripped_realtime == 1
    dumped = p.model_dump()
    for key, value in src.items():
        if key == "track_counts":
            assert dumped[key] == value
        else:
            assert dumped[key] == value


def test_progress_state_accepts_fractional_percentages():
    """rip_progress and music_progress are percentages rounded to 1 decimal
    place by the parser, so the contract must accept floats - regression
    against a hotfix where typing them as int caused 500s on every
    progress-state poll once a non-zero fractional value flowed through.
    """
    p = JobProgressState(
        track_counts=TrackCounts(total=3, ripped=0),
        rip_progress=6.4,
        music_progress=42.7,
    )
    assert p.rip_progress == 6.4
    assert p.music_progress == 42.7
