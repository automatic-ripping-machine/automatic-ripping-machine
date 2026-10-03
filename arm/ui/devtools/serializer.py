"""
Shared model serializer for the devtools API.

Mirrors models.get_d() but keeps native JSON types and honours the
model's hidden_attribs redaction, plus an unconditional redaction of
secret-looking keys (password, hash, api key, secret, token).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Keys redacted regardless of the model's hidden_attribs
_REDACTED_KEY_PARTS = ("password", "hash", "api_key", "secret", "token")


def serialize_model(obj: Any) -> dict[str, Any]:
    """
    Serialize an ARMModel instance to a JSON-safe dict.

    Args:
        obj: an ARMModel instance

    Returns:
        dict: the serialized model with secrets redacted
    """
    state = getattr(obj, "__dict__", {}).copy()
    state.pop("_sa_instance_state", None)
    hidden = getattr(obj, "hidden_attribs", ())
    result = {}
    for key, value in state.items():
        if key in hidden:
            continue
        if any(part in str(key).lower() for part in _REDACTED_KEY_PARTS):
            result[key] = "<hidden>"
        elif isinstance(value, datetime):
            result[key] = value.astimezone(timezone.utc).isoformat()
        elif isinstance(value, (int, float, bool, type(None), str, list, dict)):
            result[key] = value
        else:
            result[key] = str(value)
    return result
