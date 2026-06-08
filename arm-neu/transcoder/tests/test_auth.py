"""
Tests for auth.py - API key authentication and config.py - settings validation.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError


# ─── APIKeyAuth ──────────────────────────────────────────────────────────────


class TestAPIKeyAuth:
    """Tests for APIKeyAuth class."""

    def _make_auth(self, api_keys="", require_auth=False):
        """Create an APIKeyAuth instance with patched settings."""
        with patch("auth.settings") as mock_settings:
            mock_settings.api_keys = api_keys
            mock_settings.require_api_auth = require_auth
            from auth import APIKeyAuth

            return APIKeyAuth()

    def test_parse_simple_keys(self):
        """Simple comma-separated keys default to admin role."""
        auth = self._make_auth("key1,key2,key3")
        assert auth.keys["key1"] == "admin"
        assert auth.keys["key2"] == "admin"
        assert auth.keys["key3"] == "admin"

    def test_parse_role_keys(self):
        """Role-prefixed keys should be parsed correctly."""
        auth = self._make_auth("admin:adminkey,readonly:readkey")
        assert auth.keys["adminkey"] == "admin"
        assert auth.keys["readkey"] == "readonly"

    def test_parse_mixed_keys(self):
        """Mixed format keys should be parsed correctly."""
        auth = self._make_auth("simplekey,admin:adminkey,readonly:readkey")
        assert auth.keys["simplekey"] == "admin"
        assert auth.keys["adminkey"] == "admin"
        assert auth.keys["readkey"] == "readonly"

    def test_empty_keys(self):
        """Empty API keys string should produce empty dict."""
        auth = self._make_auth("")
        assert auth.keys == {}

    def test_verify_key_auth_disabled(self):
        """When auth is disabled, any request should get admin role."""
        auth = self._make_auth("", require_auth=False)
        assert auth.verify_key(None) == "admin"
        assert auth.verify_key("anything") == "admin"

    def test_verify_key_valid(self):
        """Valid key should return its role."""
        auth = self._make_auth("admin:mykey", require_auth=True)
        assert auth.verify_key("mykey") == "admin"

    def test_verify_key_missing_raises_401(self):
        """Missing key when auth required should raise 401."""
        auth = self._make_auth("admin:mykey", require_auth=True)
        with pytest.raises(HTTPException) as exc_info:
            auth.verify_key(None)
        assert exc_info.value.status_code == 401

    def test_verify_key_invalid_raises_403(self):
        """Invalid key should raise 403."""
        auth = self._make_auth("admin:mykey", require_auth=True)
        with pytest.raises(HTTPException) as exc_info:
            auth.verify_key("wrongkey")
        assert exc_info.value.status_code == 403

    def test_require_admin_with_admin_key(self):
        """Admin key should pass require_admin."""
        auth = self._make_auth("admin:mykey", require_auth=True)
        assert auth.require_admin("mykey") == "admin"

    def test_require_admin_with_readonly_key_raises_403(self):
        """Readonly key should fail require_admin."""
        auth = self._make_auth("readonly:readkey", require_auth=True)
        with pytest.raises(HTTPException) as exc_info:
            auth.require_admin("readkey")
        assert exc_info.value.status_code == 403

    def test_require_admin_auth_disabled(self):
        """When auth disabled, require_admin should return admin."""
        auth = self._make_auth("", require_auth=False)
        assert auth.require_admin(None) == "admin"

    def test_key_with_colon_in_value(self):
        """Keys containing colons should split on first colon only."""
        auth = self._make_auth("admin:key:with:colons")
        assert auth.keys["key:with:colons"] == "admin"

    def test_whitespace_trimmed(self):
        """Whitespace around keys should be trimmed."""
        auth = self._make_auth("  key1 , admin:key2  ")
        assert "key1" in auth.keys
        assert "key2" in auth.keys


# ─── Webhook Secret Verification ─────────────────────────────────────────────


class TestWebhookSecret:
    """Tests for verify_webhook_secret."""

    def test_no_secret_configured_allows_all(self):
        """When no webhook secret is set, all requests pass."""
        with patch("auth.settings") as mock_settings:
            mock_settings.webhook_secret = ""
            from auth import verify_webhook_secret

            assert verify_webhook_secret(None) is True
            assert verify_webhook_secret("anything") is True

    def test_valid_secret(self):
        """Correct webhook secret should pass."""
        with patch("auth.settings") as mock_settings:
            mock_settings.webhook_secret = "mysecret"
            from auth import verify_webhook_secret

            assert verify_webhook_secret("mysecret") is True

    def test_missing_secret_raises_401(self):
        """Missing secret when required should raise 401."""
        with patch("auth.settings") as mock_settings:
            mock_settings.webhook_secret = "mysecret"
            from auth import verify_webhook_secret

            with pytest.raises(HTTPException) as exc_info:
                verify_webhook_secret(None)
            assert exc_info.value.status_code == 401

    def test_invalid_secret_raises_403(self):
        """Wrong webhook secret should raise 403."""
        with patch("auth.settings") as mock_settings:
            mock_settings.webhook_secret = "mysecret"
            from auth import verify_webhook_secret

            with pytest.raises(HTTPException) as exc_info:
                verify_webhook_secret("wrongsecret")
            assert exc_info.value.status_code == 403


# ─── Settings Validation ─────────────────────────────────────────────────────


class TestSettingsValidation:
    """Tests for config.py Settings validation."""

    def _make_settings(self, **overrides):
        """Create Settings with overrides."""
        from config import Settings

        defaults = {
            "raw_path": "/data/raw",
            "completed_path": "/data/completed",
            "require_api_auth": False,
        }
        defaults.update(overrides)
        return Settings(**defaults)

    def test_default_settings(self):
        """Default settings should be valid."""
        s = self._make_settings(log_level="INFO")
        assert s.selected_preset_slug == ""
        assert s.global_overrides == "{}"
        assert s.log_level == "INFO"

    def test_invalid_log_level(self):
        """Invalid log level should be rejected."""
        with pytest.raises(ValidationError):
            self._make_settings(log_level="VERBOSE")

    def test_log_level_case_insensitive(self):
        """Log level should be case-insensitive."""
        s = self._make_settings(log_level="debug")
        assert s.log_level == "DEBUG"

    def test_max_concurrent_bounds(self):
        """Max concurrent must be 1-10."""
        s = self._make_settings(max_concurrent=1)
        assert s.max_concurrent == 1
        s = self._make_settings(max_concurrent=10)
        assert s.max_concurrent == 10

        with pytest.raises(ValidationError):
            self._make_settings(max_concurrent=0)
        with pytest.raises(ValidationError):
            self._make_settings(max_concurrent=11)

    def test_stabilize_seconds_bounds(self):
        """Stabilize seconds must be 10-600."""
        with pytest.raises(ValidationError):
            self._make_settings(stabilize_seconds=9)
        with pytest.raises(ValidationError):
            self._make_settings(stabilize_seconds=601)

    def test_max_retry_count_bounds(self):
        """Max retry count must be 0-10."""
        s = self._make_settings(max_retry_count=0)
        assert s.max_retry_count == 0
        with pytest.raises(ValidationError):
            self._make_settings(max_retry_count=11)
