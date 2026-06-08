"""Send a rich-payload webhook with optional HMAC-SHA256 signing.

The wire shape is ``OutboundWebhookPayload`` from arm_contracts. When a
shared_secret is provided, the dispatcher computes HMAC-SHA256 over the
canonical JSON body and sends it in ``X-ARM-Signature: sha256=<hex>``.

The error string returned on failure embeds a ``terminal=true|false``
marker so the dispatcher can decide whether to retry. We don't raise
exceptions — the channel boundary keeps them inside.
"""
import hashlib
import hmac
import json
import logging
from typing import Optional

import httpx

from arm.notifications.url_safety import UnsafeUrlError, assert_public_http_url

log = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 15.0


def _is_terminal_status(status_code: int) -> bool:
    """4xx (other than 429) is terminal; 5xx and 429 are transient."""
    if status_code == 429:
        return False
    return 400 <= status_code < 500


def send_webhook(
    *,
    url: str,
    payload_dict: dict,
    shared_secret: Optional[str],
    headers: Optional[dict[str, str]],
) -> tuple[bool, str | None]:
    """POST the payload to the given URL.

    :param url: full HTTPS endpoint
    :param payload_dict: JSON-serializable dict (OutboundWebhookPayload)
    :param shared_secret: optional plain-text HMAC key
    :param headers: optional additional static headers
    :returns: ``(True, None)`` on success, ``(False, "<message> terminal=<bool>")``
        on failure. The dispatcher parses the marker.
    """
    # SSRF guard: validate the target on every send (not just the unsaved-test
    # path). assert_public_http_url() requires http(s) and rejects hosts that
    # resolve to loopback/private/link-local/reserved addresses.
    try:
        assert_public_http_url(url)
    except UnsafeUrlError as exc:
        return False, f"unsafe webhook URL: {exc} terminal=true"

    body_bytes = json.dumps(
        payload_dict, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")

    request_headers: dict[str, str] = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    if shared_secret:
        digest = hmac.new(
            shared_secret.encode("utf-8"), body_bytes, hashlib.sha256
        ).hexdigest()
        request_headers["X-ARM-Signature"] = f"sha256={digest}"

    try:
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            resp = client.post(
                url, content=body_bytes, headers=request_headers
            )
    except httpx.HTTPError as exc:
        # Network errors, timeouts, etc. — all transient.
        return False, f"network error: {exc} terminal=false"

    if 200 <= resp.status_code < 300:
        return True, None

    terminal = _is_terminal_status(resp.status_code)
    return (
        False,
        f"HTTP {resp.status_code}: "
        f"{resp.text[:200]} terminal={'true' if terminal else 'false'}",
    )
