"""The label dupe check never lends another disc its identity."""

from types import SimpleNamespace

import pytest


def previous_rip(**values):
    row = {"title": "Foo", "year": "2001", "poster_url": None, "hasnicetitle": True,
           "video_type": "movie", "crc_id": "aaaa", **values}
    return SimpleNamespace(crc_id=row["crc_id"], get_d=lambda: {k: str(v) for k, v in row.items()})


@pytest.fixture
def dupe_check(monkeypatch):
    from arm.ripper import utils

    updates = []
    rows = []
    monkeypatch.setattr(utils, "Job", SimpleNamespace(query=SimpleNamespace(filter_by=lambda **k: rows)))
    monkeypatch.setattr(utils, "database_updater", lambda values, j: updates.append(values))
    return utils, rows, updates


def test_same_generic_label_with_a_different_fingerprint_is_not_a_dupe(dupe_check):
    utils, rows, updates = dupe_check
    rows.append(previous_rip(crc_id="aaaa"))
    job = SimpleNamespace(label="DVD_VIDEO", crc_id="bbbb")
    assert utils.job_dupe_check(job) is False
    assert updates == []


def test_same_disc_is_still_a_dupe_without_literal_none_values(dupe_check):
    utils, rows, updates = dupe_check
    rows.append(previous_rip(crc_id="aaaa", year=None, video_type=None))
    job = SimpleNamespace(label="DVD_VIDEO", crc_id="aaaa")
    assert utils.job_dupe_check(job) is True
    assert updates == [{"title": "Foo", "year": "", "poster_url": None, "hasnicetitle": True,
                        "video_type": "unknown"}]


def test_an_earlier_rip_without_a_fingerprint_is_not_this_disc(dupe_check):
    utils, rows, updates = dupe_check
    rows.append(previous_rip(crc_id=None, title="not identified"))
    job = SimpleNamespace(label="not identified", crc_id="ade5cef9590c59d1")
    assert utils.job_dupe_check(job) is False
    assert updates == []
