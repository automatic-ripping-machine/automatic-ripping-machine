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
