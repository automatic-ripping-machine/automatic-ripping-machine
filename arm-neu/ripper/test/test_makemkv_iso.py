"""Tests for ISO-related helpers in arm/ripper/makemkv.py."""
import pytest


class TestRunMakemkvInfoCaptureValidation:
    """The internal helper validates `source` matches ^iso:[^\\x00\\n]+$
    before passing it to subprocess.run.

    Defense-in-depth: the call uses argv-list form so shell metacharacters
    are not interpreted, but the regex also breaks the CodeQL taint
    dataflow for py/command-line-injection.
    """

    def test_accepts_valid_iso_path(self, monkeypatch):
        from arm.ripper import makemkv

        captured = {}

        class FakeResult:
            stdout = "TCOUNT:0\n"

        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            return FakeResult()

        monkeypatch.setattr(makemkv.subprocess, "run", fake_run)
        out = makemkv._run_makemkv_info_capture("iso:/tmp/Movie.iso")
        assert out == "TCOUNT:0\n"
        assert "iso:/tmp/Movie.iso" in captured["cmd"]

    def test_rejects_empty_iso_prefix(self, monkeypatch):
        from arm.ripper import makemkv

        # Should not even reach subprocess.run
        called = {"hit": False}

        def fake_run(*a, **kw):
            called["hit"] = True
            raise AssertionError("subprocess.run should not be invoked")

        monkeypatch.setattr(makemkv.subprocess, "run", fake_run)
        with pytest.raises(ValueError, match="Invalid source spec"):
            makemkv._run_makemkv_info_capture("iso:")
        assert called["hit"] is False

    def test_rejects_non_iso_scheme(self, monkeypatch):
        from arm.ripper import makemkv

        def fake_run(*a, **kw):
            raise AssertionError("subprocess.run should not be invoked")

        monkeypatch.setattr(makemkv.subprocess, "run", fake_run)
        with pytest.raises(ValueError, match="Invalid source spec"):
            makemkv._run_makemkv_info_capture("dev:/foo")

    def test_rejects_newline_in_source(self, monkeypatch):
        from arm.ripper import makemkv

        def fake_run(*a, **kw):
            raise AssertionError("subprocess.run should not be invoked")

        monkeypatch.setattr(makemkv.subprocess, "run", fake_run)
        with pytest.raises(ValueError, match="Invalid source spec"):
            makemkv._run_makemkv_info_capture("iso:/foo\nrm -rf")

    def test_rejects_null_byte_in_source(self, monkeypatch):
        from arm.ripper import makemkv

        def fake_run(*a, **kw):
            raise AssertionError("subprocess.run should not be invoked")

        monkeypatch.setattr(makemkv.subprocess, "run", fake_run)
        with pytest.raises(ValueError, match="Invalid source spec"):
            makemkv._run_makemkv_info_capture("iso:/foo\x00bar")


class TestPrescanIsoDiscType:
    """prescan_iso_disc_type runs MakeMKV --robot info on iso:{path} and parses output."""

    def test_parses_bluray_disc_type(self, monkeypatch, tmp_path):
        iso = tmp_path / "test.iso"
        iso.write_bytes(b"\x00")
        fake_output = (
            'CINFO:1,0,"BLU-RAY"\n'
            'CINFO:32,0,"VOL_LABEL_HERE"\n'
            'TCOUNT:5\n'
        )
        monkeypatch.setattr(
            "arm.ripper.makemkv._run_makemkv_info_capture",
            lambda source, **kw: fake_output,
        )
        from arm.ripper.makemkv import prescan_iso_disc_type
        result = prescan_iso_disc_type(str(iso))
        assert result["disc_type"] == "bluray"
        assert result["stream_count"] == 5
        assert result["volume_id"] == "VOL_LABEL_HERE"

    def test_parses_uhd_as_bluray4k(self, monkeypatch, tmp_path):
        iso = tmp_path / "uhd.iso"
        iso.write_bytes(b"\x00")
        fake_output = 'CINFO:1,0,"BLU-RAY UHD"\nTCOUNT:1\n'
        monkeypatch.setattr(
            "arm.ripper.makemkv._run_makemkv_info_capture",
            lambda source, **kw: fake_output,
        )
        from arm.ripper.makemkv import prescan_iso_disc_type
        result = prescan_iso_disc_type(str(iso))
        assert result["disc_type"] == "bluray4k"
        assert result["stream_count"] == 1
        assert result["volume_id"] is None

    def test_parses_dvd_disc_type(self, monkeypatch, tmp_path):
        iso = tmp_path / "movie.iso"
        iso.write_bytes(b"\x00")
        fake_output = (
            'CINFO:1,0,"DVD"\n'
            'CINFO:32,0,"DVD_VIDEO"\n'
            'TCOUNT:3\n'
        )
        monkeypatch.setattr(
            "arm.ripper.makemkv._run_makemkv_info_capture",
            lambda source, **kw: fake_output,
        )
        from arm.ripper.makemkv import prescan_iso_disc_type
        result = prescan_iso_disc_type(str(iso))
        assert result["disc_type"] == "dvd"
        assert result["stream_count"] == 3
        assert result["volume_id"] == "DVD_VIDEO"

    def test_unknown_disc_type_when_cinfo_missing(self, monkeypatch, tmp_path):
        iso = tmp_path / "obscure.iso"
        iso.write_bytes(b"\x00")
        monkeypatch.setattr(
            "arm.ripper.makemkv._run_makemkv_info_capture",
            lambda source, **kw: "TCOUNT:0\n",
        )
        from arm.ripper.makemkv import prescan_iso_disc_type
        result = prescan_iso_disc_type(str(iso))
        assert result["disc_type"] == "unknown"
        assert result["stream_count"] == 0
        assert result["volume_id"] is None

    def test_passes_iso_source_to_runner(self, monkeypatch, tmp_path):
        iso = tmp_path / "abc.iso"
        iso.write_bytes(b"\x00")
        captured = {}

        def fake_runner(source, **kw):
            captured["source"] = source
            captured["kw"] = kw
            return "TCOUNT:0\n"

        monkeypatch.setattr(
            "arm.ripper.makemkv._run_makemkv_info_capture", fake_runner,
        )
        from arm.ripper.makemkv import prescan_iso_disc_type
        prescan_iso_disc_type(str(iso), timeout=60)
        assert captured["source"] == f"iso:{iso}"
        assert captured["kw"].get("timeout") == 60
