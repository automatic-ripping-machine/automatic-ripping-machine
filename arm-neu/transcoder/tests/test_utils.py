"""
Tests for utils.py - PathValidator, CommandValidator, and utility functions.
"""

import pytest

from utils import (
    PathValidator,
    CommandValidator,
    get_disk_space_info,
    check_sufficient_disk_space,
    estimate_transcode_size,
    clean_title_for_filesystem,
    sanitize_log_message,
)


# ─── PathValidator ───────────────────────────────────────────────────────────


class TestPathValidator:
    """Tests for PathValidator - path traversal prevention."""

    def test_valid_relative_path(self, path_validator, tmp_dirs):
        """A simple relative path should resolve within the base."""
        subdir = tmp_dirs["raw"] / "movie"
        subdir.mkdir()
        result = path_validator.validate("movie")
        assert result == subdir.resolve()

    def test_valid_nested_path(self, path_validator, tmp_dirs):
        """Nested relative paths should work."""
        nested = tmp_dirs["raw"] / "movies" / "2024"
        nested.mkdir(parents=True)
        result = path_validator.validate("movies/2024")
        assert result == nested.resolve()

    def test_empty_path_rejected(self, path_validator):
        """Empty paths must be rejected."""
        with pytest.raises(ValueError, match="empty"):
            path_validator.validate("")

    def test_traversal_dotdot_slash(self, path_validator):
        """Paths with ../ must be rejected."""
        with pytest.raises(ValueError, match="dangerous"):
            path_validator.validate("../etc/passwd")

    def test_traversal_dotdot_backslash(self, path_validator):
        """Paths with ..\\ must be rejected."""
        with pytest.raises(ValueError, match="dangerous"):
            path_validator.validate("..\\windows\\system32")

    def test_traversal_tilde(self, path_validator):
        """Paths with ~ must be rejected."""
        with pytest.raises(ValueError, match="dangerous"):
            path_validator.validate("~/secret")

    def test_traversal_env_variable(self, path_validator):
        """Paths with ${} must be rejected."""
        with pytest.raises(ValueError, match="dangerous"):
            path_validator.validate("${HOME}/secret")

    def test_traversal_env_dollar(self, path_validator):
        """Paths with $ENV must be rejected."""
        with pytest.raises(ValueError, match="dangerous"):
            path_validator.validate("$ENV/secret")

    def test_absolute_path_rejected(self, path_validator):
        """Absolute paths must be rejected."""
        with pytest.raises(ValueError, match="Absolute"):
            path_validator.validate("/etc/passwd")

    def test_null_bytes_stripped(self, path_validator, tmp_dirs):
        """Null bytes should be removed from paths."""
        subdir = tmp_dirs["raw"] / "movie"
        subdir.mkdir()
        result = path_validator.validate("mov\x00ie")
        assert result == subdir.resolve()

    def test_path_outside_allowed_bases(self, tmp_dirs):
        """Paths resolving outside allowed directories must be rejected."""
        validator = PathValidator([str(tmp_dirs["raw"])])
        with pytest.raises(ValueError):
            validator.validate("../../etc/passwd")

    def test_validate_existing_path(self, path_validator, tmp_dirs):
        """validate_existing should work for existing paths."""
        existing = tmp_dirs["raw"] / "existing_dir"
        existing.mkdir()
        result = path_validator.validate_existing("existing_dir")
        assert result == existing.resolve()

    def test_validate_existing_nonexistent(self, path_validator):
        """validate_existing should reject non-existent paths."""
        with pytest.raises(ValueError, match="does not exist"):
            path_validator.validate_existing("no_such_path_12345")

    def test_multiple_allowed_bases(self, tmp_dirs):
        """Paths should resolve against any of the allowed bases."""
        validator = PathValidator([str(tmp_dirs["raw"]), str(tmp_dirs["completed"])])

        raw_dir = tmp_dirs["raw"] / "movie1"
        raw_dir.mkdir()
        result = validator.validate("movie1")
        assert result == raw_dir.resolve()

    def test_symlink_within_base_allowed(self, tmp_dirs):
        """Symlinks that stay within the base should be allowed."""
        validator = PathValidator([str(tmp_dirs["raw"])])
        target = tmp_dirs["raw"] / "real_dir"
        target.mkdir()
        link = tmp_dirs["raw"] / "link_dir"
        link.symlink_to(target)

        result = validator.validate("link_dir")
        assert result == target.resolve()


# ─── CommandValidator ────────────────────────────────────────────────────────


class TestCommandValidator:
    """Tests for CommandValidator - subprocess argument sanitization."""

    def test_valid_audio_encoders(self):
        """All valid audio encoders should be accepted."""
        valid = ["copy", "aac", "ac3", "eac3", "flac", "mp3"]
        for encoder in valid:
            assert CommandValidator.validate_audio_encoder(encoder) == encoder

    def test_invalid_audio_encoder(self):
        """Invalid audio encoder names must be rejected."""
        with pytest.raises(ValueError, match="Invalid audio encoder"):
            CommandValidator.validate_audio_encoder("bad_codec")

    def test_valid_subtitle_modes(self):
        """All valid subtitle modes should be accepted."""
        for mode in ["all", "none", "first"]:
            assert CommandValidator.validate_subtitle_mode(mode) == mode

    def test_invalid_subtitle_mode(self):
        """Invalid subtitle modes must be rejected."""
        with pytest.raises(ValueError, match="Invalid subtitle mode"):
            CommandValidator.validate_subtitle_mode("inject")

    def test_valid_preset_name(self):
        """Valid preset names should be accepted."""
        assert CommandValidator.validate_preset_name("NVENC H.265 1080p") == "NVENC H.265 1080p"
        assert CommandValidator.validate_preset_name("my-preset_v2") == "my-preset_v2"

    def test_preset_name_special_chars_rejected(self):
        """Preset names with special characters must be rejected."""
        with pytest.raises(ValueError, match="Invalid preset name"):
            CommandValidator.validate_preset_name("preset; rm -rf /")

    def test_preset_name_backtick_rejected(self):
        """Preset names with backticks must be rejected."""
        with pytest.raises(ValueError):
            CommandValidator.validate_preset_name("preset`whoami`")

    def test_preset_name_too_long(self):
        """Preset names over 100 chars must be rejected."""
        with pytest.raises(ValueError, match="too long"):
            CommandValidator.validate_preset_name("a" * 101)

    def test_preset_name_max_length(self):
        """Preset name at exactly 100 chars should be accepted."""
        name = "a" * 100
        assert CommandValidator.validate_preset_name(name) == name


