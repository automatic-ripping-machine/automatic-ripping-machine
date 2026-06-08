"""Compose an apprise URL from catalog form values.

Frontend posts ``{required: {...}, advanced: {...}}`` to the API; the
API calls this composer to assemble the full apprise URL string. The
URL is what gets stored in ``NotificationChannel.config["url"]``.

The composer does not know per-service URL syntax beyond the basic
``scheme://<required-fields-joined>?<advanced-fields-as-query>`` shape.
Services with unusual separators (e.g. Pushover's ``@``) get the raw-URL
escape hatch in the frontend.
"""
from urllib.parse import quote, urlencode


def _bool_yesno(v: bool) -> str:
    return "yes" if v else "no"


def _stringify(value) -> str:
    if isinstance(value, bool):
        return _bool_yesno(value)
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)


def compose_apprise_url(
    *,
    service_id: str,
    required: dict[str, object],
    advanced: dict[str, object],
) -> str:
    """Assemble an apprise URL from required + advanced field values.

    Required values become URL-encoded path segments in dict-iteration
    order. Advanced values become query parameters. Blank/None advanced
    values are omitted (they'd serialize as ``?key=`` which apprise
    rejects on some plugins).
    """
    path = "/".join(quote(_stringify(v), safe="")
                    for v in required.values() if v not in (None, ""))
    base = f"{service_id}://{path}"

    pairs = []
    for k, v in advanced.items():
        if v in (None, ""):
            continue
        pairs.append((k, _stringify(v)))

    if pairs:
        return f"{base}?{urlencode(pairs)}"
    return base
