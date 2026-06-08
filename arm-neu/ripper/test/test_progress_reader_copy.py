from pathlib import Path

import pytest


def test_get_copy_progress_no_file(tmp_path, monkeypatch):
    import arm.config.config as cfg
    monkeypatch.setitem(cfg.arm_config, "LOGPATH", str(tmp_path))
    from arm.services.progress_reader import get_copy_progress
    assert get_copy_progress(42) == {
        "progress": None, "stage": None,
        "files_transferred": None, "current_file": None,
    }


def test_get_copy_progress_returns_latest_entry(tmp_path, monkeypatch):
    import arm.config.config as cfg
    monkeypatch.setitem(cfg.arm_config, "LOGPATH", str(tmp_path))
    progress_dir = tmp_path / "progress"
    progress_dir.mkdir()
    (progress_dir / "42.copy.log").write_text(
        "scratch-to-media,12.5,1,/raw/abc/file_a.mkv\n"
        "scratch-to-media,47.0,1,/raw/abc/file_a.mkv\n"
        "scratch-to-media,100.0,2,/raw/abc/file_b.mkv\n"
    )
    from arm.services.progress_reader import get_copy_progress
    out = get_copy_progress(42)
    assert out["progress"] == pytest.approx(100.0)
    assert out["stage"] == "scratch-to-media"
    assert out["files_transferred"] == 2
    assert out["current_file"] == "/raw/abc/file_b.mkv"


def test_get_copy_progress_filters_by_stage(tmp_path, monkeypatch):
    import arm.config.config as cfg
    monkeypatch.setitem(cfg.arm_config, "LOGPATH", str(tmp_path))
    progress_dir = tmp_path / "progress"
    progress_dir.mkdir()
    (progress_dir / "42.copy.log").write_text(
        "scratch-to-media,100.0,2,/raw/abc/file_b.mkv\n"
        "work-to-completed,30.0,1,/completed/file_a.mkv\n"
    )
    from arm.services.progress_reader import get_copy_progress
    out_default = get_copy_progress(42)
    assert out_default["stage"] == "work-to-completed"
    assert out_default["progress"] == pytest.approx(30.0)

    out_filtered = get_copy_progress(42, stage="scratch-to-media")
    assert out_filtered["stage"] == "scratch-to-media"
    assert out_filtered["progress"] == pytest.approx(100.0)


def test_get_copy_progress_fail_soft_on_garbage(tmp_path, monkeypatch):
    import arm.config.config as cfg
    monkeypatch.setitem(cfg.arm_config, "LOGPATH", str(tmp_path))
    progress_dir = tmp_path / "progress"
    progress_dir.mkdir()
    (progress_dir / "42.copy.log").write_text(
        "garbage,this,is,not,a,real,line\n"
        "scratch-to-media,47.0,1,/raw/abc/file_a.mkv\n"
        "another,bad,line\n"
    )
    from arm.services.progress_reader import get_copy_progress
    out = get_copy_progress(42)
    # Garbage lines are skipped; the one valid line wins.
    assert out["progress"] == pytest.approx(47.0)
    assert out["stage"] == "scratch-to-media"
