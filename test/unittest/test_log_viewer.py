"""Log viewer reads: bounded, closed, incremental (#1561, #1631)."""

from pathlib import Path

import pytest

import arm.config.config as cfg


def write_log(path, data):
    path.write_bytes(data)
    return path


def test_log_reads_are_bounded_closed_and_tolerant(tmp_path, monkeypatch):
    from arm.ui import utils as ui_utils

    monkeypatch.setattr(ui_utils, "sleep", lambda *_: pytest.fail("log reader must not sleep"))
    path = write_log(tmp_path / "job.log", b"ARM: one\nplain \xff\xfe bytes\nARM: two\npartial")
    text, offset = ui_utils.read_log_chunk(path)
    assert text == "ARM: one\nplain �� bytes\nARM: two\npartial"
    assert offset == path.stat().st_size
    assert ui_utils.read_log_chunk(path, offset) == ("", offset)
    with path.open("ab") as stream:
        stream.write(b" line\nARM: three\n")
    assert ui_utils.read_log_chunk(path, offset)[0] == " line\nARM: three\n"
    assert "".join(ui_utils.generate_full_log(path)) == path.read_bytes().decode("utf-8", "replace")
    assert list(ui_utils.generate_arm_cat(path)) == ["ARM: one\n", "ARM: two\n", "ARM: three\n"]
    # A limit that falls mid-file ends on a line boundary; a shrunken (rotated) file restarts at 0.
    assert ui_utils.read_log_chunk(path, 0, limit=12) == ("ARM: one\n", 9)
    assert ui_utils.read_log_chunk(path, 10 ** 6)[1] == path.stat().st_size


def test_logreader_serves_increments_and_the_page_appends(monkeypatch):
    from arm.ui import app
    import arm.ui.routes  # noqa: F401 -- registers the blueprints like runui

    monkeypatch.setitem(app.config, "LOGIN_DISABLED", True)
    client = app.test_client()
    log = Path(cfg.arm_config["LOGPATH"]) / "increment-test.log"
    write_log(log, b"first\nARM: second\n")
    response = client.get("/logreader?logfile=increment-test.log&mode=full&offset=6")
    assert response.data == b"ARM: second\n"
    assert response.headers["X-Log-Offset"] == str(log.stat().st_size)
    armcat = client.get("/logreader?logfile=increment-test.log&mode=armcat")
    assert armcat.data == b"ARM: second\n"
    page = client.get("/logs?logfile=increment-test.log&mode=tail").data.decode()
    assert "appendChild" in page
    assert "setInterval" not in page
    assert "X-Log-Offset" in page
    log.unlink()


def test_logreader_refuses_a_log_that_resolves_outside_the_log_folder(monkeypatch, tmp_path):
    from arm.ui import app
    import arm.ui.routes  # noqa: F401 -- registers the blueprints like runui

    monkeypatch.setitem(app.config, "LOGIN_DISABLED", True)
    secret = tmp_path / "secret.txt"
    secret.write_text("not a log\n")
    link = Path(cfg.arm_config["LOGPATH"]) / "escape-test.log"
    link.symlink_to(secret)
    try:
        response = app.test_client().get("/logreader?logfile=escape-test.log&mode=full")
        assert b"not a log" not in response.data
    finally:
        link.unlink()
