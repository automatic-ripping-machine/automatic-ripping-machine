"""BFF response shape for the setup wizard surface."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SetupStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")

    db_exists: bool = False
    db_initialized: bool = False
    db_current: bool = False
    db_version: str = ""
    db_head: str = ""
    first_run: bool = True
    arm_version: str = ""
    setup_steps: dict[str, str] = {}
