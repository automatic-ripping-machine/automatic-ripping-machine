"""Tests for arm/ripper/iso_scan.py - filesystem-side ISO validation + filename metadata."""
import pytest


class TestValidateIsoPath:
    def test_accepts_iso_under_ingress(self, tmp_path):
        from arm.ripper.iso_scan import validate_iso_path
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        iso = ingress / "Movie.iso"
        iso.write_bytes(b"\x00")
        validate_iso_path(str(iso), str(ingress))

    def test_accepts_iso_in_subdirectory(self, tmp_path):
        from arm.ripper.iso_scan import validate_iso_path
        ingress = tmp_path / "ingress"
        sub = ingress / "subdir"
        sub.mkdir(parents=True)
        iso = sub / "Movie.iso"
        iso.write_bytes(b"\x00")
        validate_iso_path(str(iso), str(ingress))

    def test_rejects_path_traversal(self, tmp_path):
        from arm.ripper.iso_scan import validate_iso_path
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        outside = tmp_path / "evil.iso"
        outside.write_bytes(b"\x00")
        with pytest.raises(ValueError):
            validate_iso_path(str(outside), str(ingress))

    def test_rejects_missing_file(self, tmp_path):
        from arm.ripper.iso_scan import validate_iso_path
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        with pytest.raises(FileNotFoundError):
            validate_iso_path(str(ingress / "absent.iso"), str(ingress))

    def test_rejects_non_iso_extension(self, tmp_path):
        from arm.ripper.iso_scan import validate_iso_path
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        notiso = ingress / "Movie.mkv"
        notiso.write_bytes(b"\x00")
        with pytest.raises(ValueError, match="extension"):
            validate_iso_path(str(notiso), str(ingress))

    def test_accepts_uppercase_iso_extension(self, tmp_path):
        from arm.ripper.iso_scan import validate_iso_path
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        iso = ingress / "Movie.ISO"
        iso.write_bytes(b"\x00")
        validate_iso_path(str(iso), str(ingress))


class TestExtractMetadata:
    def test_returns_size_and_label_with_year(self, tmp_path):
        from arm.ripper.iso_scan import extract_metadata
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        iso = ingress / "Movie Title (2020).iso"
        iso.write_bytes(b"x" * 1024)
        meta = extract_metadata(str(iso))
        assert meta["iso_size"] == 1024
        assert meta["title_suggestion"] == "Movie Title"
        assert meta["year_suggestion"] == "2020"
        assert meta["label"] == "Movie Title (2020)"

    def test_handles_filename_without_year(self, tmp_path):
        from arm.ripper.iso_scan import extract_metadata
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        iso = ingress / "Random Disc.iso"
        iso.write_bytes(b"x" * 512)
        meta = extract_metadata(str(iso))
        assert meta["iso_size"] == 512
        assert meta["label"] == "Random Disc"
        assert meta["title_suggestion"] == "Random Disc"
        assert meta["year_suggestion"] is None

    def test_strips_iso_extension_case_insensitively(self, tmp_path):
        from arm.ripper.iso_scan import extract_metadata
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        iso = ingress / "Disc Two.ISO"
        iso.write_bytes(b"x" * 8)
        meta = extract_metadata(str(iso))
        assert meta["label"] == "Disc Two"
