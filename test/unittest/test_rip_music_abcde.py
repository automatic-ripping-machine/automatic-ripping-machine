"""abcde must not report success for an incomplete rip (#1526)."""

import os
import stat
import sys
from types import SimpleNamespace

import pytest

ABCDE = r'''#!{python}
import os, sys
mode = os.environ["FAKE_ABCDE_MODE"]
out = os.environ["FAKE_ABCDE_OUT"]
os.makedirs(out + "/Artist/Album", exist_ok=True)
count = 2 if mode == "short" else 3
for n in range(1, count + 1):
    with open(out + "/Artist/Album/%02d - Song.flac" % n, "wb") as f:
        f.write(b"" if mode == "empty" and n == 2 else b"fLaC data")
print("Grabbing track 01...")
if mode != "unfinished":
    print("Finished.")
sys.exit(3 if mode == "exit" else 0)
'''


@pytest.fixture
def abcde(tmp_path, monkeypatch):
    import arm.config.config as cfg
    from arm.ripper import music_brainz, utils

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "abcde"
    script.write_text(ABCDE.format(python=sys.executable))
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("FAKE_ABCDE_OUT", str(tmp_path / "music"))
    conf = tmp_path / "abcde.conf"
    conf.write_text('OUTPUTTYPE=flac\nOUTPUTDIR="%s"\n' % (tmp_path / "music"))
    monkeypatch.setitem(cfg.arm_config, "ABCDE_CONFIG_FILE", str(conf))
    monkeypatch.setattr(music_brainz, "get_disc_id", lambda job: SimpleNamespace(tracks=[1, 2, 3]))
    updates = []
    monkeypatch.setattr(utils, "database_updater", lambda values, job: updates.append(values))
    job = SimpleNamespace(disctype="music", devpath="/dev/sr0", config=SimpleNamespace(LOGPATH=str(tmp_path)))

    def run(mode):
        monkeypatch.setenv("FAKE_ABCDE_MODE", mode)
        return utils.rip_music(job, "music.log")

    return run, updates, conf


def test_complete_rip_succeeds(abcde):
    run, updates, _ = abcde
    assert run("ok") is True
    assert updates[-1] == {"status": "active"}


@pytest.mark.parametrize("mode,reason", [("unfinished", "Finished"), ("short", "2 flac file"),
                                         ("empty", "empty"), ("exit", "abcde failed")])
def test_incomplete_rips_fail_the_job(abcde, mode, reason):
    run, updates, _ = abcde
    assert run(mode) is False
    assert updates[-1]["status"] == "fail" and reason in updates[-1]["errors"]


def test_unresolvable_output_dir_still_requires_finished(abcde):
    run, updates, conf = abcde
    conf.write_text("OUTPUTTYPE=flac\nOUTPUTDIR=$HOME/music\n")
    assert run("short") is True
    assert run("unfinished") is False and "Finished" in updates[-1]["errors"]


def test_abcde_outputs_reads_the_shipped_config():
    from pathlib import Path
    from arm.ripper import utils

    text = (Path(__file__).resolve().parents[2] / "setup" / ".abcde.conf").read_text()
    assert utils.abcde_outputs(text) == ("/home/arm/music/", ["ogg"])
    assert utils.abcde_outputs("OUTPUTTYPE=flac,mp3:-V 2\nOUTPUTDIR='/music'\n") == ("/music", ["flac", "mp3"])
