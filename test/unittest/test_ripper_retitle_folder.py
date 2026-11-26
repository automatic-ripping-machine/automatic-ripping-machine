"""A title set during the rip must not reuse a completed folder that already exists."""
from types import SimpleNamespace

import pytest

import arm.config.config as cfg
from arm.ripper import arm_ripper, utils


class _Tracks(list):
    """Stand-in for the job.tracks query"""

    def filter_by(self, **_kwargs):
        return self

    def count(self):
        return len(self)


def _set_attrs(values, job):
    for key, value in values.items():
        setattr(job, key, value)


@pytest.fixture
def series_job(tmp_path, monkeypatch):
    """A series Blu-ray ripped with MakeMKV to raw/, transcoding disabled"""
    raw_dir = tmp_path / "raw" / "WRONG_1"
    raw_dir.mkdir(parents=True)
    (raw_dir / "title_t00.mkv").write_bytes(b"disc 2")
    config = SimpleNamespace(TRANSCODE_PATH=str(tmp_path / "transcode"), COMPLETED_PATH=str(tmp_path / "completed"),
                             SKIP_TRANSCODE=True, NOTIFY_RIP=False, NOTIFY_TRANSCODE=False, MAINFEATURE=False,
                             RIPMETHOD="mkv", EXTRAS_SUB="extras", DEST_EXT="mkv")
    track = SimpleNamespace(filename="title_t00.mkv", source="MakeMKV", main_feature=False)
    job = SimpleNamespace(config=config, video_type="series", title="Wrong", title_manual=None, year="2020",
                          hasnicetitle=True, disctype="bluray", devpath="/dev/sr0", status="active",
                          stage="171947566811", path=None, tracks=_Tracks([track]))

    monkeypatch.setitem(cfg.arm_config, "DELRAWFILES", True)
    monkeypatch.setitem(cfg.arm_config, "ALLOW_DUPLICATES", False)
    monkeypatch.setattr(utils, "database_updater", _set_attrs)
    for name in ("save_disc_poster", "notify", "scan_emby", "set_permissions"):
        monkeypatch.setattr(utils, name, lambda *_args: None)
    monkeypatch.setattr(arm_ripper.db.session, "commit", lambda: None)
    return job, raw_dir, tmp_path / "completed" / "tv"


def test_title_set_during_rip_gets_new_folder_when_taken(series_job, monkeypatch):
    job, raw_dir, completed = series_job
    earlier = completed / "Show (2020)" / "title_t00.mkv"
    earlier.parent.mkdir(parents=True)
    earlier.write_bytes(b"disc 1")

    def rip_and_retitle(_job):
        # The user corrects the title while MakeMKV is running
        job.title_manual = "Show"
        return str(raw_dir)

    monkeypatch.setattr(arm_ripper.makemkv, "makemkv", rip_and_retitle)

    arm_ripper.rip_visual_media(False, job, "job.log", 0)

    new_folder = completed / "Show (2020)_171947566811"
    assert job.path == str(new_folder)
    assert (new_folder / "title_t00.mkv").read_bytes() == b"disc 2"
    assert earlier.read_bytes() == b"disc 1"
    assert not (completed / "Wrong (2020)").exists()


def test_title_set_before_rip_keeps_its_folder(series_job, monkeypatch):
    job, raw_dir, completed = series_job
    job.title_manual = "Show"
    monkeypatch.setattr(arm_ripper.makemkv, "makemkv", lambda _job: str(raw_dir))

    arm_ripper.rip_visual_media(False, job, "job.log", 0)

    assert job.path == str(completed / "Show (2020)")
    assert (completed / "Show (2020)" / "title_t00.mkv").read_bytes() == b"disc 2"
    assert not (completed / "Show (2020)_171947566811").exists()
