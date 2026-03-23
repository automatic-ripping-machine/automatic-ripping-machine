"""API v1 — Setup wizard endpoints."""
import logging
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

import arm.config.config as cfg
from arm.database import db
from arm.services.config import arm_db_check

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["setup"])


def _read_version() -> str:
    """Read ARM version from VERSION file."""
    for p in ("VERSION", os.path.join(cfg.arm_config.get("INSTALLPATH", "/opt/arm"), "VERSION")):
        try:
            with open(p) as f:
                return f.read().strip()
        except OSError:
            continue
    return "unknown"


@router.get("/setup/status")
def get_setup_status():
    """Return setup state for the wizard.

    Designed to work even when the database is not yet initialized —
    all DB queries are wrapped in try/except so the endpoint always
    returns a valid JSON response.
    """
    try:
        db_status = arm_db_check()
    except Exception:
        db_status = {
            "db_exists": False,
            "db_current": False,
            "head_revision": "unknown",
            "db_revision": "unknown",
        }

    db_initialized = db_status.get("db_current", False)

    # Check first_run via AppState.setup_complete
    first_run = True
    drive_count = 0
    try:
        from arm.models.app_state import AppState
        state = AppState.get()
        first_run = not state.setup_complete
    except Exception:
        pass  # Table may not exist yet

    try:
        from arm.models.system_drives import SystemDrives
        drive_count = SystemDrives.query.count()
    except Exception:
        pass

    return {
        "db_exists": db_status.get("db_exists", False),
        "db_initialized": db_initialized,
        "db_current": db_initialized,
        "db_version": db_status.get("db_revision", "unknown"),
        "db_head": db_status.get("head_revision", "unknown"),
        "first_run": first_run,
        "arm_version": _read_version(),
        "setup_steps": {
            "database": "complete" if db_initialized else "pending",
            "drives": f"{drive_count} detected",
            "settings_reviewed": "complete" if not first_run else "pending",
        },
    }


@router.post("/setup/complete")
def complete_setup():
    """Mark setup as done. Prevents the wizard from showing again."""
    try:
        from arm.models.app_state import AppState
        state = AppState.get()
        state.setup_complete = True
        db.session.commit()
        return {"success": True}
    except Exception as e:
        log.error("Failed to mark setup complete: %s", e)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to mark setup complete"},
        )
