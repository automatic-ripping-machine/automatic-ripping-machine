"""
Devtools service - ARM config access.
"""
from __future__ import annotations

import re
from typing import Any

from config import config as cfg

_SECRET_KEYS = re.compile(r"(password|secret|key|token)", re.IGNORECASE)


def _redact_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    Redact secret-looking arm.yaml values.

    Args:
        config: the arm.yaml config dict

    Returns:
        dict: the config with secret values replaced
    """
    return {key: ("<redacted>" if _SECRET_KEYS.search(str(key)) else value) for key, value in config.items()}


def get_app_config() -> dict[str, Any]:
    """
    Return the full arm.yaml config with secrets redacted.

    Returns:
        dict: redacted config plus a note
    """
    return {
        "keys": _redact_config(cfg.arm_config),
        "note": "values redacted for password/key/token entries",
    }


def get_config_value(key: str) -> dict[str, Any]:
    """
    Return one arm.yaml value (redacted when secret-looking).

    Args:
        key: arm.yaml key name

    Returns:
        dict: key, value and value type
    """
    if key not in cfg.arm_config:
        raise ValueError(f"Unknown config key '{key}'")
    value = cfg.arm_config[key]
    if _SECRET_KEYS.search(str(key)):
        value = "<redacted>"
    return {"key": key, "value": value, "type": type(cfg.arm_config[key]).__name__}


def set_config_value(key: str, value: Any) -> dict[str, Any]:
    """
    Set an arm.yaml value in-memory only.

    The change is not persisted - durable, behaviour-affecting changes must
    go through the UI's /save_settings path, which rewrites arm.yaml.

    Args:
        key: arm.yaml key name
        value: new value, coerced to the existing value's type

    Returns:
        dict: key, previous and current values plus a persistence note
    """
    if key not in cfg.arm_config:
        raise ValueError(f"Unknown config key '{key}'")
    old = cfg.arm_config[key]
    if isinstance(old, bool):
        value = str(value).strip().lower() in ("1", "true", "yes", "on")
    elif isinstance(old, int):
        value = int(value)
    elif isinstance(old, str):
        value = str(value)
    cfg.arm_config[key] = value
    return {
        "key": key,
        "previous": old if not _SECRET_KEYS.search(str(key)) else "<redacted>",
        "current": cfg.arm_config[key],
        "note": "in-memory only; /save_settings or restart required to persist",
    }
