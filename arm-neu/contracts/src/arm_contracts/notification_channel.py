"""Notification channel models.

A "channel" is one user-configured destination (a Discord webhook URL,
an outbound HTTPS endpoint with optional HMAC, a local bash script).
The channel-config discriminated union encodes the type-specific shape;
the ``Channel`` model wraps it with lifecycle metadata exposed via the
neu API.

The four valid event keys come from ``notification_event.NotificationEvent``;
they are duplicated here as a ``Literal`` so the dependency only runs in
one direction. If a fifth event is ever added, both lists must update —
the round-trip tests guard the constraint.
"""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr


class AppriseChannelConfig(BaseModel):
    """An Apprise URL such as ``discord://id/token`` or
    ``pover://user@token``. neu's compose-url endpoint assembles the
    final string from the catalog form; the user may also paste a raw
    URL directly. ``service_id`` records which catalog service produced
    the URL so the editor can re-render that service's fields.
    ``fields`` carries the per-field values (e.g. {"webhook_id": "...",
    "webhook_token": "..."}). Secrets should be masked by the caller;
    arm-neu's API layer uses the literal "<hidden>" sentinel for that
    round-trip."""
    model_config = ConfigDict(extra="ignore")
    type: Literal["apprise"] = "apprise"
    url: str
    service_id: str | None = None
    fields: dict[str, str | int | float | bool] | None = None


class WebhookChannelConfig(BaseModel):
    """Rich-payload HTTPS webhook. If ``shared_secret`` is set, the
    dispatcher computes HMAC-SHA256 over the canonical JSON body and
    sends it in ``X-ARM-Signature: sha256=<hex>``. ``headers`` is a
    flat map of extra static headers (e.g. ``Authorization: Bearer …``)
    that the user wants on every send."""
    model_config = ConfigDict(extra="ignore")
    type: Literal["webhook"] = "webhook"
    url: HttpUrl
    shared_secret: SecretStr | None = None
    headers: dict[str, str] | None = None


class BashChannelConfig(BaseModel):
    """Local script run as a subprocess. Job context is passed via
    ``ARM_*`` env vars; the exact list is pinned in sub-spec 2."""
    model_config = ConfigDict(extra="ignore")
    type: Literal["bash"] = "bash"
    script_path: str


ChannelConfig = Annotated[
    AppriseChannelConfig | WebhookChannelConfig | BashChannelConfig,
    Field(discriminator="type"),
]
"""Discriminated union of channel configs. Stored as JSON in the
``notification_channel.config`` column."""


EventKey = Literal[
    "job.started",
    "job.rip_complete",
    "job.transcode_complete",
    "job.failed",
    "job.manual_wait_required",
    "job.duplicate_detected",
]
"""The set of event_key values a channel may subscribe to. Must stay
in sync with ``notification_event.NotificationEvent``'s discriminator
literals; the ``test_event_keys_literal_matches_event_union`` test
in ``tests/test_notification_channel.py`` enforces this."""


class ChannelTemplate(BaseModel):
    """Per-event title/body override. ``None`` means 'use the default
    template for this event' — the dispatcher resolves defaults from
    a static map keyed off event_key in arm-neu."""
    model_config = ConfigDict(extra="ignore")
    title: str | None = None
    body: str | None = None


class Channel(BaseModel):
    """API representation of a configured notification channel.

    Storage-only fields (``created_at``, ``updated_at``) live on the
    SQLAlchemy model in arm-neu and are intentionally not exposed via
    the API — keep them off this model.

    Secret values inside ``config`` (e.g. ``WebhookChannelConfig.shared_secret``)
    are returned masked when this model is serialized by the API layer;
    see neu's API layer for the ``<hidden>``-roundtrip rule on PATCH.
    """
    model_config = ConfigDict(extra="ignore")

    id: int
    type: Literal["apprise", "webhook", "bash"]
    name: str
    enabled: bool
    config: ChannelConfig
    subscribed_events: list[EventKey]
    templates: dict[EventKey, ChannelTemplate] = Field(default_factory=dict)
    last_fired_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None


class ChannelCreate(BaseModel):
    """POST /api/v1/notifications/channels body. ``id``, ``last_*``
    fields are excluded (server-assigned)."""
    model_config = ConfigDict(extra="ignore")

    type: Literal["apprise", "webhook", "bash"]
    name: str
    enabled: bool = True
    config: ChannelConfig
    subscribed_events: list[EventKey] = Field(default_factory=list)
    templates: dict[EventKey, ChannelTemplate] = Field(default_factory=dict)


class ChannelUpdate(BaseModel):
    """PATCH /api/v1/notifications/channels/{id} body. All fields
    optional — only provided keys are applied. The API layer enforces
    the ``<hidden>``-literal roundtrip rule for ``SecretStr`` fields
    inside ``config``."""
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    enabled: bool | None = None
    config: ChannelConfig | None = None
    subscribed_events: list[EventKey] | None = None
    templates: dict[EventKey, ChannelTemplate] | None = None
