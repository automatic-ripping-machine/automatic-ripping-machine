"""Failed rips must not end in arm.ripper.main.main() returning normally.

__main__ marks the job a success whenever main() returns, so every failure
branch has to raise utils.RipperException for the handler to mark it failed.
"""
import types

import pytest

from arm.ripper import main as ripper_main
from arm.ripper import arm_ripper, identify, music_brainz, utils


@pytest.fixture
def run_main(monkeypatch):
    """Run main() for a fake job of the given disc type, without hardware."""
    for module, name in ((identify, "identify"), (utils, "notify_entry"), (utils, "check_for_wait"),
                         (utils, "notify"), (utils, "scan_emby"), (music_brainz, "main"),
                         (ripper_main, "log_arm_params"), (ripper_main, "check_fstab")):
        monkeypatch.setattr(module, name, lambda *a, **k: None)
    monkeypatch.setattr(utils, "job_dupe_check", lambda job: False)
    monkeypatch.setattr(ripper_main.db.session, "commit", lambda: None)

    def run(disctype, **rippers):
        for name, ripper in rippers.items():
            monkeypatch.setattr(utils, name, ripper)
        job = types.SimpleNamespace(disctype=disctype, errors=None, label="DISC", title="Disc",
                                    has_track_99=False, status="active")
        monkeypatch.setattr(ripper_main, "job", job)
        monkeypatch.setattr(ripper_main, "log_file", "disc.log")
        ripper_main.main()
        return job

    return run


def failed_rip(message):
    """Fake rip_data/rip_music that records an error like the real ones do."""
    def rip(job, *args):
        job.errors = message
        return False
    return rip


def test_failed_data_rip_raises(run_main):
    with pytest.raises(utils.RipperException, match="Data rip failed with code: 1"):
        run_main("data", rip_data=failed_rip("Data rip failed with code: 1(b'')"))


def test_failed_music_rip_raises(run_main):
    with pytest.raises(utils.RipperException, match="Call to abcde failed"):
        run_main("music", rip_music=failed_rip("Call to abcde failed with code: 1 (b'')"))


def test_unknown_disc_type_raises(run_main):
    with pytest.raises(utils.RipperException, match="identify the disc type"):
        run_main("unknown")


def test_successful_data_rip_returns(run_main):
    job = run_main("data", rip_data=lambda job: True)
    assert job.errors is None


def test_successful_music_rip_returns(run_main):
    job = run_main("music", rip_music=lambda job, logfile: True)
    assert job.status == "success"


def test_video_disc_returns(run_main, monkeypatch):
    calls = []
    monkeypatch.setattr(arm_ripper, "rip_visual_media", lambda *args: calls.append(args))
    run_main("dvd")
    assert len(calls) == 1
