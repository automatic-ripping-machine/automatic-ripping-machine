"""Tests for the webhook channel sender — HMAC signing, headers, retry semantics."""
import hashlib
import hmac
import json
from unittest.mock import patch, MagicMock

import pytest


def _build_payload_dict():
    """Minimal valid OutboundWebhookPayload dict."""
    from datetime import datetime, timezone
    from uuid import uuid4
    return {
        "schema_version": 1,
        "event": {
            "event_key": "job.started",
            "event_id": str(uuid4()),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "job_id": 1,
            "job_title": "X",
            "job_disc_type": "dvd",
            "job_imdb_id": None,
            "drive_mount": "/dev/sr0",
        },
        "title": "T",
        "body": "B",
        "channel": {"id": 1, "name": "n", "type": "webhook"},
        "arm_instance_name": "hifi",
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


def test_webhook_send_no_secret_no_signature_header():
    from arm.notifications.channels.webhook import send_webhook

    fake_resp = MagicMock(status_code=200, text="ok")
    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.post.return_value = fake_resp
    with patch("arm.notifications.channels.webhook.httpx.Client",
               return_value=fake_client):
        ok, error = send_webhook(
            url="https://example.com/hook",
            payload_dict=_build_payload_dict(),
            shared_secret=None,
            headers=None,
        )
    assert ok is True
    assert error is None
    call_kwargs = fake_client.post.call_args.kwargs
    assert "X-ARM-Signature" not in (call_kwargs.get("headers") or {})


def test_webhook_send_with_secret_includes_hmac_header():
    from arm.notifications.channels.webhook import send_webhook

    fake_resp = MagicMock(status_code=200, text="ok")
    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.post.return_value = fake_resp
    payload = _build_payload_dict()
    with patch("arm.notifications.channels.webhook.httpx.Client",
               return_value=fake_client):
        ok, _ = send_webhook(
            url="https://example.com/hook",
            payload_dict=payload,
            shared_secret="supersecret123",
            headers=None,
        )
    assert ok is True
    call_kwargs = fake_client.post.call_args.kwargs
    sig_header = call_kwargs["headers"]["X-ARM-Signature"]
    assert sig_header.startswith("sha256=")

    # Verify the signature matches what we'd expect.
    sent_body = call_kwargs["content"]
    expected = hmac.new(
        b"supersecret123",
        sent_body if isinstance(sent_body, bytes) else sent_body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert sig_header == f"sha256={expected}"


def test_webhook_send_extra_headers_merged():
    from arm.notifications.channels.webhook import send_webhook

    fake_resp = MagicMock(status_code=200, text="ok")
    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.post.return_value = fake_resp
    with patch("arm.notifications.channels.webhook.httpx.Client",
               return_value=fake_client):
        ok, _ = send_webhook(
            url="https://example.com/hook",
            payload_dict=_build_payload_dict(),
            shared_secret=None,
            headers={"Authorization": "Bearer abc"},
        )
    assert ok is True
    sent_headers = fake_client.post.call_args.kwargs["headers"]
    assert sent_headers.get("Authorization") == "Bearer abc"
    assert sent_headers.get("Content-Type") == "application/json"


def test_webhook_send_4xx_is_terminal_failure():
    """HTTP 4xx (except 429) means the subscriber rejected the payload —
    retrying won't help. Returns terminal=True via the structured error."""
    from arm.notifications.channels.webhook import send_webhook

    fake_resp = MagicMock(status_code=400, text="bad request")
    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.post.return_value = fake_resp
    with patch("arm.notifications.channels.webhook.httpx.Client",
               return_value=fake_client):
        ok, error = send_webhook(
            url="https://example.com/hook",
            payload_dict=_build_payload_dict(),
            shared_secret=None,
            headers=None,
        )
    assert ok is False
    assert error is not None
    assert "400" in error
    assert "terminal=true" in error  # marker the dispatcher reads


def test_webhook_send_429_is_transient():
    """429 Too Many Requests → retry."""
    from arm.notifications.channels.webhook import send_webhook

    fake_resp = MagicMock(status_code=429, text="rate limited")
    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.post.return_value = fake_resp
    with patch("arm.notifications.channels.webhook.httpx.Client",
               return_value=fake_client):
        ok, error = send_webhook(
            url="https://example.com/hook",
            payload_dict=_build_payload_dict(),
            shared_secret=None,
            headers=None,
        )
    assert ok is False
    assert "terminal=false" in error


def test_webhook_send_5xx_is_transient():
    from arm.notifications.channels.webhook import send_webhook

    fake_resp = MagicMock(status_code=503, text="unavailable")
    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.post.return_value = fake_resp
    with patch("arm.notifications.channels.webhook.httpx.Client",
               return_value=fake_client):
        ok, error = send_webhook(
            url="https://example.com/hook",
            payload_dict=_build_payload_dict(),
            shared_secret=None,
            headers=None,
        )
    assert ok is False
    assert "terminal=false" in error


def test_webhook_send_network_error_is_transient():
    from arm.notifications.channels.webhook import send_webhook
    import httpx

    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.post.side_effect = httpx.ConnectError("connection refused")
    with patch("arm.notifications.channels.webhook.httpx.Client",
               return_value=fake_client):
        ok, error = send_webhook(
            url="https://example.com/hook",
            payload_dict=_build_payload_dict(),
            shared_secret=None,
            headers=None,
        )
    assert ok is False
    assert "terminal=false" in error
