"""Apprise-introspected service catalog.

The catalog is generated at runtime from apprise's own plugin metadata
(``apprise.manager_plugins.NotificationManager``). Each plugin class
exposes ``template_tokens`` (URL path components, including which are
required and private) and ``template_args`` (query parameters with
types, defaults, and allowed values).

A blocklist filters out operational args that aren't user-facing
(timeouts, TLS verification, persistent storage, etc.). A featured
list pins the ten most common services for the UI's primary picker
slot; everything else lives in the long tail.
"""
import functools
import logging
from typing import Any

import apprise
from apprise.manager_plugins import NotificationManager

log = logging.getLogger(__name__)

# Args every apprise plugin inherits — never user-facing.
# Note: ``format`` is intentionally NOT blocked — some services expose
# meaningful format choices (text/html/markdown) that users can override.
_BLOCKED_ARGS = frozenset({
    "verify",     # TLS verification — security default
    "rto",        # read timeout
    "cto",        # connect timeout
    "store",      # persistent-store mode
    "tz",         # timezone (locale concern)
    "overflow",   # message-overflow mode (apprise-internal)
    "emojis",     # apprise-side emoji expansion (off by default)
})

FEATURED_SERVICES = [
    # IDs are the apprise URL schemes (``secure_protocol`` preferred,
    # falling back to ``protocol``). Apprise's scheme names don't always
    # match the brand — telegram is ``tgram``, pushbullet is ``pbul``,
    # pushover is ``pover``, email is ``mailtos``.
    "discord", "slack", "tgram", "pbul", "pover",
    "ntfys", "mailtos", "ifttt", "gotifys", "matrixs",
]


def _get_manager() -> NotificationManager:
    """Indirection so tests can patch the manager."""
    mgr = NotificationManager()
    mgr.load_modules()
    return mgr


def _normalize_type(template_type: str) -> str:
    """apprise types like 'choice:string' become 'choice' for the UI;
    'string', 'bool', 'int', 'float' pass through."""
    if template_type.startswith("choice"):
        return "choice"
    return template_type


def _build_field(key: str, spec: dict) -> dict:
    """Convert one apprise template token / arg to a catalog field."""
    field: dict[str, Any] = {
        "key": key,
        "label": str(spec.get("name", key)),
        "type": _normalize_type(spec.get("type", "string")),
        "private": bool(spec.get("private", False)),
        "required": bool(spec.get("required", False)),
    }
    if "default" in spec:
        default = spec["default"]
        # Enum-y defaults can be objects with a .value — coerce safely.
        if hasattr(default, "value"):
            default = default.value
        field["default"] = default
    if field["type"] == "choice" and "values" in spec:
        field["values"] = sorted(str(v) for v in spec["values"])
    return field


def _service_id(plugin_cls) -> str | None:
    """The apprise URL scheme is the canonical id (e.g. ``discord``)."""
    scheme = plugin_cls.secure_protocol or plugin_cls.protocol
    if scheme is None:
        return None
    if isinstance(scheme, (list, tuple)):
        return scheme[0]
    return scheme


def _build_service_entry(plugin_cls) -> dict | None:
    service_id = _service_id(plugin_cls)
    if not service_id:
        return None

    required_fields = []
    for key, spec in (plugin_cls.template_tokens or {}).items():
        if spec.get("required"):
            required_fields.append(_build_field(key, spec))

    advanced_fields = []
    for key, spec in (plugin_cls.template_args or {}).items():
        if key in _BLOCKED_ARGS:
            continue
        # Skip aliases — apprise lists them as "alias_of": <other_key>.
        if "alias_of" in spec:
            continue
        advanced_fields.append(_build_field(key, spec))

    return {
        "id": service_id,
        # apprise wraps some labels in LazyTranslation; coerce to str so
        # downstream sorting/serialization works uniformly.
        "name": str(plugin_cls.service_name),
        "docs_url": plugin_cls.service_url or "",
        "url_scheme": service_id,
        "required_fields": required_fields,
        "advanced_fields": advanced_fields,
    }


@functools.lru_cache(maxsize=1)
def build_catalog() -> dict:
    """Build the service catalog from the live apprise plugin manager.

    Result shape: ``{"featured": [id, ...], "services": [{...}, ...]}``.
    Services are sorted by ``name`` for stable iteration; ``featured``
    is the curated subset in display order.
    """
    mgr = _get_manager()
    services = []
    seen_ids: set[str] = set()
    for plugin_cls in mgr.plugins():
        try:
            entry = _build_service_entry(plugin_cls)
        except Exception as exc:
            log.debug("catalog: skipping plugin %s: %s",
                      getattr(plugin_cls, "__name__", "<?>"), exc)
            continue
        if entry is None or entry["id"] in seen_ids:
            continue
        seen_ids.add(entry["id"])
        services.append(entry)

    services.sort(key=lambda s: s["name"].lower())
    return {
        "featured": [s for s in FEATURED_SERVICES if s in seen_ids],
        "services": services,
    }
