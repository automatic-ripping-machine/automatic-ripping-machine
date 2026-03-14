"""API v1 — Settings endpoints."""
import asyncio
import logging

import yaml
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import arm.config.config as cfg
from arm.models.config import hidden_attribs, HIDDEN_VALUE
from arm.services import jobs as svc_jobs
from arm.services.config import generate_comments, build_arm_cfg

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["settings"])


@router.get('/settings/notify-timeout')
def get_notify_timeout():
    """Get the notification timeout setting."""
    return svc_jobs.get_notify_timeout('notify_timeout')


@router.get('/settings/config')
def get_config():
    """Return live arm.yaml config with sensitive fields masked."""
    from arm.ripper.naming import PATTERN_VARIABLES

    raw_config = dict(cfg.arm_config)
    config = {}
    for key in raw_config.keys():
        if key in hidden_attribs and raw_config[key]:
            config[str(key)] = HIDDEN_VALUE
        else:
            config[str(key)] = str(raw_config[key]) if raw_config[key] is not None else None

    comments = generate_comments()
    return {
        "config": config,
        "comments": comments,
        "naming_variables": PATTERN_VARIABLES,
    }


@router.put('/settings/config')
async def update_config(request: Request):
    """Update arm.yaml config from JSON payload."""
    data = await request.json()
    if not data or "config" not in data:
        return JSONResponse(
            {"success": False, "error": "Missing 'config' in request body"},
            status_code=400,
        )

    incoming = data["config"]
    if not isinstance(incoming, dict) or len(incoming) == 0:
        return JSONResponse(
            {"success": False, "error": "'config' must be a non-empty object"},
            status_code=400,
        )

    # Preserve existing values for hidden fields that were not changed
    current = dict(cfg.arm_config)
    for key in hidden_attribs:
        if key in incoming and incoming[key] == HIDDEN_VALUE and key in current:
            incoming[key] = str(current[key])

    # Convert all values to strings (build_arm_cfg expects str values)
    form_data = {k: str(v) for k, v in incoming.items()}

    comments = generate_comments()
    arm_cfg_text = build_arm_cfg(form_data, comments)

    def _write_config():
        with open(cfg.arm_config_path, "w") as f:
            f.write(arm_cfg_text)

    try:
        await asyncio.to_thread(_write_config)
    except OSError as e:
        log.error(f"Failed to write config: {e}")
        return JSONResponse(
            {"success": False, "error": "Failed to write config file"},
            status_code=500,
        )

    # Reload config in-place so all existing references see the new values
    def _read_config():
        with open(cfg.arm_config_path, "r") as f:
            return yaml.safe_load(f)

    try:
        new_values = await asyncio.to_thread(_read_config)
        cfg.arm_config.clear()
        cfg.arm_config.update(new_values)
    except Exception as e:
        log.error(f"Config reload failed: {e}")
        return {
            "success": True,
            "warning": "Config saved but reload failed",
        }

    return {"success": True}


def _abcde_path() -> str:
    """Return the resolved abcde.conf path from ARM config.

    Uses ``os.path.realpath`` to resolve symlinks and normalise the path,
    then validates that the result is an absolute path to prevent
    path-traversal attacks via a manipulated config value.
    """
    import os
    raw = str(cfg.arm_config.get("ABCDE_CONFIG_FILE", "/etc/abcde.conf"))
    resolved = os.path.realpath(raw)
    if not os.path.isabs(resolved):
        raise ValueError(f"ABCDE_CONFIG_FILE resolved to a relative path: {resolved}")
    return resolved


@router.get('/settings/abcde')
async def get_abcde_config():
    """Return the contents of the abcde.conf file."""
    try:
        path = _abcde_path()
    except ValueError as e:
        log.error(str(e))
        return JSONResponse({"content": "", "path": "", "exists": False}, status_code=200)

    def _read():
        try:
            with open(path, "r") as f:
                return f.read()
        except FileNotFoundError:
            return None

    try:
        content = await asyncio.to_thread(_read)
    except OSError as e:
        log.error(f"Failed to read abcde config: {e}")
        return JSONResponse(
            {"content": "", "path": path, "exists": False},
            status_code=200,
        )

    return {
        "content": content or "",
        "path": path,
        "exists": content is not None,
    }


@router.put('/settings/abcde')
async def update_abcde_config(request: Request):
    """Write content to the abcde.conf file."""
    data = await request.json()
    if not data or "content" not in data:
        return JSONResponse(
            {"success": False, "error": "Missing 'content' in request body"},
            status_code=400,
        )

    try:
        path = _abcde_path()
    except ValueError as e:
        log.error(str(e))
        return JSONResponse(
            {"success": False, "error": "Invalid ABCDE_CONFIG_FILE path"},
            status_code=400,
        )

    content = data["content"]

    def _write():
        with open(path, "w") as f:
            f.write(content)

    try:
        await asyncio.to_thread(_write)
    except OSError as e:
        log.error(f"Failed to write abcde config: {e}")
        return JSONResponse(
            {"success": False, "error": "Failed to write abcde config file"},
            status_code=500,
        )

    return {"success": True}
