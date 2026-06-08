"""
Simple API key authentication for ARM Transcoder
"""

import hmac
import logging
from typing import Optional

from fastapi import Header, HTTPException, status
from fastapi.security import APIKeyHeader

from config import settings

logger = logging.getLogger(__name__)

# Optional API key scheme for documentation
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyAuth:
    """Simple API key authentication."""

    def __init__(self):
        """Initialize with API keys from config."""
        # Parse API keys from comma-separated string
        # Format: "key1,key2,key3" or "admin:key1,readonly:key2"
        self.keys = {}

        if settings.api_keys:
            for key_entry in settings.api_keys.split(","):
                key_entry = key_entry.strip()
                if ":" in key_entry:
                    # Format: "role:key"
                    role, key = key_entry.split(":", 1)
                    self.keys[key] = role.strip()
                else:
                    # Format: "key" (defaults to admin)
                    self.keys[key_entry] = "admin"

        self.require_auth = settings.require_api_auth

        if self.require_auth and not self.keys:
            logger.warning(
                "API authentication required but no keys configured! "
                "Set API_KEYS environment variable."
            )

    def verify_key(
        self,
        api_key: Optional[str] = Header(None, alias="X-API-Key"),
    ) -> str:
        """
        Verify API key from header.

        Args:
            api_key: API key from X-API-Key header

        Returns:
            Role associated with the key

        Raises:
            HTTPException: If authentication fails
        """
        # Skip auth if not required
        if not self.require_auth:
            return "admin"

        # Check if key provided
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required. Provide X-API-Key header.",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Verify key (constant-time lookup via hmac.compare_digest)
        role = None
        for known_key, known_role in self.keys.items():
            if hmac.compare_digest(api_key, known_key):
                role = known_role
                break
        if not role:
            logger.warning("Invalid API key attempt")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key",
            )

        return role

    def require_admin(
        self,
        api_key: Optional[str] = Header(None, alias="X-API-Key"),
    ) -> str:
        """
        Require admin role.

        Args:
            api_key: API key from X-API-Key header

        Returns:
            Role (will be 'admin')

        Raises:
            HTTPException: If not admin
        """
        role = self.verify_key(api_key)

        if role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

        return role


# Global auth instance
auth = APIKeyAuth()


# Dependency functions for FastAPI
async def get_current_user(
    api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """
    FastAPI dependency for any authenticated endpoint.

    Usage:
        @app.get("/jobs")
        async def list_jobs(role: str = Depends(get_current_user)):
            ...
    """
    return auth.verify_key(api_key)


async def require_admin(
    api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """
    FastAPI dependency for admin-only endpoints.

    Usage:
        @app.delete("/jobs/{id}")
        async def delete_job(id: int, role: str = Depends(require_admin)):
            ...
    """
    return auth.require_admin(api_key)


def verify_webhook_secret(
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret")
) -> bool:
    """
    Verify webhook secret (for ARM callbacks).

    Args:
        x_webhook_secret: Secret from X-Webhook-Secret header

    Returns:
        True if valid

    Raises:
        HTTPException: If secret required but invalid
    """
    if not settings.webhook_secret:
        # No secret configured, allow
        return True

    if not x_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook secret required",
        )

    if not hmac.compare_digest(x_webhook_secret, settings.webhook_secret):
        logger.warning("Invalid webhook secret attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook secret",
        )

    return True
