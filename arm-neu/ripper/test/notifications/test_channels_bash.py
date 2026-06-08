"""Tests for the bash channel sender."""
import os
import stat
import tempfile

import pytest


def _make_script(body: str) -> str:
    """Write a small bash script to a temp file and make it executable."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".sh", delete=False, prefix="arm-test-")
    f.write("#!/usr/bin/env bash\n")
    f.write(body)
    f.close()
    os.chmod(f.name, stat.S_IRWXU)
    return f.name


def test_bash_send_success_with_zero_exit():
    from arm.notifications.channels.bash import send_bash
    script = _make_script("exit 0\n")
    try:
        ok, error = send_bash(
            script_path=script,
            title="T", body="B",
            env_vars={"ARM_JOB_ID": "42"},
        )
        assert ok is True
        assert error is None
    finally:
        os.unlink(script)


def test_bash_send_nonzero_exit_is_terminal():
    from arm.notifications.channels.bash import send_bash
    script = _make_script("exit 5\n")
    try:
        ok, error = send_bash(
            script_path=script,
            title="T", body="B",
            env_vars={},
        )
        assert ok is False
        assert "terminal=true" in error
        assert "exit 5" in error or "exit code 5" in error
    finally:
        os.unlink(script)


def test_bash_send_missing_script_is_terminal():
    from arm.notifications.channels.bash import send_bash
    ok, error = send_bash(
        script_path="/nonexistent/path/to/script.sh",
        title="T", body="B",
        env_vars={},
    )
    assert ok is False
    assert "terminal=true" in error


def test_bash_send_non_executable_script_is_terminal():
    """A script that exists but lacks the execute bit is a terminal
    config error, not a transient failure."""
    from arm.notifications.channels.bash import send_bash
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".sh", delete=False, prefix="arm-test-noexec-")
    f.write("#!/usr/bin/env bash\nexit 0\n")
    f.close()
    # Read/write only — explicitly no execute bit.
    os.chmod(f.name, stat.S_IRUSR | stat.S_IWUSR)
    try:
        ok, error = send_bash(
            script_path=f.name,
            title="T", body="B",
            env_vars={},
        )
        assert ok is False
        assert "not executable" in error
        assert "terminal=true" in error
    finally:
        os.unlink(f.name)


def test_bash_send_timeout_is_terminal():
    """If the script runs past the configured timeout, terminate it
    and report terminal failure."""
    from arm.notifications.channels.bash import send_bash
    script = _make_script("sleep 60\n")
    try:
        ok, error = send_bash(
            script_path=script,
            title="T", body="B",
            env_vars={},
            timeout_seconds=1,
        )
        assert ok is False
        assert "terminal=true" in error
        assert "timeout" in error.lower()
    finally:
        os.unlink(script)


def test_bash_send_passes_env_vars():
    """The script should see all ARM_* env vars we pass."""
    from arm.notifications.channels.bash import send_bash
    out_file = tempfile.NamedTemporaryFile(
        delete=False, prefix="arm-test-").name
    script = _make_script(f"echo \"$ARM_JOB_ID:$ARM_TITLE\" > {out_file}\nexit 0\n")
    try:
        send_bash(
            script_path=script,
            title="T", body="B",
            env_vars={"ARM_JOB_ID": "169", "ARM_TITLE": "Mysterysuspense"},
        )
        with open(out_file) as f:
            output = f.read().strip()
        assert output == "169:Mysterysuspense"
    finally:
        os.unlink(script)
        if os.path.exists(out_file):
            os.unlink(out_file)
