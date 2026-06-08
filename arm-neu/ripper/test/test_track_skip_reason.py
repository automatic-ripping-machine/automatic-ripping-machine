"""Tests for the new skip_reason column on Track."""

import pytest
from arm.database import db


@pytest.fixture
def client(app_context):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from arm.api.v1.jobs import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


def test_track_skip_reason_default_null(app_context, sample_job):
    from arm.models.track import Track

    t = Track(
        job_id=sample_job.job_id,
        track_number="0",
        length=5712,
        aspect_ratio="16:9",
        fps=23.976,
        main_feature=True,
        source="MakeMKV",
        basename="title_00",
        filename="title_00.mkv",
    )
    db.session.add(t)
    db.session.commit()
    assert t.skip_reason is None


def test_track_skip_reason_set_to_too_short(app_context, sample_job):
    from arm.models.track import Track

    t = Track(
        job_id=sample_job.job_id, track_number="1", length=33,
        aspect_ratio="16:9", fps=23.976, main_feature=False,
        source="MakeMKV", basename="title_01", filename="title_01.mkv",
    )
    t.skip_reason = "too_short"
    t.process = False
    db.session.add(t)
    db.session.commit()

    rows = db.session.query(Track).filter_by(skip_reason="too_short").all()
    assert len(rows) == 1


def test_process_single_tracks_sets_too_short(app_context, sample_job, tmp_path):
    """When a track is below MINLENGTH, process_single_tracks sets
    process=False and skip_reason='too_short'."""
    from unittest.mock import patch
    from arm.models.track import Track
    from arm.ripper import makemkv

    sample_job.config.MINLENGTH = "600"
    sample_job.config.MAXLENGTH = "5000"
    sample_job.config.MKV_ARGS = ""

    short = Track(
        job_id=sample_job.job_id, track_number="0", length=33,
        aspect_ratio="16:9", fps=23.976, main_feature=False,
        source="MakeMKV", basename="t0", filename="t0.mkv",
    )
    db.session.add(short)
    db.session.commit()
    db.session.refresh(sample_job)

    with patch.object(makemkv, "run", return_value=iter([])):
        makemkv.process_single_tracks(sample_job, str(tmp_path), "auto")

    db.session.refresh(short)
    assert short.process is False
    assert short.skip_reason == "too_short"


def test_process_single_tracks_sets_too_long(app_context, sample_job, tmp_path):
    from unittest.mock import patch
    from arm.models.track import Track
    from arm.ripper import makemkv

    sample_job.config.MINLENGTH = "600"
    sample_job.config.MAXLENGTH = "5000"
    sample_job.config.MKV_ARGS = ""

    long_track = Track(
        job_id=sample_job.job_id, track_number="0", length=12345,
        aspect_ratio="16:9", fps=23.976, main_feature=False,
        source="MakeMKV", basename="t0", filename="t0.mkv",
    )
    db.session.add(long_track)
    db.session.commit()
    db.session.refresh(sample_job)

    with patch.object(makemkv, "run", return_value=iter([])):
        makemkv.process_single_tracks(sample_job, str(tmp_path), "auto")

    db.session.refresh(long_track)
    assert long_track.process is False
    assert long_track.skip_reason == "too_long"


