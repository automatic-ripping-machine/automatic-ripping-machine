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

    def test_dvd_stream_count(self, dvd_folder):
        """DVD stream count reads VIDEO_TS files (covers _count_streams dvd branch)."""
        from arm.ripper.folder_scan import extract_metadata
        meta = extract_metadata(str(dvd_folder), "dvd")
        # dvd_folder fixture creates VIDEO_TS.IFO and VTS_01_1.VOB
        assert meta["stream_count"] == 2

    def test_extract_metadata_dvd_title_year(self, dvd_folder):
        """DVD metadata extracts title and year from folder name 'DVD Movie 2020'."""
        from arm.ripper.folder_scan import extract_metadata
        meta = extract_metadata(str(dvd_folder), "dvd")
        assert meta["title_suggestion"] == "DVD Movie"
        assert meta["year_suggestion"] == "2020"


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

    def test_nonexistent_path_raises_file_not_found(self, tmp_ingress):
        """validate_ingress_path raises FileNotFoundError for path that is under
        ingress root but does not exist on disk (covers line 18)."""
        from arm.ripper.folder_scan import validate_ingress_path
        missing = os.path.join(str(tmp_ingress), "does_not_exist")
        with pytest.raises(FileNotFoundError, match="does not exist"):
            validate_ingress_path(missing, str(tmp_ingress))


class TestScanFolder:
    def test_scan_bluray_folder(self, bdmv_folder, tmp_ingress):
        from arm.ripper.folder_scan import scan_folder
        result = scan_folder(str(bdmv_folder), str(tmp_ingress))
        assert result["disc_type"] == "bluray"
        assert result["label"] == "TEST MOVIE"
        assert "title_suggestion" in result
        assert "folder_size_bytes" in result
        assert "stream_count" in result


class TestParseTitleYear:
    """Test _parse_title_year internal function for various formats."""

    def test_paren_year_format(self, tmp_path):
        """'Title (2024)' folder name extracts title and year (lines 88-90)."""
        from arm.ripper.folder_scan import _parse_title_year
        folder = tmp_path / "My Movie (2024)"
        folder.mkdir()
        title, year = _parse_title_year("My Movie (2024)", str(folder))
        assert title == "My Movie"
        assert year == "2024"

    def test_space_year_format(self, tmp_path):
        """'Title 2024' folder name extracts title and year (lines 95-98)."""
        from arm.ripper.folder_scan import _parse_title_year
        folder = tmp_path / "My Movie 2024"
        folder.mkdir()
        title, year = _parse_title_year("My Movie 2024", str(folder))
        assert title == "My Movie"
        assert year == "2024"

    def test_no_year_returns_cleaned_label(self, tmp_path):
        """Folder with no year returns cleaned label and None (lines 100-101)."""
        from arm.ripper.folder_scan import _parse_title_year
        folder = tmp_path / "some_movie"
        folder.mkdir()
        title, year = _parse_title_year("some_movie", str(folder))
        assert title == "some movie"
        assert year is None

    def test_underscores_cleaned(self, tmp_path):
        """Underscores and dots in label are replaced with spaces."""
        from arm.ripper.folder_scan import _parse_title_year
        folder = tmp_path / "My.Great.Movie"
        folder.mkdir()
        title, year = _parse_title_year("My.Great.Movie", str(folder))
        assert title == "My Great Movie"
        assert year is None

    def test_year_before_1900_not_matched(self, tmp_path):
        """Year < 1900 is not treated as a year."""
        from arm.ripper.folder_scan import _parse_title_year
        folder = tmp_path / "Movie 1234"
        folder.mkdir()
        title, year = _parse_title_year("Movie 1234", str(folder))
        # 1234 < 1900, so no year match — falls through to cleaned label
        assert year is None

    def test_standalone_year_only_not_matched(self, tmp_path):
        """A folder name that is just a year has no title prefix, so no match."""
        from arm.ripper.folder_scan import _parse_title_year
        folder = tmp_path / "2024"
        folder.mkdir()
        title, year = _parse_title_year("2024", str(folder))
        # parts[:0] is empty, so title is "" which is falsy — no match
        assert year is None


class TestLabelFromBlurayXml:
    """Test _label_from_bluray_xml edge cases."""

    def test_malformed_xml_returns_none(self, bdmv_folder):
        """Malformed XML triggers the except branch (lines 77-79)."""
        from arm.ripper.folder_scan import _label_from_bluray_xml
        xml_path = os.path.join(str(bdmv_folder), "BDMV", "META", "DL", "bdmt_eng.xml")
        with open(xml_path, "w") as f:
            f.write("NOT VALID XML {{{{ <broken>")
        result = _label_from_bluray_xml(str(bdmv_folder))
        assert result is None


class TestCalculateFolderSize:
    """Test _calculate_folder_size edge cases."""

    def test_oserror_skipped(self, tmp_path):
        """Files that cause OSError on getsize are silently skipped (lines 110-111)."""
        from arm.ripper.folder_scan import _calculate_folder_size
        # Create a normal file
        good = tmp_path / "good.bin"
        good.write_bytes(b"\x00" * 100)
        # Patch os.path.getsize to raise OSError for one specific file
        orig_getsize = os.path.getsize

        def patched_getsize(path):
            if "good.bin" in path:
                raise OSError("permission denied")
            return orig_getsize(path)

        with patch("arm.ripper.folder_scan.os.path.getsize", side_effect=patched_getsize):
            size = _calculate_folder_size(str(tmp_path))
        assert size == 0  # the only file raised OSError

    def test_nested_dirs(self, tmp_path):
        """Nested directories are walked correctly."""
        from arm.ripper.folder_scan import _calculate_folder_size
        sub = tmp_path / "a" / "b"
        sub.mkdir(parents=True)
        (sub / "file.bin").write_bytes(b"\x00" * 256)
        (tmp_path / "top.bin").write_bytes(b"\x00" * 128)
        size = _calculate_folder_size(str(tmp_path))
        assert size == 384


class TestCountStreams:
    """Test _count_streams for various disc types."""

    def test_dvd_counts_video_ts_files(self, dvd_folder):
        """DVD type counts files in VIDEO_TS directory (lines 121, 123)."""
        from arm.ripper.folder_scan import _count_streams
        count = _count_streams(str(dvd_folder), "dvd")
        assert count == 2  # VIDEO_TS.IFO + VTS_01_1.VOB

    def test_unknown_type_returns_zero(self, tmp_path):
        """Unknown disc type returns 0 (line 121 else branch)."""
        from arm.ripper.folder_scan import _count_streams
        assert _count_streams(str(tmp_path), "music") == 0

    def test_missing_stream_dir_returns_zero(self, tmp_path):
        """Missing stream directory returns 0."""
        from arm.ripper.folder_scan import _count_streams
        assert _count_streams(str(tmp_path), "bluray") == 0
