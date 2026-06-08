"""Notification response shape."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class NotificationSchema(BaseModel):
    id: int
    title: str | None = None
    message: str | None = None
    trigger_time: datetime | None = None
    seen: bool = False
    cleared: bool = False

    model_config = {"from_attributes": True}