def test_all_tracks_path_marks_long_tracks_as_process_true(app_context, sample_job, tmp_path):
    """The all-tracks rip path (mkv-all branch) must set process=True on
    tracks that survive MakeMKV's --minlength filter, so the UI doesn't
    mislabel actively-ripping tracks as 'Skipped' mid-rip."""
    import unittest.mock
    from arm.models.track import Track
    from arm.models.system_drives import SystemDrives
    from arm.ripper import makemkv as mkv_mod

    drive = SystemDrives()
    drive.mount = sample_job.devpath
    drive.job_id_current = sample_job.job_id
    drive.mdisc = 0
    db.session.add(drive)

    sample_job.config.MINLENGTH = "600"
    sample_job.config.MAXLENGTH = "99999"
    sample_job.config.MKV_ARGS = ""
    sample_job.no_of_titles = 3
    db.session.commit()

    long_track = Track(sample_job.job_id, "0", 4568, "4:3", 29.97, False,
                       "MakeMKV", "t0", "t0.mkv")
    short1 = Track(sample_job.job_id, "1", 21, "4:3", 29.97, False,
                   "MakeMKV", "t1", "t1.mkv")
    short2 = Track(sample_job.job_id, "2", 60, "4:3", 29.97, False,
                   "MakeMKV", "t2", "t2.mkv")
    db.session.add_all([long_track, short1, short2])
    db.session.commit()

    skip_msg_1 = unittest.mock.MagicMock()
    skip_msg_1.message = ("Title #1 has length of 21 seconds which is less "
                          "than minimum title length of 600 seconds and was "
                          "therefore skipped")
    skip_msg_2 = unittest.mock.MagicMock()
    skip_msg_2.message = ("Title #2 has length of 60 seconds which is less "
                          "than minimum title length of 600 seconds and was "
                          "therefore skipped")
    del skip_msg_1.code
    del skip_msg_2.code

    with unittest.mock.patch.object(mkv_mod.utils, "get_drive_mode", return_value="auto"), \
         unittest.mock.patch.object(mkv_mod, "get_track_info"), \
         unittest.mock.patch.object(mkv_mod, "_mark_ripped_from_disk"), \
         unittest.mock.patch.object(mkv_mod, "run", return_value=iter([skip_msg_1, skip_msg_2])):
        mkv_mod.makemkv_mkv(sample_job, str(tmp_path))

    db.session.refresh(long_track)
    db.session.refresh(short1)
    db.session.refresh(short2)
    assert long_track.process is True
    assert long_track.skip_reason is None
    assert short1.process is False
    assert short1.skip_reason == "makemkv_skipped"
    assert short2.process is False
    assert short2.skip_reason == "makemkv_skipped"


def test_folder_prescan_auto_disable_sets_too_short(app_context, sample_job):
    """The folder-import prescan auto-disable should set process=False,
    enabled=False AND skip_reason='too_short' on tracks below MINLENGTH.

    process=False is the rip-time gate honored by kick_off_import_rip's
    deselection filter; without it short tracks were ripped despite the
    auto-filter (observed during 17.6.0-rc ISO smoke on hifi).
    """
    from arm.models.track import Track
    from arm.api.v1.folder import auto_disable_short_tracks

    for n, length in [("0", 4568), ("1", 33), ("2", 22)]:
        db.session.add(Track(
            job_id=sample_job.job_id, track_number=n, length=length,
            aspect_ratio="16:9", fps=23.976, main_feature=False,
            source="MakeMKV", basename=f"t{n}", filename=f"t{n}.mkv",
        ))
    db.session.commit()

    auto_disable_short_tracks(sample_job, minlength=600)

    rows = {t.track_number: t for t in db.session.query(Track).filter_by(job_id=sample_job.job_id)}
    assert rows["0"].enabled is True
    assert rows["0"].skip_reason is None
    # process is left at its default (None or True) for the kept track
    assert rows["1"].enabled is False
    assert rows["1"].process is False
    assert rows["1"].skip_reason == "too_short"
    assert rows["2"].enabled is False
    assert rows["2"].process is False
    assert rows["2"].skip_reason == "too_short"


def test_manual_disable_sets_user_disabled(client, app_context, sample_job):
    from arm.models.track import Track

    t = Track(
        job_id=sample_job.job_id, track_number="0", length=4568,
        aspect_ratio="4:3", fps=29.97, main_feature=False,
        source="MakeMKV", basename="t0", filename="t0.mkv",
    )
    db.session.add(t)
    db.session.commit()

    response = client.patch(
        f"/api/v1/jobs/{sample_job.job_id}/tracks/{t.track_id}",
        json={"enabled": False},
    )
    assert response.status_code == 200
    db.session.refresh(t)
    assert t.enabled is False
    assert t.skip_reason == "user_disabled"


def test_manual_re_enable_clears_skip_reason(client, app_context, sample_job):
    from arm.models.track import Track

    t = Track(
        job_id=sample_job.job_id, track_number="0", length=4568,
        aspect_ratio="4:3", fps=29.97, main_feature=False,
        source="MakeMKV", basename="t0", filename="t0.mkv",
    )
    t.enabled = False
    t.skip_reason = "user_disabled"
    db.session.add(t)
    db.session.commit()

    response = client.patch(
        f"/api/v1/jobs/{sample_job.job_id}/tracks/{t.track_id}",
        json={"enabled": True},
    )
    assert response.status_code == 200
    db.session.refresh(t)
    assert t.enabled is True
    assert t.skip_reason is None