# ─── Disk Space Utilities ────────────────────────────────────────────────────


class TestDiskSpaceUtils:
    """Tests for disk space utility functions."""

    def test_get_disk_space_info(self, tmp_path):
        """Should return disk space info dict."""
        info = get_disk_space_info(str(tmp_path))
        assert "total_bytes" in info
        assert "used_bytes" in info
        assert "free_bytes" in info
        assert "free_gb" in info
        assert info["total_bytes"] > 0
        assert info["free_gb"] > 0

    def test_get_disk_space_info_invalid_path(self):
        """Should return zeros for invalid path."""
        info = get_disk_space_info("/nonexistent/path/abc123")
        assert info["total_bytes"] == 0
        assert info["free_gb"] == 0

    def test_check_sufficient_disk_space_enough(self, tmp_path):
        """Should return True when there's enough space."""
        sufficient, msg = check_sufficient_disk_space(
            str(tmp_path), required_bytes=1024, minimum_free_gb=0.001
        )
        assert sufficient is True
        assert "Sufficient" in msg

    def test_check_sufficient_disk_space_minimum_free(self, tmp_path):
        """Should fail when minimum free space not met."""
        sufficient, msg = check_sufficient_disk_space(
            str(tmp_path), required_bytes=1024, minimum_free_gb=999999
        )
        assert sufficient is False
        assert "Insufficient" in msg

    def test_check_sufficient_disk_space_required_too_high(self, tmp_path):
        """Should fail when required bytes exceed free space."""
        sufficient, msg = check_sufficient_disk_space(
            str(tmp_path), required_bytes=10**18, minimum_free_gb=0.001
        )
        assert sufficient is False

    def test_estimate_transcode_size(self):
        """Should estimate output at 60% of input."""
        assert estimate_transcode_size(1000) == 600
        assert estimate_transcode_size(0) == 0
        assert estimate_transcode_size(1_000_000) == 600_000


# ─── Filesystem Title Cleaning ───────────────────────────────────────────────


class TestCleanTitle:
    """Tests for clean_title_for_filesystem."""

    def test_normal_title(self):
        """Normal titles should pass through."""
        assert clean_title_for_filesystem("The Matrix") == "The Matrix"

    def test_special_characters_removed(self):
        """Filesystem-invalid characters should be removed."""
        result = clean_title_for_filesystem('Movie: "Subtitle" <2024>')
        assert ":" not in result
        assert '"' not in result
        assert "<" not in result
        assert ">" not in result

    def test_multiple_spaces_collapsed(self):
        """Multiple spaces should collapse to single space."""
        assert clean_title_for_filesystem("Too   Many   Spaces") == "Too Many Spaces"

    def test_empty_becomes_untitled(self):
        """Empty/whitespace-only titles should become 'untitled'."""
        assert clean_title_for_filesystem("") == "untitled"
        assert clean_title_for_filesystem("   ") == "untitled"

    def test_control_characters_removed(self):
        """Control characters should be removed."""
        result = clean_title_for_filesystem("Movie\x01\x02Title")
        assert result == "MovieTitle"

    def test_long_title_truncated(self):
        """Titles over 200 chars should be truncated."""
        long_title = "A" * 250
        result = clean_title_for_filesystem(long_title)
        assert len(result) <= 200

    def test_pipe_removed(self):
        """Pipe character should be removed."""
        result = clean_title_for_filesystem("Movie | Part 1")
        assert "|" not in result

    def test_question_mark_removed(self):
        """Question mark should be removed."""
        result = clean_title_for_filesystem("What If?")
        assert "?" not in result

    def test_backslash_removed(self):
        """Backslash should be removed."""
        result = clean_title_for_filesystem("path\\to\\file")
        assert "\\" not in result


# ─── Log Sanitization ────────────────────────────────────────────────────────


class TestSanitizeLogMessage:
    """Tests for sanitize_log_message."""

    def test_masks_password(self):
        """Should mask password values."""
        result = sanitize_log_message("password=secret123")
        assert "secret123" not in result
        assert "***" in result

    def test_masks_api_key(self):
        """Should mask api_key values."""
        result = sanitize_log_message("api_key=abc123def")
        assert "abc123def" not in result
        assert "***" in result

    def test_masks_token(self):
        """Should mask token values."""
        result = sanitize_log_message('token: "mytoken123"')
        assert "mytoken123" not in result

    def test_preserves_normal_text(self):
        """Normal log messages should not be modified."""
        msg = "Processing job 42 for title Movie"
        assert sanitize_log_message(msg) == msg

    def test_custom_sensitive_keys(self):
        """Should support custom sensitive key list."""
        result = sanitize_log_message(
            "database_url=postgres://secret",
            sensitive_keys=["database_url"],
        )
        assert "postgres://secret" not in result

    def test_case_insensitive_masking(self):
        """Key matching should be case-insensitive."""
        result = sanitize_log_message("PASSWORD=mysecret")
        assert "mysecret" not in result
