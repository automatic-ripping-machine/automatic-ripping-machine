"""Tests for the folder ownership checks in the docker startup script.

The functions are pulled out of arm_user_files_setup.sh and run with bash, with
stat, mountpoint, chown and runuser replaced by stubs on PATH.
"""
import os
import re
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "docker" / "runit" / "arm_user_files_setup.sh"

STUBS = {
    # Owner is kept in a state file so the chown stub can change what stat reports
    "stat": 'case "$2" in %u) cut -d: -f1 "$STATE";; %g) cut -d: -f2 "$STATE";; esac\n',
    "mountpoint": 'exit "$MOUNTED"\n',
    "chown": 'echo "$*" >> "$CALLS"\n[ "$1" = "arm:arm" ] && echo "$ARM_UID:$ARM_GID" > "$STATE"\nexit 0\n',
    "runuser": 'exit "$WRITABLE"\n',
}


def _functions():
    text = SCRIPT.read_text()
    return "\n".join(re.findall(r"^\w+\(\) \{\n.*?^\}$", text, re.M | re.S))


def _run(tmp_path, owner, mounted, writable, commands):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in STUBS.items():
        stub = bin_dir / name
        stub.write_text("#!/bin/sh\n" + body)
        stub.chmod(0o755)
    state = tmp_path / "owner"
    state.write_text(owner + "\n")
    calls = tmp_path / "calls"
    calls.write_text("")
    home = tmp_path / "home"
    home.mkdir()
    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}", STATE=str(state), CALLS=str(calls),
               MOUNTED="0" if mounted else "1", WRITABLE="0" if writable else "1",
               ARM_UID="1035", ARM_GID="100", ARM_HOME=str(home))
    script = "set -euo pipefail\n" + _functions() + "\n" + commands
    proc = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
    return proc, calls.read_text().split("\n")[0], home


def test_unmounted_home_with_custom_gid_is_fixed(tmp_path):
    # usermod -u moved the owner, groupmod -g left the group at 1000 (#1186)
    proc, chown_call, home = _run(tmp_path, "1035:1000", mounted=False, writable=False,
                                  commands='fix_home_ownership\ncheck_folder_ownership "$ARM_HOME"\n')
    assert proc.returncode == 0, proc.stdout
    assert chown_call == f"arm:arm {home}"
    assert "[OK]" in proc.stdout


def test_mounted_home_is_not_chowned_and_wrong_owner_fails(tmp_path):
    proc, chown_call, _ = _run(tmp_path, "0:0", mounted=True, writable=False,
                               commands='fix_home_ownership\ncheck_folder_ownership "$ARM_HOME"\n')
    assert proc.returncode == 1
    assert chown_call == ""
    assert "[ERROR]" in proc.stdout


def test_mounted_folder_writable_by_arm_passes(tmp_path):
    # e.g. an NFS share where the server squashes ownership
    proc, _, _ = _run(tmp_path, "1035:1000", mounted=True, writable=True,
                      commands='check_folder_ownership "$ARM_HOME"\n')
    assert proc.returncode == 0, proc.stdout
    assert "[WARN]" in proc.stdout