def test_manual_patch_without_enabled_leaves_skip_reason_alone(client, app_context, sample_job):
    """A PATCH that does not include 'enabled' must not touch skip_reason."""
    from arm.models.track import Track

    t = Track(
        job_id=sample_job.job_id, track_number="0", length=4568,
        aspect_ratio="4:3", fps=29.97, main_feature=False,
        source="MakeMKV", basename="t0", filename="t0.mkv",
    )
    t.skip_reason = "makemkv_skipped"
    db.session.add(t)
    db.session.commit()

    response = client.patch(
        f"/api/v1/jobs/{sample_job.job_id}/tracks/{t.track_id}",
        json={"filename": "renamed.mkv"},
    )
    assert response.status_code == 200
    db.session.refresh(t)
    assert t.filename == "renamed.mkv"
    assert t.skip_reason == "makemkv_skipped"


def test_mark_prescan_filter_state_skips_short_tracks(app_context, sample_job):
    """mark_prescan_filter_state stamps process=False + skip_reason=too_short
    on tracks below the configured MINLENGTH so the disc-review widget
    renders them as 'skip' before the rip phase starts."""
    from arm.models.track import Track
    from arm.ripper.utils import mark_prescan_filter_state

    short = Track(
        job_id=sample_job.job_id, track_number="0", length=33,
        aspect_ratio="16:9", fps=23.976, main_feature=False,
        source="MakeMKV", basename="t0", filename="t0.mkv",
    )
    long_track = Track(
        job_id=sample_job.job_id, track_number="1", length=5400,
        aspect_ratio="16:9", fps=23.976, main_feature=True,
        source="MakeMKV", basename="t1", filename="t1.mkv",
    )
    db.session.add_all([short, long_track])
    db.session.commit()
    db.session.refresh(sample_job)

    mark_prescan_filter_state(sample_job, minlength=600, maxlength=99999)
    db.session.commit()

    db.session.refresh(short)
    db.session.refresh(long_track)
    assert short.process is False
    assert short.skip_reason == "too_short"
    # Long-enough tracks keep process=None (the serializer's NULL->True
    # default makes the widget render them as rippable).
    assert long_track.process is None
    assert long_track.skip_reason is None


def test_mark_prescan_filter_state_skips_too_long_tracks(app_context, sample_job):
    """Tracks above MAXLENGTH get process=False + skip_reason=too_long."""
    from arm.models.track import Track
    from arm.ripper.utils import mark_prescan_filter_state

    too_long = Track(
        job_id=sample_job.job_id, track_number="0", length=12345,
        aspect_ratio="16:9", fps=23.976, main_feature=False,
        source="MakeMKV", basename="t0", filename="t0.mkv",
    )
    db.session.add(too_long)
    db.session.commit()
    db.session.refresh(sample_job)

    mark_prescan_filter_state(sample_job, minlength=600, maxlength=5000)
    db.session.commit()

    db.session.refresh(too_long)
    assert too_long.process is False
    assert too_long.skip_reason == "too_long"


def test_mark_prescan_filter_state_skips_tracks_with_null_length(app_context, sample_job):
    """Tracks with length=None (music CDs, unscanned folders) are not
    touched - process stays None, skip_reason stays None."""
    from arm.models.track import Track
    from arm.ripper.utils import mark_prescan_filter_state

    no_length = Track(
        job_id=sample_job.job_id, track_number="0", length=None,
        aspect_ratio="", fps=0.0, main_feature=False,
        source="MakeMKV", basename="t0", filename="t0.mkv",
    )
    db.session.add(no_length)
    db.session.commit()
    db.session.refresh(sample_job)

    mark_prescan_filter_state(sample_job, minlength=600, maxlength=5000)
    db.session.commit()

    db.session.refresh(no_length)
    assert no_length.process is None
    assert no_length.skip_reason is None
