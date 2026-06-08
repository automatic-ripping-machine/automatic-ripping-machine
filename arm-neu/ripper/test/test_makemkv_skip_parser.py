"""Tests for parsing MakeMKV stdout 'title skipped' messages.

In all-tracks rip mode, MakeMKV's binary does the MIN filtering itself
and emits 'Title #X has length of Y seconds which is less than minimum
title length of N seconds and was therefore skipped' messages. We parse
these and persist skip_reason='makemkv_skipped' on the corresponding
track records so the UI shows backend truth.
"""
from pathlib import Path

from arm.ripper.makemkv import parse_makemkv_skip_message

_FIXTURE = Path(__file__).parent / "fixtures" / "makemkv_stdout" / "movie_dvd_5_skipped.txt"


def test_parse_skip_message_extracts_title_number():
    line = "Title #2 has length of 21 seconds which is less than minimum title length of 600 seconds and was therefore skipped"
    result = parse_makemkv_skip_message(line)
    assert result == {"track_number": "2", "length": 21, "min_length": 600}


def test_parse_skip_message_returns_none_for_non_skip_line():
    assert parse_makemkv_skip_message("Operation successfully completed") is None
    assert parse_makemkv_skip_message("Title #1 was added (6 cell(s), 1:16:08)") is None


def test_parse_skip_message_strips_makemkv_log_prefix():
    """ARM's logger sometimes re-emits MakeMKV stdout with a 'MakeMKV: ' prefix."""
    line = "MakeMKV: Title #7 has length of 42 seconds which is less than minimum title length of 600 seconds and was therefore skipped"
    result = parse_makemkv_skip_message(line)
    assert result == {"track_number": "7", "length": 42, "min_length": 600}


def test_real_log_extracts_5_skip_records():
    text = _FIXTURE.read_text()
    skips = [
        parsed
        for line in text.splitlines()
        if (parsed := parse_makemkv_skip_message(line)) is not None
    ]
    assert len(skips) == 5
    assert {s["track_number"] for s in skips} == {"2", "3", "4", "5", "6"}
    assert sorted(s["length"] for s in skips) == [21, 50, 60, 188, 249]


def test_apply_skip_to_track_records(app_context, sample_job):
    """Calling apply_makemkv_skips with a list of skip dicts updates the
    matching track records: process=False, skip_reason='makemkv_skipped'."""
    from arm.database import db
    from arm.models.track import Track
    from arm.ripper.makemkv import apply_makemkv_skips

    for n, length in [("1", 4568), ("2", 21), ("3", 249)]:
        db.session.add(Track(
            job_id=sample_job.job_id, track_number=n, length=length,
            aspect_ratio="4:3", fps=29.97, main_feature=False,
            source="MakeMKV", basename=f"t{n}", filename=f"t{n}.mkv",
        ))
    db.session.commit()

    skips = [
        {"track_number": "2", "length": 21, "min_length": 600},
        {"track_number": "3", "length": 249, "min_length": 600},
    ]
    apply_makemkv_skips(sample_job, skips)

    rows = {t.track_number: t for t in db.session.query(Track).filter_by(job_id=sample_job.job_id)}
    assert rows["1"].skip_reason is None
    assert rows["2"].skip_reason == "makemkv_skipped"
    assert rows["2"].process is False
    assert rows["3"].skip_reason == "makemkv_skipped"
