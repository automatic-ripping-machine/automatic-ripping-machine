"""Tests for the settings page version/git checks in arm.ui.utils (#1345)."""
import subprocess

import arm.config.config as cfg
from arm.ui import utils as ui_utils


def _raise_git_error(*args, **kwargs):
    raise subprocess.CalledProcessError(128, args[0])


def _patch_failing_git(monkeypatch):
    """Make every git call fail like it does in the Docker image; return the recorded call kwargs."""
    calls = []

    def fake_check_output(*args, **kwargs):
        calls.append(kwargs)
        _raise_git_error(*args, **kwargs)

    monkeypatch.setattr(subprocess, 'check_output', fake_check_output)
    return calls


def test_git_check_version_no_remote_silences_git(tmp_path, monkeypatch):
    """With no origin remote, git's stderr is suppressed and the remote version is 'Unknown'."""
    (tmp_path / 'VERSION').write_text('2.22.1\n')
    monkeypatch.setitem(cfg.arm_config, 'INSTALLPATH', str(tmp_path))
    calls = _patch_failing_git(monkeypatch)

    local_version, remote_version = ui_utils.git_check_version()

    assert local_version == '2.22.1'
    assert remote_version == 'Unknown'
    assert len(calls) == 1
    assert calls[0].get('stderr') is subprocess.DEVNULL


def test_git_check_version_returns_remote_version(tmp_path, monkeypatch):
    """When git can read the remote VERSION it is returned stripped."""
    (tmp_path / 'VERSION').write_text('2.22.0\n')
    monkeypatch.setitem(cfg.arm_config, 'INSTALLPATH', str(tmp_path))
    monkeypatch.setattr(subprocess, 'check_output', lambda *a, **k: b'2.22.1\n')

    assert ui_utils.git_check_version() == ('2.22.0', '2.22.1')


def test_git_check_version_missing_version_file(tmp_path, monkeypatch):
    """A missing local VERSION file reports 'unknown' instead of raising UnboundLocalError."""
    monkeypatch.setitem(cfg.arm_config, 'INSTALLPATH', str(tmp_path))
    monkeypatch.setattr(subprocess, 'check_output', _raise_git_error)

    local_version, remote_version = ui_utils.git_check_version()

    assert local_version == 'unknown'
    assert remote_version == 'Unknown'


def test_get_git_revision_hash_silences_git(tmp_path, monkeypatch):
    """A failing 'git rev-parse' returns 'unknown' and does not write to stderr."""
    monkeypatch.setitem(cfg.arm_config, 'INSTALLPATH', str(tmp_path))
    calls = _patch_failing_git(monkeypatch)

    assert ui_utils.get_git_revision_hash() == 'unknown'
    assert calls[0].get('stderr') is subprocess.DEVNULL
