"""Tests for folder structure detection and metadata extraction."""
import os
import pytest
from unittest.mock import patch


class TestDetectDiscType:
    def test_bdmv_detected_as_bluray(self, bdmv_folder):
        from arm.ripper.folder_scan import detect_disc_type
        result = detect_disc_type(str(bdmv_folder))
        assert result == "bluray"

    def test_bdmv_uhd_detected_as_bluray4k(self, bdmv_uhd_folder):
        from arm.ripper.folder_scan import detect_disc_type
        result = detect_disc_type(str(bdmv_uhd_folder))
        assert result == "bluray4k"

    def test_dvd_detected(self, dvd_folder):
        from arm.ripper.folder_scan import detect_disc_type
        result = detect_disc_type(str(dvd_folder))
        assert result == "dvd"

    def test_unknown_folder_raises(self, tmp_ingress):
        from arm.ripper.folder_scan import detect_disc_type
        empty = tmp_ingress / "empty"
        empty.mkdir()
        with pytest.raises(ValueError, match="No disc structure"):
            detect_disc_type(str(empty))

    def test_nonexistent_path_raises(self):
        from arm.ripper.folder_scan import detect_disc_type
        with pytest.raises(FileNotFoundError):
            detect_disc_type("/nonexistent/path")


class TestExtractMetadata:
    def test_bluray_title_from_xml(self, bdmv_folder):
        from arm.ripper.folder_scan import extract_metadata
        meta = extract_metadata(str(bdmv_folder), "bluray")
        assert meta["label"] == "TEST MOVIE"

    def test_bluray_missing_xml_returns_folder_name(self, bdmv_folder):
        from arm.ripper.folder_scan import extract_metadata
        os.remove(os.path.join(str(bdmv_folder), "BDMV", "META", "DL", "bdmt_eng.xml"))
        meta = extract_metadata(str(bdmv_folder), "bluray")
        assert meta["label"] == "Test Movie 2024"

    def test_dvd_uses_folder_name(self, dvd_folder):
        from arm.ripper.folder_scan import extract_metadata
        meta = extract_metadata(str(dvd_folder), "dvd")
        assert meta["label"] == "DVD Movie 2020"

    def test_stream_count_counted(self, bdmv_folder):
        from arm.ripper.folder_scan import extract_metadata
        meta = extract_metadata(str(bdmv_folder), "bluray")
        assert meta["stream_count"] == 1

    def test_folder_size_calculated(self, bdmv_folder):
        from arm.ripper.folder_scan import extract_metadata
        meta = extract_metadata(str(bdmv_folder), "bluray")
        assert meta["folder_size_bytes"] > 0


class TestValidateIngressPath:
    def test_valid_path_passes(self, tmp_ingress, bdmv_folder):
        from arm.ripper.folder_scan import validate_ingress_path
        validate_ingress_path(str(bdmv_folder), str(tmp_ingress))

    def test_traversal_blocked(self, tmp_ingress):
        from arm.ripper.folder_scan import validate_ingress_path
        with pytest.raises(ValueError, match="outside"):
            validate_ingress_path("/etc/passwd", str(tmp_ingress))

    def test_symlink_traversal_blocked(self, tmp_ingress, tmp_path):
        from arm.ripper.folder_scan import validate_ingress_path
        outside = tmp_path / "outside"
        outside.mkdir()
        link = tmp_ingress / "sneaky_link"
        link.symlink_to(outside)
        with pytest.raises(ValueError, match="outside"):
            validate_ingress_path(str(link), str(tmp_ingress))


class TestScanFolder:
    def test_scan_bluray_folder(self, bdmv_folder, tmp_ingress):
        from arm.ripper.folder_scan import scan_folder
        result = scan_folder(str(bdmv_folder), str(tmp_ingress))
        assert result["disc_type"] == "bluray"
        assert result["label"] == "TEST MOVIE"
        assert "title_suggestion" in result
        assert "folder_size_bytes" in result
        assert "stream_count" in result
