"""Preset CRUD endpoints."""

import json
import logging
import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from auth import get_current_user, require_admin
from config import settings
from database import get_db
from handbrake_presets import list_handbrake_presets
from models import ConfigOverrideDB, CustomPresetDB
from presets import Preset, resolve_preset

logger = logging.getLogger(__name__)

router = APIRouter()

_RESP_SCHEME_UNLOADED = {503: {"description": "Scheme not loaded"}}
_RESP_NOT_FOUND = {404: {"description": "Preset not found"}}
_RESP_BAD_REQUEST = {400: {"description": "Validation error"}}
_RESP_CONFLICT = {409: {"description": "Slug conflict"}}


def _get_scheme():
    from main import active_scheme
    if active_scheme is None:
        raise HTTPException(status_code=503, detail="Scheme not loaded")
    return active_scheme


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "custom"


_VALID_TIERS = ("dvd", "bluray", "uhd")


def _validate_shared_overrides(shared: dict, scheme) -> list[str]:
    errors = []
    if "audio_encoder" in shared and shared["audio_encoder"] not in scheme.supported_audio_encoders:
        errors.append(f"Unsupported audio encoder: {shared['audio_encoder']}")
    if "subtitle_mode" in shared and shared["subtitle_mode"] not in scheme.supported_subtitle_modes:
        errors.append(f"Unsupported subtitle mode: {shared['subtitle_mode']}")
    return errors


def _validate_tier_overrides(tiers: dict, scheme) -> list[str]:
    errors = []
    valid_encoders = set(scheme.encoder_slugs)
    for tier_name, tier_fields in tiers.items():
        if tier_name not in _VALID_TIERS:
            errors.append(f"Unknown tier: {tier_name}")
            continue
        encoder = tier_fields.get("video_encoder")
        if encoder and encoder not in valid_encoders:
            errors.append(f"Unsupported encoder: {encoder}")
    return errors


def _validate_overrides(scheme, overrides: dict) -> list[str]:
    errors = _validate_shared_overrides(overrides.get("shared", {}), scheme)
    errors.extend(_validate_tier_overrides(overrides.get("tiers", {}), scheme))
    return errors


def _builtin_to_response(preset: Preset) -> dict[str, Any]:
    """Convert a built-in Preset to the API response shape."""
    return {
        "slug": preset.slug,
        "name": preset.name,
        "scheme": preset.scheme,
        "description": preset.description,
        "builtin": True,
        "shared": preset.shared,
        "tiers": preset.tiers,
    }


def _custom_to_response(row: CustomPresetDB, scheme) -> dict[str, Any]:
    """Convert a CustomPresetDB row to the API response shape.

    If the custom preset's scheme doesn't match the active scheme, mark it
    as unavailable instead of trying to resolve it.
    """
    overrides = json.loads(row.overrides_json) if row.overrides_json else {}

    if row.scheme != scheme.slug:
        return {
            "slug": row.slug,
            "name": row.name,
            "scheme": row.scheme,
            "description": "",
            "builtin": False,
            "parent_slug": row.parent_slug,
            "shared": overrides.get("shared", {}),
            "tiers": overrides.get("tiers", {}),
            "unavailable": True,
            "reason": "scheme mismatch",
        }

    parent = scheme.get_preset(row.parent_slug)
    if parent is None:
        return {
            "slug": row.slug,
            "name": row.name,
            "scheme": row.scheme,
            "description": "",
            "builtin": False,
            "parent_slug": row.parent_slug,
            "shared": overrides.get("shared", {}),
            "tiers": overrides.get("tiers", {}),
            "unavailable": True,
            "reason": "parent preset not found",
        }

    # Resolve each tier by merging parent + overrides
    resolved_tiers = {}
    for tier in ("dvd", "bluray", "uhd"):
        resolved_tiers[tier] = resolve_preset(parent, tier, overrides)

    return {
        "slug": row.slug,
        "name": row.name,
        "scheme": row.scheme,
        "description": parent.description,
        "builtin": False,
        "parent_slug": row.parent_slug,
        "shared": {**parent.shared, **overrides.get("shared", {})},
        "tiers": resolved_tiers,
    }


# ---- Scheme endpoint -------------------------------------------------------


@router.get("/scheme", responses=_RESP_SCHEME_UNLOADED)
async def get_scheme(_role: Annotated[str, Depends(get_current_user)]):
    """Return active scheme metadata."""
    scheme = _get_scheme()
    return {
        "slug": scheme.slug,
        "name": scheme.name,
        "supported_encoders": [
            enc.model_dump() for enc in scheme.supported_encoders
        ],
        "supported_audio_encoders": scheme.supported_audio_encoders,
        "supported_subtitle_modes": scheme.supported_subtitle_modes,
        "advanced_fields": scheme.advanced_fields,
    }


# ---- Preset CRUD -----------------------------------------------------------


@router.get("/handbrake-presets")
async def get_handbrake_presets(
    _role: Annotated[str, Depends(get_current_user)],
) -> dict[str, list[str]]:
    """Return categorized HandBrakeCLI built-in preset names.

    Result shape: ``{category_name: [preset_name, ...]}``. Empty dict if
    HandBrakeCLI is missing, hangs, or emits unparseable output - the
    UI is expected to fall back to free-text entry in that case.
    """
    return await list_handbrake_presets()


