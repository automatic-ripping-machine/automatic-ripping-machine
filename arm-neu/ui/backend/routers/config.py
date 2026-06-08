"""Feature-flag discovery endpoint for the frontend."""

from fastapi import APIRouter

from backend.config import settings
from backend.models.config import RuntimeConfigResponse

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config", response_model=RuntimeConfigResponse)
async def get_config() -> RuntimeConfigResponse:
    """Return feature flags that the frontend needs to render the right UI."""
    return RuntimeConfigResponse(transcoder_enabled=settings.transcoder_enabled)
