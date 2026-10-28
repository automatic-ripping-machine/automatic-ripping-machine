"""Log viewer reads: bounded, closed, incremental (#1561, #1631)."""

from pathlib import Path
import shutil
import subprocess

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


def test_raw_reads_advance_through_long_lines(tmp_path):
    from arm.ui import utils as ui_utils
    original = b"ARM: " + b"x" * 100 + b"\n"
    path = write_log(tmp_path / "long.log", original)
    chunks, offset, file_id = [], 0, None
    while offset < len(original):
        data, start, next_offset, file_id = ui_utils.read_log_data(path, offset, limit=16, file_id=file_id)
        assert start == offset
        assert 0 < next_offset - offset <= 16
        chunks.append(data)
        offset = next_offset
    assert b"".join(chunks) == original
    assert "".join(ui_utils.generate_arm_cat(path)) == original.decode()


def test_armcat_snapshot_keeps_a_marker_and_unicode_split_across_reads(tmp_path, monkeypatch):
    from arm.ui import utils as ui_utils
    monkeypatch.setattr(ui_utils, "LOG_CHUNK_BYTES", 3)
    original = "noise\nARM: café\nplain\nARM: last"
    path = write_log(tmp_path / "split.log", original.encode())
    assert "".join(ui_utils.generate_arm_cat(path)) == "ARM: café\nARM: last"


@pytest.mark.parametrize("rotation", ["truncate", "replace", "copytruncate"])
def test_raw_cursor_resets_when_the_log_rotates(tmp_path, rotation):
    from arm.ui import utils as ui_utils
    path = write_log(tmp_path / "rotate.log", b"old log\n" * 20)
    _, _, offset, file_id = ui_utils.read_log_data(path)
    replacement = b"new log\n" * (30 if rotation != "truncate" else 1)
    if rotation == "replace":
        write_log(tmp_path / "new.log", replacement).replace(path)
    else:
        path.write_bytes(replacement)
    data, start, next_offset, new_id = ui_utils.read_log_data(path, offset, file_id=file_id)
    assert start == 0
    assert data == replacement
    assert next_offset == len(replacement)
    assert new_id != file_id


def test_logreader_rotation_headers_reset_even_when_new_file_is_larger(monkeypatch):
    from arm.ui import app
    import arm.ui.routes  # noqa: F401
    monkeypatch.setitem(app.config, "LOGIN_DISABLED", True)
    log = Path(cfg.arm_config["LOGPATH"]) / "rotate-http.log"
    write_log(log, b"ARM: old\n")
    try:
        client = app.test_client()
        response = client.get("/logreader?logfile=rotate-http.log&mode=full")
        cursor = {"offset": response.headers["X-Log-Offset"], "file_id": response.headers["X-Log-Id"]}
        log.write_bytes(b"ARM: replacement\n" * 20)
        response = client.get("/logreader", query_string={"logfile": log.name, "mode": "full", **cursor})
        assert response.headers["X-Log-Start"] == "0"
        assert response.data == log.read_bytes()
    finally:
        log.unlink()


def test_log_page_runs_its_real_polling_script(tmp_path, monkeypatch):
    from arm.ui import app
    import arm.ui.routes  # noqa: F401
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required to execute the rendered log page's JavaScript")
    monkeypatch.setitem(app.config, "LOGIN_DISABLED", True)
    page = app.test_client().get("/logs?logfile=page-test.log&mode=armcat")
    assert page.status_code == 200
    rendered = tmp_path / "log.html"
    rendered.write_bytes(page.data)
    subprocess.run([node, str(Path(__file__).with_name("check_log_page.js")), str(rendered)],
                   check=True, capture_output=True, timeout=15)
