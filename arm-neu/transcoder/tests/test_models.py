"""
Tests for models.py - Pydantic validation and data models.
"""

import pytest
from pydantic import ValidationError

from arm_contracts import WebhookPayload
from models import JobStatus, TranscodeJob, TranscodeJobDB


# ─── WebhookPayload Validation ──────────────────────────────────────────────


class TestWebhookPayload:
    """Tests for WebhookPayload Pydantic model validation."""

    def test_valid_minimal_payload(self):
        """Minimal valid payload with title and job_id."""
        payload = WebhookPayload(title="Movie Rip Complete", job_id=1)
        assert payload.title == "Movie Rip Complete"
        assert payload.job_id == 1
        assert payload.body is None
        assert payload.input_path is None
        assert payload.output_path is None

    def test_valid_full_payload(self):
        """Full payload with all fields."""
        payload = WebhookPayload(
            title="Movie Title",
            body="Rip of Movie Title (2024) complete",
            input_path="movies/Movie Title (2024)",
            output_path="Movies/0.Rips/Movie Title (2024)",
            job_id=123,
            status="success",
            type="info",
        )
        assert payload.title == "Movie Title"
        assert payload.job_id == 123
        assert payload.status == "success"

    def test_empty_title_rejected(self):
        """Empty title must be rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="", job_id=1)

    def test_whitespace_only_title_rejected(self):
        """Whitespace-only title must be rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="   ", job_id=1)

    def test_title_max_length(self):
        """Title over 500 chars must be rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="A" * 501, job_id=1)

    def test_title_at_max_length(self):
        """Title at exactly 500 chars should be accepted."""
        payload = WebhookPayload(title="A" * 500, job_id=1)
        assert len(payload.title) == 500

    def test_title_control_characters_stripped(self):
        """Control characters should be removed from title."""
        payload = WebhookPayload(title="Movie\x01\x02\x03Title", job_id=1)
        assert payload.title == "MovieTitle"

    def test_body_max_length(self):
        """Body over 2000 chars must be rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", job_id=1, body="B" * 2001)

    def test_body_preserves_newlines(self):
        """Newlines in body should be preserved."""
        payload = WebhookPayload(title="Test", job_id=1, body="Line 1\nLine 2\n")
        assert "\n" in payload.body

    def test_body_preserves_tabs(self):
        """Tabs in body should be preserved."""
        payload = WebhookPayload(title="Test", job_id=1, body="Col1\tCol2")
        assert "\t" in payload.body

    def test_body_control_chars_stripped(self):
        """Control characters (except newline/tab) should be removed from body."""
        payload = WebhookPayload(title="Test", job_id=1, body="Clean\x01\x02text")
        assert "\x01" not in payload.body
        assert "\x02" not in payload.body

    def test_input_path_max_length(self):
        """input_path over 1000 chars must be rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", job_id=1, input_path="p" * 1001)

    def test_input_path_null_bytes_stripped(self):
        """Null bytes should be removed from input_path."""
        payload = WebhookPayload(title="Test", job_id=1, input_path="movie\x00title")
        assert "\x00" not in payload.input_path

    def test_input_path_control_chars_stripped(self):
        """Control characters should be removed from input_path."""
        payload = WebhookPayload(title="Test", job_id=1, input_path="movie\x01title")
        assert "\x01" not in payload.input_path

    def test_input_path_rejects_absolute(self):
        """Absolute paths are rejected by the contracts validator."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", job_id=1, input_path="/abs/path")

    def test_output_path_rejects_dotdot(self):
        """`..` segments are rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", job_id=1, output_path="Movies/../etc")

    def test_job_id_required(self):
        """job_id is required."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test")

    def test_job_id_coerced_to_int(self):
        """job_id string should be coerced to int."""
        payload = WebhookPayload(title="Test", job_id="42")
        assert payload.job_id == 42
        assert isinstance(payload.job_id, int)

    def test_job_id_accepts_int(self):
        """job_id as int should be accepted directly."""
        payload = WebhookPayload(title="Test", job_id=42)
        assert payload.job_id == 42

    def test_job_id_rejects_non_numeric(self):
        """job_id with non-numeric value must be rejected."""
        with pytest.raises(ValidationError, match="valid integer"):
            WebhookPayload(title="Test", job_id="abc")

    def test_job_id_rejects_none(self):
        """job_id=None must be rejected (it's required)."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", job_id=None)

    def test_status_max_length(self):
        """Status over 50 chars must be rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", job_id=1, status="s" * 51)

    def test_type_rejects_non_enum_value(self):
        """type is a WebhookEventType enum (contracts v0.7.0); only 'info' or None validates."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", job_id=1, type="bogus_event_type")

    def test_type_accepts_info(self):
        """type='info' is the only currently-defined WebhookEventType member."""
        payload = WebhookPayload(title="Test", job_id=1, type="info")
        assert payload.type == "info"

    def test_none_optional_fields(self):
        """All optional fields should accept None."""
        payload = WebhookPayload(
            title="Test",
            job_id=1,
            body=None,
            message=None,
            input_path=None,
            output_path=None,
            status=None,
            type=None,
        )
        assert payload.body is None
        assert payload.message is None
        assert payload.input_path is None
        assert payload.output_path is None

    # ─── Multi-title disc fields ────────────────────────────────────────────

    def test_multi_title_default_none(self):
        """multi_title should default to None when not provided."""
        payload = WebhookPayload(title="Test", job_id=1)
        assert payload.multi_title is None

    def test_multi_title_true(self):
        """multi_title=True should be accepted."""
        payload = WebhookPayload(title="Test", job_id=1, multi_title=True)
        assert payload.multi_title is True

    def test_multi_title_false(self):
        """multi_title=False should be accepted."""
        payload = WebhookPayload(title="Test", job_id=1, multi_title=False)
        assert payload.multi_title is False

    def test_tracks_default_none(self):
        """tracks should default to None when not provided."""
        payload = WebhookPayload(title="Test", job_id=1)
        assert payload.tracks is None

    def test_tracks_empty_list(self):
        """tracks=[] should be accepted."""
        payload = WebhookPayload(title="Test", job_id=1, tracks=[])
        assert payload.tracks == []

    def test_tracks_with_metadata(self):
        """tracks with per-track metadata dicts should be accepted."""
        tracks = [
            {"track_number": "1", "filename": "t01.mkv", "title": "Episode 1", "year": "2024"},
            {"track_number": "2", "filename": "t02.mkv", "title": "Episode 2", "year": "2024"},
        ]
        payload = WebhookPayload(title="Test", job_id=1, multi_title=True, tracks=tracks)
        assert payload.multi_title is True
        assert len(payload.tracks) == 2
        assert payload.tracks[0].filename == "t01.mkv"
        assert payload.tracks[1].track_number == "2"

    def test_multi_title_full_payload(self):
        """Full payload with multi_title and tracks alongside standard fields."""
        tracks = [
            {"track_number": "1", "filename": "main.mkv", "title": "Movie", "video_type": "movie"},
        ]
        payload = WebhookPayload(
            title="ARM notification",
            body="Rip of Movie (2024) complete",
            input_path="movies/Movie (2024)",
            output_path="Movies/0.Rips/Movie (2024)",
            job_id=42,
            status="success",
            type="info",
            multi_title=True,
            tracks=tracks,
        )
        assert payload.multi_title is True
        assert len(payload.tracks) == 1
        assert payload.title == "ARM notification"
        assert payload.job_id == 42

    # ─── Apprise message field support ──────────────────────────────────────

    def test_apprise_message_field_accepted(self):
        """Apprise json:// sends 'message' instead of 'body'."""
        payload = WebhookPayload(
            title="ARM notification",
            job_id=1,
            message="Movie Title (2024) rip complete. Starting transcode.",
            type="info",
        )
        assert payload.message == "Movie Title (2024) rip complete. Starting transcode."
        assert payload.body is None

    def test_effective_body_prefers_body(self):
        """effective_body should prefer 'body' over 'message' when both present."""
        payload = WebhookPayload(
            title="Test",
            job_id=1,
            body="from body",
            message="from message",
        )
        assert payload.effective_body == "from body"

    def test_effective_body_falls_back_to_message(self):
        """effective_body should return 'message' when 'body' is None."""
        payload = WebhookPayload(
            title="Test",
            job_id=1,
            message="from message",
        )
        assert payload.effective_body == "from message"

    def test_effective_body_none_when_both_empty(self):
        """effective_body should return None when both fields are empty."""
        payload = WebhookPayload(title="Test", job_id=1)
        assert payload.effective_body is None

    def test_apprise_full_payload(self):
        """Apprise json:// sends version, title, message, type."""
        payload = WebhookPayload(
            title="ARM notification",
            job_id=1,
            message="Movie (2024) rip complete. Starting transcode.",
            type="info",
        )
        assert payload.effective_body == "Movie (2024) rip complete. Starting transcode."

    def test_message_max_length(self):
        """Message over 2000 chars must be rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", job_id=1, message="M" * 2001)

    def test_message_control_chars_stripped(self):
        """Control characters should be stripped from message field."""
        payload = WebhookPayload(title="Test", job_id=1, message="Clean\x01\x02text")
        assert "\x01" not in payload.message
        assert "\x02" not in payload.message


# ─── JobStatus Enum ──────────────────────────────────────────────────────────


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_all_statuses_exist(self):
        """All expected statuses should exist."""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.PROCESSING == "processing"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"

    def test_status_is_string(self):
        """JobStatus values should be strings."""
        for status in JobStatus:
            assert isinstance(status.value, str)


# ─── TranscodeJob Model ─────────────────────────────────────────────────────


class TestTranscodeJob:
    """Tests for TranscodeJob Pydantic model."""

    def test_create_job(self):
        """Should create a job with required fields."""
        job = TranscodeJob(id=1, title="Movie", source_path="/data/raw/movie")
        assert job.title == "Movie"
        assert job.source_path == "/data/raw/movie"
        assert job.id == 1

    def test_create_job_with_all_fields(self):
        """Should create a job with all fields."""
        job = TranscodeJob(
            id=42,
            title="Movie",
            source_path="/data/raw/movie",
        )
        assert job.id == 42

    def test_from_attributes_config(self):
        """Should support from_attributes for ORM integration."""
        assert TranscodeJob.model_config.get("from_attributes") is True


# ─── TranscodeJobDB Model ───────────────────────────────────────────────────


class TestTranscodeJobDB:
    """Tests for TranscodeJobDB schema changes."""

    def test_no_autoincrement(self):
        """TranscodeJobDB.id is not auto-incrementing — it's the ARM job ID."""
        col = TranscodeJobDB.__table__.columns["id"]
        assert col.primary_key
        assert col.autoincrement == "auto" or col.autoincrement is False

    def test_no_arm_job_id_column(self):
        """arm_job_id column has been removed."""
        assert "arm_job_id" not in TranscodeJobDB.__table__.columns
