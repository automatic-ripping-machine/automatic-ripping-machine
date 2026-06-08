"""Configuration endpoints."""

import json
import logging
import typing
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from auth import get_current_user, require_admin
from config import settings, unwrap_optional, UPDATABLE_KEYS, VALID_LOG_LEVELS
from database import get_db
from models import ConfigOverrideDB

logger = logging.getLogger(__name__)

router = APIRouter()


def _serialize_for_storage(value: object, annotation: type) -> str:
    """Convert a Pydantic-validated value to its DB string form.

    Dict/list fields are stored as JSON. Everything else uses str().
    Paired with _JSON_STRING_KEYS in src/config.py (load-side validation)
    and the dict-to-JSON preconversion earlier in this router.

    For str fields whose *content* is JSON (e.g. global_overrides), str(value)
    is a no-op on the already-serialized JSON string, which is exactly what
    we want.
    """
    annotation = unwrap_optional(annotation)

    if annotation is dict or typing.get_origin(annotation) is dict:
        return json.dumps(value)
    if annotation is list or typing.get_origin(annotation) is list:
        return json.dumps(value)

    return str(value)


@router.get("/config")
async def get_config(_role: Annotated[str, Depends(get_current_user)]):
    """Return current updatable settings and valid option lists."""
    config = {key: getattr(settings, key) for key in UPDATABLE_KEYS}
    # Deserialize JSON-stored overrides for clients that expect structured data.
    if isinstance(config.get("global_overrides"), str):
        try:
            config["global_overrides"] = json.loads(config["global_overrides"])
        except (ValueError, TypeError):
            config["global_overrides"] = {}
    return {
        "config": config,
        "updatable_keys": sorted(UPDATABLE_KEYS),
        "paths": {
            "raw_path": settings.raw_path,
            "completed_path": settings.completed_path,
            "work_path": settings.work_path,
        },
        "valid_log_levels": VALID_LOG_LEVELS,
    }


@router.patch("/config", responses={400: {"description": "Invalid or non-updatable keys"}, 422: {"description": "Validation error"}})
async def update_config(
    request: Request,
    _role: Annotated[str, Depends(require_admin)],
):
    """Update runtime settings. Validates, persists to DB, patches singleton."""
    data = await request.json()
    if not isinstance(data, dict) or not data:
        raise HTTPException(status_code=400, detail="Request body must be a non-empty JSON object")

    # Reject unknown keys
    invalid_keys = set(data.keys()) - UPDATABLE_KEYS
    if invalid_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Non-updatable keys: {', '.join(sorted(invalid_keys))}",
        )

    # global_overrides (and any future JSON-str field) arrives as a dict from the
    # UI; we serialize here so Pydantic validation sees a string. Mirrored by
    # _JSON_STRING_KEYS in src/config.py (load-side) and _serialize_for_storage
    # below (DB-write side).
    if "global_overrides" in data and isinstance(data["global_overrides"], dict):
        data["global_overrides"] = json.dumps(data["global_overrides"])

    # Validate preset slug exists (if provided)
    if "selected_preset_slug" in data:
        slug = data["selected_preset_slug"]
        if slug:  # empty = use scheme default
            from main import active_scheme
            if not active_scheme.get_preset(slug):
                from models import CustomPresetDB
                async with get_db() as db_check:
                    custom = await db_check.get(CustomPresetDB, slug)
                if not custom:
                    raise HTTPException(status_code=400,
                        detail=f"Unknown preset slug: {slug}")

    # Validate values by building a partial Settings with overrides
    current_vals = {key: getattr(settings, key) for key in UPDATABLE_KEYS}
    current_vals.update(data)
    try:
        from config import Settings as SettingsClass
        validated = SettingsClass.model_validate({**settings.model_dump(), **current_vals})
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Persist to DB and update in-memory singleton
    async with get_db() as db:
        for key, value in data.items():
            coerced = getattr(validated, key)
            annotation = SettingsClass.model_fields[key].annotation
            storage_value = _serialize_for_storage(coerced, annotation)
            override = await db.get(ConfigOverrideDB, key)
            if override:
                override.value = storage_value
                override.updated_at = datetime.now(timezone.utc)
            else:
                db.add(ConfigOverrideDB(key=key, value=storage_value))
            setattr(settings, key, coerced)
        await db.commit()

    return {
        "success": True,
        "applied": {key: getattr(settings, key) for key in data},
    }
