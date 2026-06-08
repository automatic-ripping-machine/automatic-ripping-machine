"""Setup wizard proxy endpoints."""
from typing import Any

from fastapi import APIRouter

from backend.models.files import OperationResult
from backend.models.setup import SetupStatus
from backend.routers.arm_actions import _check_result
from backend.services import arm_client

router = APIRouter(prefix="/api", tags=["setup"])


@router.get("/setup/status", response_model=SetupStatus)
async def get_setup_status() -> dict[str, Any]:
    """Proxy setup status from ARM backend."""
    return _check_result(await arm_client.get_setup_status())


@router.post("/setup/complete", response_model=OperationResult)
async def complete_setup() -> dict[str, Any]:
    """Mark setup as done (proxies to ARM backend)."""
    return _check_result(await arm_client.complete_setup())