@router.get("/presets", responses=_RESP_SCHEME_UNLOADED)
async def list_presets(_role: Annotated[str, Depends(get_current_user)]):
    """Return all presets: built-ins from the active scheme + custom from DB."""
    scheme = _get_scheme()

    results: list[dict[str, Any]] = []

    # Built-in presets
    for preset in scheme.built_in_presets:
        results.append(_builtin_to_response(preset))

    # Custom presets from DB
    async with get_db() as db:
        rows = (await db.execute(select(CustomPresetDB))).scalars().all()

    for row in rows:
        results.append(_custom_to_response(row, scheme))

    return {"presets": results}


@router.get("/presets/{slug}", responses={**_RESP_SCHEME_UNLOADED, **_RESP_NOT_FOUND})
async def get_preset(
    slug: str,
    _role: Annotated[str, Depends(get_current_user)],
):
    """Return a single preset by slug."""
    scheme = _get_scheme()

    # Check built-ins first
    builtin = scheme.get_preset(slug)
    if builtin is not None:
        return _builtin_to_response(builtin)

    # Check custom presets
    async with get_db() as db:
        row = await db.get(CustomPresetDB, slug)

    if row is None:
        raise HTTPException(status_code=404, detail=f"Preset not found: {slug}")

    return _custom_to_response(row, scheme)


@router.post("/presets", status_code=201,
              responses={**_RESP_SCHEME_UNLOADED, **_RESP_BAD_REQUEST, **_RESP_CONFLICT})
async def create_preset(
    request: dict[str, Any],
    _role: Annotated[str, Depends(require_admin)],
):
    """Create a custom preset based on a built-in parent."""
    scheme = _get_scheme()

    name = request.get("name")
    if not name or not str(name).strip():
        raise HTTPException(status_code=400, detail="name is required")
    name = str(name).strip()

    parent_slug = request.get("parent_slug")
    if not parent_slug:
        raise HTTPException(status_code=400, detail="parent_slug is required")

    parent = scheme.get_preset(parent_slug)
    if parent is None:
        raise HTTPException(
            status_code=400,
            detail=f"Parent preset not found in active scheme: {parent_slug}",
        )

    overrides = request.get("overrides", {})
    if not isinstance(overrides, dict):
        raise HTTPException(status_code=400, detail="overrides must be an object")

    # Validate override fields against scheme capabilities
    errors = _validate_overrides(scheme, overrides)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    slug = _slugify(name)

    # Check for conflicts with built-in presets
    if scheme.get_preset(slug) is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Slug conflicts with built-in preset: {slug}",
        )

    async with get_db() as db:
        existing = await db.get(CustomPresetDB, slug)
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Custom preset already exists: {slug}",
            )

        row = CustomPresetDB(
            slug=slug,
            name=name,
            scheme=scheme.slug,
            parent_slug=parent_slug,
            overrides_json=json.dumps(overrides),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)

    return _custom_to_response(row, scheme)


@router.patch("/presets/{slug}",
               responses={**_RESP_SCHEME_UNLOADED, **_RESP_BAD_REQUEST, **_RESP_NOT_FOUND})
async def update_preset(
    slug: str,
    request: dict[str, Any],
    _role: Annotated[str, Depends(require_admin)],
):
    """Update a custom preset. Built-in presets cannot be modified."""
    scheme = _get_scheme()

    # Reject updates to built-in presets
    if scheme.get_preset(slug) is not None:
        raise HTTPException(status_code=404, detail="Cannot update built-in preset")

    async with get_db() as db:
        row = await db.get(CustomPresetDB, slug)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Preset not found: {slug}")

        if "name" in request:
            name = request["name"]
            if not name or not str(name).strip():
                raise HTTPException(status_code=400, detail="name cannot be empty")
            row.name = str(name).strip()

        if "overrides" in request:
            overrides = request["overrides"]
            if not isinstance(overrides, dict):
                raise HTTPException(status_code=400, detail="overrides must be an object")
            errors = _validate_overrides(scheme, overrides)
            if errors:
                raise HTTPException(status_code=400, detail="; ".join(errors))
            row.overrides_json = json.dumps(overrides)

        await db.commit()
        await db.refresh(row)

    return _custom_to_response(row, scheme)


@router.delete("/presets/{slug}", responses={**_RESP_SCHEME_UNLOADED, **_RESP_NOT_FOUND})
async def delete_preset(
    slug: str,
    _role: Annotated[str, Depends(require_admin)],
):
    """Delete a custom preset. Built-in presets cannot be deleted.

    If the deleted preset is currently the `selected_preset_slug`, the
    selection is nulled in the same transaction so subsequent jobs fall
    through to the active scheme's default preset rather than silently
    referring to a dangling slug.
    """
    scheme = _get_scheme()

    if scheme.get_preset(slug) is not None:
        raise HTTPException(status_code=404, detail="Cannot delete built-in preset")

    selection_cleared = False
    async with get_db() as db:
        row = await db.get(CustomPresetDB, slug)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Preset not found: {slug}")

        # If this preset is the active selection, null it (and persist) so
        # next-job resolution falls back to the scheme default.
        if settings.selected_preset_slug == slug:
            override_row = await db.get(ConfigOverrideDB, "selected_preset_slug")
            if override_row:
                await db.delete(override_row)
            settings.selected_preset_slug = ""
            selection_cleared = True

        await db.delete(row)
        await db.commit()

    return {"success": True, "deleted": slug, "selection_cleared": selection_cleared}
