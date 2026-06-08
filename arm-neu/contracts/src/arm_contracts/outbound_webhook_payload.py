"""OutboundWebhookPayload: the rich-payload wire shape sent by arm-neu's
notification dispatcher to user-configured webhook channels.

Distinct from Apprise's ``json://`` envelope (which uses Apprise's
generic ``{title, body, type, version, tag}`` shape). This payload
carries the full ``NotificationEvent`` so subscribers can react to job
state programmatically.

When the channel has a ``shared_secret``, the dispatcher computes
HMAC-SHA256 over the canonical JSON-serialized body and sends it in
``X-ARM-Signature: sha256=<hex>``. Schema version is locked at 1; any
breaking change to the wire shape bumps this number and triggers a
contracts major release.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from arm_contracts.notification_event import NotificationEvent


class ChannelRef(BaseModel):
    """Compact reference to the channel that produced this send, embedded
    in the outbound payload so subscribers can correlate without storing
    the full channel record."""
    model_config = ConfigDict(extra="ignore")
    id: int
    name: str
    type: Literal["apprise", "webhook", "bash"]


class OutboundWebhookPayload(BaseModel):
    """Body POSTed to webhook channels. The ``event`` field carries the
    full discriminated event; ``title`` and ``body`` are pre-rendered
    from the channel's template (or its event-default if the channel
    didn't override it)."""
    model_config = ConfigDict(extra="ignore")

    schema_version: Literal[1] = 1
    event: NotificationEvent
    title: str
    body: str
    channel: ChannelRef
    arm_instance_name: str | None = None
    sent_at: datetime
