"""HandBrake command quoting for titles with a single quote (#1457)."""

import shlex
import subprocess

import arm.config.config as cfg


def test_1457_handbrake_log_path_with_a_single_quote(tmp_path, monkeypatch):
    from arm.ripper import handbrake

    monkeypatch.setitem(cfg.arm_config, "HANDBRAKE_CLI", "echo")
    log = tmp_path / "Ocean's Eleven (2001).log"
    output = tmp_path / "Ocean's Eleven (2001).mkv"
    cmd = handbrake.build_handbrake_command("/dev/sr0", str(output), "H.265 MKV 1080p30", "--subtitle scan", str(log),
                                            track_number="3")
    assert shlex.split(cmd)[-3:] == [">>", str(log), "2>&1"]
    subprocess.run(cmd, shell=True, check=True)
    written = log.read_text()
    assert "-o " + str(output) in written and "--preset H.265 MKV 1080p30" in written and "-t 3" in written
