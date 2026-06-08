"""Tests for transcoder._notify_arm_callback - informational path.

F1 + F3 (audit 2026-04-29): the informational callback used to send a
hand-built {"status": status} dict with no version header. After the fix:
- the body must round-trip through arm_contracts.TranscodeCallbackPayload
- the request must include X-Api-Version: 2
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from arm_contracts import JobStatus, TranscodeCallbackPayload


@pytest.fixture
def fake_settings(monkeypatch):
    """Set arm_callback_url so _notify_arm_callback fires."""
    from config import settings
    monkeypatch.setattr(settings, "arm_callback_url", "https://arm.example")
    return settings


@pytest.fixture
def fake_job():
    job = MagicMock()
    job.id = 42
    return job


@pytest.mark.asyncio
async def test_informational_callback_uses_typed_payload(fake_settings, fake_job):
    """F3: informational callback body must validate as TranscodeCallbackPayload."""
    from transcoder import TranscodeWorker

    transcoder = TranscodeWorker.__new__(TranscodeWorker)  # bypass __init__
    captured = {}

    class _FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return None
        async def post(self, url, **kwargs):
            captured["url"] = url
            captured["json"] = kwargs.get("json")
            captured["headers"] = kwargs.get("headers")
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            return resp

    with patch("transcoder.httpx.AsyncClient", return_value=_FakeClient()):
        await transcoder._notify_arm_callback(fake_job, "transcoding")

    assert captured["url"] == (
        "https://arm.example/api/v1/jobs/42/transcode-callback"
    )
    # Body parses through the contract - rename of JobStatus.transcoding
    # would fail here.
    parsed = TranscodeCallbackPayload.model_validate(captured["json"])
    assert parsed.status == JobStatus.transcoding


@pytest.mark.asyncio
async def test_informational_callback_includes_x_api_version(fake_settings, fake_job):
    """F1: informational callback must include X-Api-Version: 2."""
    from transcoder import TranscodeWorker

    transcoder = TranscodeWorker.__new__(TranscodeWorker)
    captured = {}

    class _FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return None
        async def post(self, url, **kwargs):
            captured["headers"] = kwargs.get("headers")
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            return resp

    with patch("transcoder.httpx.AsyncClient", return_value=_FakeClient()):
        await transcoder._notify_arm_callback(fake_job, "transcoding")

    assert captured["headers"] == {"X-Api-Version": "2"}


@pytest.mark.asyncio
async def test_informational_callback_rejects_invalid_status(fake_settings, fake_job):
    """F3: invalid JobStatus value crashes at construction, not over the wire."""
    from transcoder import TranscodeWorker

    transcoder = TranscodeWorker.__new__(TranscodeWorker)

    with patch("transcoder.httpx.AsyncClient") as mock_client_cls:
        with pytest.raises(ValueError):
            # "bogus" is not a valid JobStatus member
            await transcoder._notify_arm_callback(fake_job, "bogus")
        # Crucially, no HTTP call was made
        mock_client_cls.assert_not_called()
