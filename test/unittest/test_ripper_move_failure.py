"""Ripped files must not be deleted when they could not be moved to the completed folder."""
from types import SimpleNamespace

import pytest

import arm.config.config as cfg
from arm.ripper import arm_ripper, utils


class _Tracks(list):
    """Stand-in for the job.tracks query"""

    def filter_by(self, **kwargs):
        return _Tracks(track for track in self if all(getattr(track, key) == value for key, value in kwargs.items()))

    def count(self):
        return len(self)


def _set_attrs(values, job):
    for key, value in values.items():
        setattr(job, key, value)


@pytest.fixture
def series_job(tmp_path, monkeypatch):
    """A series Blu-ray ripped with MakeMKV to raw/, transcoding disabled"""
    raw_dir = tmp_path / "raw" / "Show_1"
    raw_dir.mkdir(parents=True)
    (raw_dir / "title_t00.mkv").write_bytes(b"ripped title")
    config = SimpleNamespace(TRANSCODE_PATH=str(tmp_path / "transcode"), COMPLETED_PATH=str(tmp_path / "completed"),
                             SKIP_TRANSCODE=True, NOTIFY_RIP=False, NOTIFY_TRANSCODE=False, MAINFEATURE=False,
                             RIPMETHOD="mkv", EXTRAS_SUB="extras", DEST_EXT="mkv")
    track = SimpleNamespace(filename="title_t00.mkv", source="MakeMKV", main_feature=False, ripped=True)
    job = SimpleNamespace(config=config, video_type="series", title="Show", title_manual=None, year="2020",
                          hasnicetitle=True, disctype="bluray", devpath="/dev/sr0", status="active",
                          path=None, tracks=_Tracks([track]))

    monkeypatch.setitem(cfg.arm_config, "DELRAWFILES", True)
    monkeypatch.setattr(utils, "check_for_dupe_folder", lambda _dupes, path, _job: path)
    monkeypatch.setattr(utils, "database_updater", _set_attrs)
    for name in ("save_disc_poster", "notify", "scan_emby", "set_permissions"):
        monkeypatch.setattr(utils, name, lambda *_args: None)
    monkeypatch.setattr(arm_ripper.db.session, "commit", lambda: None)
    monkeypatch.setattr(arm_ripper.makemkv, "makemkv", lambda _job: str(raw_dir))
    final_dir = tmp_path / "completed" / "tv" / "Show (2020)"
    return job, raw_dir, final_dir


def test_files_moved_then_raw_deleted(series_job):
    job, raw_dir, final_dir = series_job

    arm_ripper.rip_visual_media(False, job, "job.log", 0)

    assert (final_dir / "title_t00.mkv").read_bytes() == b"ripped title"
    assert not raw_dir.exists()


def test_destination_exists_keeps_raw_and_fails(series_job):
    job, raw_dir, final_dir = series_job
    final_dir.mkdir(parents=True)
    (final_dir / "title_t00.mkv").write_bytes(b"other disc")

    with pytest.raises(utils.RipperException, match="could not be moved"):
        arm_ripper.rip_visual_media(False, job, "job.log", 0)

    assert (raw_dir / "title_t00.mkv").read_bytes() == b"ripped title"
    assert (final_dir / "title_t00.mkv").read_bytes() == b"other disc"


@pytest.mark.parametrize("video_type", ["series", "movie"])
@pytest.mark.parametrize("filename", ["", None, "   "])
def test_missing_required_filename_keeps_raw_and_fails(series_job, video_type, filename):
    job, raw_dir, final_dir = series_job
    job.video_type = video_type
    job.tracks[0].filename = filename

    with pytest.raises(utils.RipperException, match="could not be moved"):
        arm_ripper.rip_visual_media(False, job, "job.log", 0)

    assert (raw_dir / "title_t00.mkv").read_bytes() == b"ripped title"


@pytest.mark.parametrize("video_type", ["series", "movie"])
@pytest.mark.parametrize("only_unripped", [False, True])
def test_no_ripped_tracks_keeps_raw_and_fails(series_job, video_type, only_unripped):
    job, raw_dir, final_dir = series_job
    job.video_type = video_type
    if only_unripped:
        job.tracks[0].ripped = False
    else:
        job.tracks.clear()

    with pytest.raises(utils.RipperException, match="could not be moved"):
        arm_ripper.rip_visual_media(False, job, "job.log", 0)

    assert (raw_dir / "title_t00.mkv").read_bytes() == b"ripped title"


def test_incomplete_track_list_keeps_all_sources_before_moving(series_job):
    job, raw_dir, final_dir = series_job
    job.tracks.append(SimpleNamespace(filename="", source="MakeMKV", main_feature=False, ripped=True))

    with pytest.raises(utils.RipperException, match="could not be moved"):
        arm_ripper.rip_visual_media(False, job, "job.log", 0)

    assert (raw_dir / "title_t00.mkv").read_bytes() == b"ripped title"
    assert not (final_dir / "title_t00.mkv").exists()


def test_a_single_movie_track_is_moved_before_cleanup(series_job):
    job, raw_dir, final_dir = series_job
    job.video_type = "movie"

    arm_ripper.rip_visual_media(False, job, "job.log", 0)

    assert (final_dir.parent.parent / "movies" / "Show (2020)" / "Show (2020).mkv").read_bytes() == b"ripped title"
    assert not raw_dir.exists()


@pytest.fixture
def data_job(tmp_path, monkeypatch):
    """A data disc labelled DATA whose dd rip writes b'new image'"""
    config = SimpleNamespace(RAW_PATH=str(tmp_path / "raw"), COMPLETED_PATH=str(tmp_path / "completed"),
                             LOGPATH=str(tmp_path))
    job = SimpleNamespace(label="DATA", video_type="unknown", devpath="/dev/sr0", logfile="job.log",
                          config=config, status="active", errors=None)
    monkeypatch.setitem(cfg.arm_config, "DATA_RIP_PARAMETERS", "")
    monkeypatch.setattr(utils, "database_updater", _set_attrs)

    def fake_dd(cmd, shell):
        part_file = cmd.split('of="', 1)[1].split('"', 1)[0]
        with open(part_file, "wb") as image:
            image.write(b"new image")
        return b""

    monkeypatch.setattr(utils.subprocess, "check_output", fake_dd)
    return job, tmp_path / "completed" / "unidentified"


def test_data_disc_same_label_gets_unique_name(data_job, tmp_path):
    job, completed = data_job
    earlier = completed / "DATA" / "DATA.iso"
    earlier.parent.mkdir(parents=True)
    earlier.write_bytes(b"earlier image")

    assert utils.rip_data(job) is True

    assert earlier.read_bytes() == b"earlier image"
    images = sorted(completed.glob("DATA_*/DATA.iso"))
    assert len(images) == 1
    assert images[0].read_bytes() == b"new image"
    assert not (tmp_path / "raw" / "DATA").exists()


def test_data_disc_failed_move_keeps_image_and_fails(data_job, tmp_path, monkeypatch):
    job, _completed = data_job
    monkeypatch.setattr(utils, "move_files_main", lambda *_args: False)

    assert utils.rip_data(job) is False

    assert job.status == "fail"
    assert (tmp_path / "raw" / "DATA" / "DATA.part").read_bytes() == b"new image"
