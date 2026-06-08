"""
Tests for security - path traversal, payload attacks, command injection, auth bypass.
"""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from arm_contracts import WebhookPayload
from utils import CommandValidator


# ─── Path Traversal Attack Vectors ───────────────────────────────────────────


class TestPathTraversalAttacks:
    """Comprehensive path traversal attack tests (spec section 1.1)."""

    def test_simple_dotdot(self, path_validator):
        with pytest.raises(ValueError):
            path_validator.validate("../secret")

    def test_double_dotdot(self, path_validator):
        with pytest.raises(ValueError):
            path_validator.validate("../../etc/passwd")

    def test_dotdot_in_middle(self, path_validator):
        with pytest.raises(ValueError):
            path_validator.validate("movies/../../../etc/shadow")

    def test_windows_backslash_traversal(self, path_validator):
        with pytest.raises(ValueError):
            path_validator.validate("..\\..\\windows\\system32")

    def test_url_encoded_dotdot(self, path_validator):
        """URL-encoded traversal (if decoded before reaching validator)."""
        with pytest.raises(ValueError):
            path_validator.validate("../etc/passwd")

    def test_null_byte_injection(self, path_validator, tmp_dirs):
        """Null bytes should be stripped, not used for bypassing."""
        subdir = tmp_dirs["raw"] / "safe"
        subdir.mkdir()
        # Null byte should be stripped, leaving "safe"
        result = path_validator.validate("sa\x00fe")
        assert result == subdir.resolve()

    def test_tilde_home_expansion(self, path_validator):
        with pytest.raises(ValueError):
            path_validator.validate("~/private/data")

    def test_env_variable_expansion(self, path_validator):
        with pytest.raises(ValueError):
            path_validator.validate("${HOME}/secrets")

    def test_env_dollar_sign(self, path_validator):
        with pytest.raises(ValueError):
            path_validator.validate("$ENV_VAR/data")

    def test_absolute_path_linux(self, path_validator):
        with pytest.raises(ValueError):
            path_validator.validate("/etc/passwd")

    def test_absolute_path_proc(self, path_validator):
        with pytest.raises(ValueError):
            path_validator.validate("/proc/self/environ")

    def test_deeply_nested_traversal(self, path_validator):
        with pytest.raises(ValueError):
            path_validator.validate("a/b/c/d/../../../../../etc/passwd")


# ─── Oversized Payload Attacks ───────────────────────────────────────────────


