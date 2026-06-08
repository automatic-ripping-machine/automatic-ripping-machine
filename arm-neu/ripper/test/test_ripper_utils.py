"""Tests for arm/ripper/utils.py transcoder_notify() webhook behavior."""
import pytest


@pytest.mark.parametrize("webhook_secret", ["test-secret", ""])
def test_transcoder_notify_sends_x_api_version_header(
    webhook_secret, app_context,
    transcoder_notify_job, transcoder_notify_patches,
):
    """transcoder_notify must send X-Api-Version: 2 regardless of webhook secret.

    Cross-service version handshake: ARM stamps every webhook POST to the
    transcoder so older transcoders reject new-shape payloads loudly instead
    of silently dropping unknown fields.
    """
    from arm.ripper.utils import transcoder_notify

    cfg = {
        'TRANSCODER_URL': 'https://localhost:5000/webhook',
        'TRANSCODER_WEBHOOK_SECRET': webhook_secret,
        'SHARED_RAW_PATH': '',
        'LOCAL_RAW_PATH': '',
    }

    transcoder_notify(cfg, "Title", "Body", transcoder_notify_job)

    transcoder_notify_patches.post.assert_called_once()
    _, kwargs = transcoder_notify_patches.post.call_args
    headers = kwargs.get('headers') or {}
    assert headers.get('X-Api-Version') == '2', (
        f"Expected X-Api-Version: 2 header, got headers={headers!r}"
    )
