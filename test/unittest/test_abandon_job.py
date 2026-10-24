"""Tests for terminate_process, used when a job is abandoned from the UI (#1014)"""
import contextlib
import shutil
import subprocess
import time

import psutil
import pytest

from arm.ui import json_api


class FakeProcess:
    """Stand-in for psutil.Process that records the signals it receives"""

    def __init__(self, pid, children=(), gone=False):
        self.pid = pid
        self._children = list(children)
        self.gone = gone
        self.signals = []

    def children(self, recursive=False):
        assert recursive
        return list(self._children)

    def terminate(self):
        if self.gone:
            raise psutil.NoSuchProcess(self.pid)
        self.signals.append("terminate")

    def kill(self):
        self.signals.append("kill")


def _install(monkeypatch, parent, survivors=()):
    monkeypatch.setattr(json_api.psutil, "Process", lambda pid: parent)
    waited = []

    def fake_wait_procs(procs, timeout=None):
        waited.extend(procs)
        alive = [p for p in procs if p in survivors]
        return [p for p in procs if p not in alive], alive

    monkeypatch.setattr(json_api.psutil, "wait_procs", fake_wait_procs)
    return waited


def test_children_are_terminated_with_parent(monkeypatch):
    handbrake = FakeProcess(102)
    shell = FakeProcess(101, children=[handbrake])
    ripper = FakeProcess(100, children=[shell, handbrake])
    waited = _install(monkeypatch, ripper)

    json_api.terminate_process(100)

    assert handbrake.signals == ["terminate"]
    assert shell.signals == ["terminate"]
    assert ripper.signals == ["terminate"]
    assert {p.pid for p in waited} == {100, 101, 102}


def test_survivors_are_killed(monkeypatch):
    stubborn = FakeProcess(201)
    ripper = FakeProcess(200, children=[stubborn])
    _install(monkeypatch, ripper, survivors=[stubborn])

    json_api.terminate_process(200)

    assert stubborn.signals == ["terminate", "kill"]
    assert ripper.signals == ["terminate"]


def test_child_that_already_exited_is_ignored(monkeypatch):
    finished = FakeProcess(301, gone=True)
    ripper = FakeProcess(300, children=[finished])
    _install(monkeypatch, ripper)

    json_api.terminate_process(300)

    assert ripper.signals == ["terminate"]


def test_access_denied_still_raises(monkeypatch):
    def denied(pid):
        raise psutil.AccessDenied(pid)

    monkeypatch.setattr(json_api.psutil, "Process", denied)
    with pytest.raises(ValueError):
        json_api.terminate_process(400)


@pytest.mark.skipif(shutil.which("sh") is None or shutil.which("sleep") is None,
                    reason="needs sh and sleep")
def test_real_shell_child_is_terminated():
    # Like HandBrakeCLI under shell=True: the shell waits on a child that does not get the signal
    shell = subprocess.Popen(["sh", "-c", "sleep 60 & wait"])
    sleepers = []
    try:
        deadline = time.monotonic() + 5
        while not sleepers and time.monotonic() < deadline:
            time.sleep(0.05)
            sleepers = psutil.Process(shell.pid).children(recursive=True)
        assert sleepers, "sleep child did not start"

        json_api.terminate_process(shell.pid)

        assert shell.wait(timeout=5) is not None
        _, alive = psutil.wait_procs(sleepers, timeout=5)
        assert not alive
    finally:
        # Don't leave an orphaned sleep behind when the assertion fails
        for proc in sleepers + [shell]:
            with contextlib.suppress(psutil.NoSuchProcess):
                proc.kill()
        shell.wait()
