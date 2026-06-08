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


def _row_version(revision) -> str:
    """Extract the version string from an alembic revision row, or 'unknown'.

    arm_db_check() puts an alembic Row (from arm_db_get) into ``db_revision``.
    The Row carries a ``version_num`` column; when serialized directly to
    JSON it becomes ``{}``, which fails the BFF's typed setup contract.
    """
    if revision is None:
        return "unknown"
    version = getattr(revision, "version_num", None)
    if isinstance(version, str) and version:
        return version
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

    # Check first_run via AppState.setup_complete.
    #
    # When the DB is initialized, default to first_run=False so that
    # transient DB errors (contention, locked session) don't flash the
    # setup wizard during normal operation.  Only default to True when
    # the DB genuinely doesn't exist or isn't current.
    first_run = not db_initialized
    drive_count = 0
    try:
        from arm.models.app_state import AppState
        state = AppState.get()
        first_run = not state.setup_complete
    except Exception:
        if not db_initialized:
            first_run = True  # DB not ready - assume first run
        else:
            log.warning("AppState query failed on initialized DB - defaulting first_run=False")
            first_run = False  # DB exists but query failed - don't flash wizard

    try:
        from arm.models.system_drives import SystemDrives
        # stale=True rows are old detections kept for audit history; the
        # wizard count should reflect drives currently attached.
        drive_count = SystemDrives.query.filter(
            (SystemDrives.stale.is_(False)) | (SystemDrives.stale.is_(None))
        ).count()
    except Exception:
        pass

    return {
        "db_exists": db_status.get("db_exists", False),
        "db_initialized": db_initialized,
        "db_current": db_initialized,
        "db_version": _row_version(db_status.get("db_revision")),
        "db_head": db_status.get("head_revision") or "unknown",
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
