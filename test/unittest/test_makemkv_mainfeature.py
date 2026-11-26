"""Tests for main feature selection in makemkv_mkv"""
from types import SimpleNamespace

from arm.models import Track
from arm.ripper import makemkv
from arm.ui import app, db
import arm.ui.routes  # noqa: F401


def test_mainfeature_prefers_filesize_over_chapters(monkeypatch, tmp_path):
    """A small extra with more chapters must not beat the film (#1832)"""
    job_id = 987654
    job = SimpleNamespace(job_id=job_id, devpath="/dev/sr0",
                          drive=SimpleNamespace(mdisc=0),
                          config=SimpleNamespace(MAINFEATURE=True))
    selected = []
    monkeypatch.setattr(makemkv.utils, "get_drive_mode", lambda devpath: "auto")
    monkeypatch.setattr(makemkv, "get_track_info", lambda mdisc, job: None)
    monkeypatch.setattr(makemkv, "rip_mainfeature", lambda job, track, rawpath: selected.append(track))

    with app.app_context():
        db.create_all()
        app.config.update(TESTING=True, LOGIN_DISABLED=True)
        # Values from the District 9 disc in #1832
        film = Track(job_id, "0", 6735, 1.78, 23.976, False, "MakeMKV", "", "title_t00.mkv",
                     chapters=16, filesize=24_500_000_000)
        extra = Track(job_id, "3", 1273, 1.78, 29.97, False, "MakeMKV", "", "title_t03.mkv",
                      chapters=52, filesize=2_100_000_000)
        db.session.add_all([extra, film])
        db.session.commit()
        try:
            makemkv.makemkv_mkv(job, str(tmp_path))
            assert len(selected) == 1
            assert selected[0].filename == "title_t00.mkv"
        finally:
            Track.query.filter_by(job_id=job_id).delete()
            db.session.commit()
