"""FastAPI dependency injection utilities."""

from fastapi import HTTPException

from backend.config import settings


def require_transcoder_enabled() -> None:
    """Raise 503 when the transcoder feature is disabled for this deployment."""
    if not settings.transcoder_enabled:
        raise HTTPException(
            status_code=503,
            detail="Transcoder disabled on this deployment",
        )
