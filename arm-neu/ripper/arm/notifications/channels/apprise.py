"""Send a notification through an apprise URL.

Wraps ``apprise.Apprise()`` so the rest of the module can stay
synchronous and dispatcher-friendly. apprise itself handles per-service
HTTP, retries within the library's own scope, and URL parsing.

URL-parse failures are terminal (apprise.add() returning False); send
failures are transient (apprise.notify() returning False).
"""
import logging

import apprise

log = logging.getLogger(__name__)


class AppriseSendError(RuntimeError):
    """Internal sentinel — used for typing clarity, not raised."""


def send_apprise(*, url: str, title: str, body: str) -> tuple[bool, str | None]:
    """Send via an apprise URL.

    :returns: ``(True, None)`` on success, ``(False, error_message)``
        on failure. Errors are never raised — the dispatcher branches
        on the boolean.
    """
    try:
        apobj = apprise.Apprise()
        if not apobj.add(url):
            return False, f"apprise rejected URL (likely malformed): {url}"
        ok = apobj.notify(body=body, title=title)
        if not ok:
            return False, "apprise.notify() returned False (transient)"
        return True, None
    except Exception as exc:
        log.warning("apprise send raised: %s", exc)
        return False, str(exc)
