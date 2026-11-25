"""Disc type detection for hybrid Blu-ray discs (#1831)."""

from types import SimpleNamespace


def test_1831_hybrid_bluray_is_not_detected_as_dvd(tmp_path, monkeypatch):
    from arm.models.job import Job
    import arm.models.job as job_module

    for name in ("BDMV", "VIDEO_TS"):
        (tmp_path / name).mkdir()
    job = Job.__mapper__.class_manager.new_instance()
    job.mountpoint, job.disctype = str(tmp_path), "unknown"
    job.get_disc_type(False)
    assert job.disctype == "bluray"
    (tmp_path / "BDMV").rmdir()
    job.get_disc_type(False)
    assert job.disctype == "dvd"
    properties = {"ID_CDROM_MEDIA_BD": "1", "ID_CDROM_MEDIA_DVD": "1", "ID_FS_LABEL": "HYBRID"}
    monkeypatch.setattr(job_module.pyudev, "Context", lambda: None, raising=False)
    monkeypatch.setattr(job_module.pyudev.Devices, "from_device_file",
                        lambda context, path: SimpleNamespace(items=lambda: properties.items()))
    job.devpath = "/dev/sr0"
    job.parse_udev()
    assert job.disctype == "bluray"
