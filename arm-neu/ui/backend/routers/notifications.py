from typing import Any

from fastapi import APIRouter, HTTPException

from backend.models.schemas import NotificationSchema
from backend.services import arm_client

router = APIRouter(prefix="/api", tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationSchema])
async def list_notifications():
    resp = await arm_client.get_notifications()
    if resp is None:
        raise HTTPException(status_code=503, detail="ARM web UI is unreachable")
    notifications = resp.get("notifications") or []
    return [NotificationSchema.model_validate(n) for n in notifications]


@router.patch("/notifications/{notify_id}", responses={502: {"description": "Failed to dismiss notification"}, 503: {"description": "ARM web UI is unreachable"}})
async def dismiss_notification(notify_id: int) -> dict[str, Any]:
    """Mark a notification as read (proxies to ARM)."""
    result = await arm_client.dismiss_notification(notify_id)
    if result is None:
        raise HTTPException(status_code=503, detail="ARM web UI is unreachable")
    if isinstance(result, dict) and result.get("success") is False:
        detail = result.get("message") or "Failed to dismiss notification"
        raise HTTPException(status_code=502, detail=detail)
    return result


# --- Channels (v4 channels system) ---

_UNREACHABLE = "ARM web UI is unreachable"


@router.get("/notifications/channels")
async def list_channels() -> Any:
    resp = await arm_client.list_channels()
    if resp is None:
        raise HTTPException(status_code=503, detail=_UNREACHABLE)
    return resp


@router.get("/notifications/channels/{channel_id}")
async def get_channel(channel_id: int) -> Any:
    resp = await arm_client.get_channel(channel_id)
    if resp is None:
        raise HTTPException(status_code=503, detail=_UNREACHABLE)
    return resp


@router.post("/notifications/channels")
async def create_channel(body: dict[str, Any]) -> Any:
    resp = await arm_client.create_channel(body)
    if resp is None:
        raise HTTPException(status_code=503, detail=_UNREACHABLE)
    return resp


@router.patch("/notifications/channels/{channel_id}")
async def update_channel(channel_id: int, body: dict[str, Any]) -> Any:
    resp = await arm_client.update_channel(channel_id, body)
    if resp is None:
        raise HTTPException(status_code=503, detail=_UNREACHABLE)
    return resp


@router.delete("/notifications/channels/{channel_id}")
async def delete_channel(channel_id: int) -> Any:
    resp = await arm_client.delete_channel(channel_id)
    if resp is None:
        raise HTTPException(status_code=503, detail=_UNREACHABLE)
    return resp


@router.post("/notifications/channels/{channel_id}/test")
async def test_send_channel(channel_id: int, body: dict[str, Any] | None = None) -> Any:
    resp = await arm_client.test_send_channel(channel_id, body or {})
    if resp is None:
        raise HTTPException(status_code=503, detail=_UNREACHABLE)
    return resp


@router.get("/notifications/dispatch/{dispatch_id}")
async def get_dispatch(dispatch_id: int) -> Any:
    resp = await arm_client.get_dispatch(dispatch_id)
    if resp is None:
        raise HTTPException(status_code=503, detail=_UNREACHABLE)
    return resp


@router.get("/notifications/dispatches")
async def list_dispatches(channel_id: int | None = None, status: str | None = None,
                          limit: int = 50) -> Any:
    resp = await arm_client.list_dispatches(channel_id=channel_id, status=status, limit=limit)
    if resp is None:
        raise HTTPException(status_code=503, detail=_UNREACHABLE)
    return resp


@router.get("/notifications/services")
async def get_services() -> Any:
    resp = await arm_client.get_services()
    if resp is None:
        raise HTTPException(status_code=503, detail=_UNREACHABLE)
    return resp


@router.post("/notifications/services/{service_id}/compose-url")
async def compose_channel_url(service_id: str, body: dict[str, Any]) -> Any:
    resp = await arm_client.compose_channel_url(service_id, body)
    if resp is None:
        raise HTTPException(status_code=503, detail=_UNREACHABLE)
    return resp


@router.post("/notifications/test")
async def test_channel_config(body: dict[str, Any]) -> Any:
    resp = await arm_client.test_channel_config(body)
    if resp is None:
        raise HTTPException(status_code=503, detail=_UNREACHABLE)
    return resp