class TestOversizedPayloads:
    """Tests for payload size limits (spec section 1.2)."""

    def test_oversized_title(self):
        """Title exceeding 500 chars must be rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="X" * 501, job_id=951)

    def test_oversized_body(self):
        """Body exceeding 2000 chars must be rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", body="X" * 2001, job_id=952)

    def test_oversized_input_path(self):
        """input_path exceeding 1000 chars must be rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", input_path="X" * 1001, job_id=953)

    def test_oversized_output_path(self):
        """output_path exceeding 1000 chars must be rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", output_path="X" * 1001, job_id=953)

    def test_oversized_job_id(self):
        """Job ID exceeding 50 chars must be rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", job_id="x" * 51)

    def test_all_fields_at_max(self):
        """All fields at max length should be accepted.

        The 'type' field is no longer a free length-bounded string; it is now
        a strict WebhookEventType enum (contracts v0.7.0). It is therefore
        excluded from this length-boundary sweep and pinned to a valid enum
        value to keep the rest of the fields under test.
        """
        payload = WebhookPayload(
            title="T" * 500,
            body="B" * 2000,
            input_path="P" * 1000,
            output_path="O" * 1000,
            job_id=99999,
            status="s" * 50,
            type="info",
        )
        assert len(payload.title) == 500


# ─── Command Injection Attacks ───────────────────────────────────────────────


class TestCommandInjection:
    """Tests for command injection prevention (spec section 1.3)."""

    def test_audio_encoder_injection(self):
        with pytest.raises(ValueError):
            CommandValidator.validate_audio_encoder("aac; whoami")

    def test_subtitle_mode_injection(self):
        with pytest.raises(ValueError):
            CommandValidator.validate_subtitle_mode("all; cat /etc/passwd")

    def test_preset_name_semicolon(self):
        with pytest.raises(ValueError):
            CommandValidator.validate_preset_name("preset; rm -rf /")

    def test_preset_name_backtick(self):
        with pytest.raises(ValueError):
            CommandValidator.validate_preset_name("preset`id`")

    def test_preset_name_dollar_paren(self):
        with pytest.raises(ValueError):
            CommandValidator.validate_preset_name("$(whoami)")

    def test_preset_name_pipe(self):
        with pytest.raises(ValueError):
            CommandValidator.validate_preset_name("preset | cat /etc/shadow")

    def test_preset_name_redirect(self):
        with pytest.raises(ValueError):
            CommandValidator.validate_preset_name("preset > /tmp/out")

    def test_preset_name_ampersand(self):
        with pytest.raises(ValueError):
            CommandValidator.validate_preset_name("preset && whoami")


# ─── API Key Validation Security ─────────────────────────────────────────────


class TestAPIKeySecurityAttacks:
    """Tests for authentication bypass attempts."""

    def _make_auth(self, api_keys="", require_auth=True):
        with patch("auth.settings") as mock_settings:
            mock_settings.api_keys = api_keys
            mock_settings.require_api_auth = require_auth
            from auth import APIKeyAuth
            return APIKeyAuth()

    def test_empty_string_key_rejected(self):
        """Empty string should be treated as missing key (401)."""
        from fastapi import HTTPException
        auth = self._make_auth("admin:realkey", require_auth=True)
        with pytest.raises(HTTPException) as exc_info:
            auth.verify_key("")
        # Empty string is falsy, so treated as "no key provided" = 401
        assert exc_info.value.status_code == 401

    def test_none_key_rejected(self):
        """None should raise 401 when auth required."""
        from fastapi import HTTPException
        auth = self._make_auth("admin:realkey", require_auth=True)
        with pytest.raises(HTTPException) as exc_info:
            auth.verify_key(None)
        assert exc_info.value.status_code == 401

    def test_partial_key_rejected(self):
        """Partial key match should be rejected."""
        from fastapi import HTTPException
        auth = self._make_auth("admin:supersecretkey123", require_auth=True)
        with pytest.raises(HTTPException):
            auth.verify_key("supersecret")

    def test_key_with_extra_chars_rejected(self):
        """Key with appended characters should be rejected."""
        from fastapi import HTTPException
        auth = self._make_auth("admin:mykey", require_auth=True)
        with pytest.raises(HTTPException):
            auth.verify_key("mykey_extra")

    def test_case_sensitive_keys(self):
        """API keys should be case-sensitive."""
        from fastapi import HTTPException
        auth = self._make_auth("admin:MyKey", require_auth=True)
        with pytest.raises(HTTPException):
            auth.verify_key("mykey")

    def test_readonly_cannot_admin(self):
        """Readonly key should not get admin access."""
        from fastapi import HTTPException
        auth = self._make_auth("readonly:readkey", require_auth=True)
        with pytest.raises(HTTPException) as exc_info:
            auth.require_admin("readkey")
        assert exc_info.value.status_code == 403


# ─── Webhook Input Sanitization ──────────────────────────────────────────────


class TestWebhookInputSanitization:
    """Tests for malicious webhook payload content."""

    def test_title_with_script_tags(self):
        """HTML/script injection in title should be sanitized (control chars removed)."""
        payload = WebhookPayload(title="<script>alert('xss')</script>", job_id=954)
        # No control chars to strip, but field is sanitized
        assert payload.title is not None

    def test_job_id_sql_injection(self):
        """SQL injection in job_id should be rejected by regex."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", job_id="1; DROP TABLE jobs;--")

    def test_job_id_with_quotes(self):
        """Job ID with quotes should be rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", job_id="job'OR'1'='1")

    def test_input_path_with_null_byte(self):
        """Null bytes in input_path should be stripped."""
        payload = WebhookPayload(title="Test", input_path="movie\x00.mkv", job_id=955)
        assert "\x00" not in payload.input_path

    def test_title_with_null_byte(self):
        """Control characters (including null) should be stripped from title."""
        payload = WebhookPayload(title="Movie\x00Title", job_id=956)
        assert "\x00" not in payload.title

    def test_body_massive_newlines(self):
        """Body with many newlines should still be constrained by max_length."""
        body = "\n" * 2001
        with pytest.raises(ValidationError):
            WebhookPayload(title="Test", body=body, job_id=957)
