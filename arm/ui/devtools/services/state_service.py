"""
Devtools service - application state summary.
"""
from __future__ import annotations

from typing import Any

from ui.devtools.adapters import state_adapter


def get_app_state() -> dict[str, Any]:
    """
    Return current ARM job, drive, service, warning and safe config summaries.

    Returns:
        dict: the five state summaries
    """
    return {
        "jobs": state_adapter.get_jobs_summary(),
        "drives": state_adapter.get_drive_state_summary(),
        "services": state_adapter.get_service_health(),
        "warnings": state_adapter.get_warning_summary(),
        "safe_config": state_adapter.get_safe_config_summary(),
    }
