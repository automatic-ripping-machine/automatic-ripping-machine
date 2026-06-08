"""API v1 - Notification endpoints."""
import datetime
import logging

from fastapi import APIRouter

from arm.database import db
from arm.models.notifications import Notifications
from arm.services import jobs as svc_jobs

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["notifications"])


@router.get('/notifications')
def list_notifications(include_cleared: bool = False):
    """List notifications, newest first. Excludes cleared by default."""
    query = Notifications.query
    if not include_cleared:
        query = query.filter(Notifications.cleared == False)  # noqa: E712
    notifications = query.order_by(Notifications.trigger_time.desc()).all()
    return {
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "seen": n.seen,
                "cleared": n.cleared,
                "trigger_time": n.trigger_time.isoformat() if n.trigger_time else None,
                "dismiss_time": n.dismiss_time.isoformat() if n.dismiss_time else None,
            }
            for n in notifications
        ],
    }


@router.get('/notifications/count')
def notification_count():
    """Return notification counts by status."""
    total = Notifications.query.count()
    unseen = Notifications.query.filter(
        Notifications.seen == False  # noqa: E712
    ).count()
    cleared = Notifications.query.filter(
        Notifications.cleared == True  # noqa: E712
    ).count()
    seen = total - unseen - cleared
    return {
        "unseen": unseen,
        "seen": seen,
        "cleared": cleared,
        "total": total,
    }


@router.post('/notifications/dismiss-all')
def dismiss_all_notifications():
    """Mark all unseen notifications as seen."""
    now = datetime.datetime.now()
    count = (
        Notifications.query
        .filter(Notifications.seen == False)  # noqa: E712
        .update({"seen": True, "dismiss_time": now})
    )
    db.session.commit()
    return {"success": True, "count": count}


@router.post('/notifications/purge')
def purge_cleared_notifications():
    """Hard-delete all cleared notifications."""
    count = (
        Notifications.query
        .filter(Notifications.cleared == True)  # noqa: E712
        .delete()
    )
    db.session.commit()
    return {"success": True, "count": count}


@router.patch('/notifications/{notify_id}')
def read_notification(notify_id: int):
    """Mark a notification as read."""
    return svc_jobs.read_notification(str(notify_id))


# -------------------- Channels CRUD --------------------

from typing import Any  # noqa: E402

from fastapi import HTTPException  # noqa: E402

from arm_contracts import (  # noqa: E402
    ChannelCreate,
    ChannelUpdate,
)
from arm.notifications.models import (  # noqa: E402
    NotificationChannel,
    NotificationOutbox,
)
from arm.notifications import catalog as catalog_module  # noqa: E402
from arm.notifications.url_composer import compose_apprise_url  # noqa: E402

_HIDDEN_LITERAL = "<hidden>"
# Per-channel test-send cooldown (seconds). Tracked in-memory; resets
# on process restart. Sufficient for single-user setups.
_TEST_SEND_COOLDOWN_SECONDS = 10
_test_send_last: dict[int, datetime.datetime] = {}


def _apprise_field_is_private(service_id: str, key: str) -> bool | None:
    """Look up a field's `private` flag from the apprise catalog.
    Returns True/False if found, None for unknown service or key."""
    from arm.notifications.catalog import build_catalog
    cat = build_catalog()
    svc = next((s for s in cat["services"] if s["id"] == service_id), None)
    if svc is None:
        return None
    for f in [*svc.get("required_fields", []), *svc.get("advanced_fields", [])]:
        if f["key"] == key:
            return bool(f.get("private"))
    return None


def _compose_apprise_url_from_fields(
    service_id: str | None, fields: dict
) -> str | None:
    """Compose an apprise url from a flat fields dict.

    Looks up `service_id` in the catalog, partitions `fields` into
    required vs advanced by the catalog's `required_fields` keys, and
    returns the composed url. Returns None when service_id is missing
    or unknown (callers decide whether that's an error)."""
    if not service_id:
        return None
    from arm.notifications.catalog import build_catalog
    from arm.notifications.url_composer import compose_apprise_url
    cat = build_catalog()
    svc = next((s for s in cat["services"] if s["id"] == service_id), None)
    if svc is None:
        return None
    required_keys = {f["key"] for f in svc.get("required_fields", [])}
    return compose_apprise_url(
        service_id=service_id,
        required={k: v for k, v in fields.items() if k in required_keys},
        advanced={k: v for k, v in fields.items() if k not in required_keys},
    )


def _mask_config(cfg: dict) -> dict:
    """Replace secret fields with the masked literal for GET responses."""
    if not cfg:
        return cfg
    out = dict(cfg)
    if cfg.get("type") == "webhook" and "shared_secret" in cfg:
        if cfg["shared_secret"]:
            out["shared_secret"] = _HIDDEN_LITERAL
    if cfg.get("type") == "apprise" and isinstance(cfg.get("fields"), dict):
        service_id = cfg.get("service_id")
        masked_fields: dict = {}
        for k, v in cfg["fields"].items():
            if service_id and _apprise_field_is_private(service_id, k) is True and v:
                masked_fields[k] = _HIDDEN_LITERAL
            else:
                masked_fields[k] = v
        out["fields"] = masked_fields
    return out


def _merge_patch_config(existing: dict, incoming: dict | None) -> dict:
    """When the client sends a PATCH with config.<secret>=<hidden>,
    preserve the existing secret instead of overwriting it.
    For apprise channels, also merge `fields` per-key and recompose
    `url` from the merged fields."""
    if incoming is None:
        return existing
    merged = dict(incoming)
    # Webhook shared_secret (existing behavior).
    if (
        existing.get("type") == "webhook"
        and merged.get("type") == "webhook"
        and merged.get("shared_secret") == _HIDDEN_LITERAL
    ):
        merged["shared_secret"] = existing.get("shared_secret")
    # Apprise per-field merge + url recompose.
    if (
        existing.get("type") == "apprise"
        and merged.get("type") == "apprise"
        and isinstance(merged.get("fields"), dict)
    ):
        service_id = merged.get("service_id") or existing.get("service_id")
        stored_fields = existing.get("fields") or {}
        merged_fields: dict = dict(stored_fields)  # start from stored
        for k, v in merged["fields"].items():
            # <hidden> on a private field -> keep stored value
            if (
                _apprise_field_is_private(service_id, k) is True
                and v == _HIDDEN_LITERAL
            ):
                continue  # keep stored
            merged_fields[k] = v
        merged["fields"] = merged_fields
        merged["service_id"] = service_id
        # Recompose url from merged fields.
        composed = _compose_apprise_url_from_fields(service_id, merged_fields)
        if composed is not None:
            merged["url"] = composed
    return merged


def _channel_to_out_dict(ch: NotificationChannel) -> dict:
    """Serialize a DB row to the Channel API shape with secrets masked."""
    return {
        "id": ch.id,
        "type": ch.type,
        "name": ch.name,
        "enabled": ch.enabled,
        "config": _mask_config(ch.config),
        "subscribed_events": ch.subscribed_events or [],
        "templates": ch.templates or {},
        "last_fired_at": ch.last_fired_at.isoformat() if ch.last_fired_at else None,
        "last_success_at": ch.last_success_at.isoformat() if ch.last_success_at else None,
        "last_error": ch.last_error,
    }


def _validate_apprise_url(url: str) -> None:
    """Reject URLs that apprise can't parse before saving the channel."""
    import apprise
    a = apprise.Apprise()
    if not a.add(url):
        raise HTTPException(
            status_code=422,
            detail=f"apprise rejected URL: {url}",
        )


@router.get("/notifications/channels")
def list_channels():
    rows = NotificationChannel.query.order_by(
        NotificationChannel.created_at.desc()).all()
    return [_channel_to_out_dict(r) for r in rows]


@router.get("/notifications/channels/{channel_id}")
def get_channel(channel_id: int):
    ch = NotificationChannel.query.get(channel_id)
    if ch is None:
        raise HTTPException(404, "channel not found")
    return _channel_to_out_dict(ch)


@router.post("/notifications/channels", status_code=201)
def create_channel(payload: ChannelCreate):
    config_dict = payload.config.model_dump(mode="json")
    # SecretStr -> plaintext for storage.
    if payload.config.type == "webhook":
        sec = payload.config.shared_secret
        config_dict["shared_secret"] = (
            sec.get_secret_value() if sec is not None else None
        )
    # Apprise: if the client sent {service_id, fields} (no url), compose
    # server-side. Otherwise validate the provided url as before.
    if payload.config.type == "apprise":
        fields = config_dict.get("fields") or {}
        service_id = config_dict.get("service_id")
        if fields and service_id and not config_dict.get("url"):
            composed = _compose_apprise_url_from_fields(service_id, fields)
            if composed is not None:
                config_dict["url"] = composed
        _validate_apprise_url(config_dict.get("url", ""))
    ch = NotificationChannel(
        type=payload.type,
        name=payload.name,
        enabled=payload.enabled,
        config=config_dict,
        subscribed_events=list(payload.subscribed_events),
        templates={k: v.model_dump() for k, v in payload.templates.items()},
    )
    db.session.add(ch)
    db.session.commit()
    return _channel_to_out_dict(ch)


@router.patch("/notifications/channels/{channel_id}")
def patch_channel(channel_id: int, payload: ChannelUpdate):
    ch = NotificationChannel.query.get(channel_id)
    if ch is None:
        raise HTTPException(404, "channel not found")

    if payload.name is not None:
        ch.name = payload.name
    if payload.enabled is not None:
        ch.enabled = payload.enabled
    if payload.subscribed_events is not None:
        ch.subscribed_events = list(payload.subscribed_events)
    if payload.templates is not None:
        ch.templates = {k: v.model_dump() for k, v in payload.templates.items()}
    if payload.config is not None:
        incoming = payload.config.model_dump(mode="json")
        if payload.config.type == "webhook":
            sec = payload.config.shared_secret
            incoming["shared_secret"] = (
                sec.get_secret_value() if sec is not None else None
            )
        if payload.config.type == "apprise" and payload.config.url:
            _validate_apprise_url(payload.config.url)
        ch.config = _merge_patch_config(ch.config or {}, incoming)
    db.session.commit()
    return _channel_to_out_dict(ch)


@router.delete("/notifications/channels/{channel_id}", status_code=204)
def delete_channel(channel_id: int):
    ch = NotificationChannel.query.get(channel_id)
    if ch is None:
        raise HTTPException(404, "channel not found")
    # Cascade is declared in the FK; explicitly remove outbox rows for
    # SQLite where ON DELETE CASCADE isn't always honored.
    NotificationOutbox.query.filter_by(channel_id=channel_id).delete()
    db.session.delete(ch)
    db.session.commit()
    return None


# -------------------- Test send --------------------

def _synthetic_event(event_key: str) -> dict:
    """A placeholder event payload used by the test-send endpoint."""
    from uuid import uuid4
    base = {
        "event_id": str(uuid4()),
        "occurred_at": datetime.datetime.utcnow().isoformat(),
        "job_id": 0,
        "job_title": "ARM Test",
        "job_disc_type": "dvd",
        "job_imdb_id": None,
    }
    if event_key == "job.started":
        return {**base, "event_key": event_key, "drive_mount": "/dev/sr0"}
    if event_key == "job.rip_complete":
        return {**base, "event_key": event_key,
                "rip_duration_seconds": 0, "track_count": 0}
    if event_key == "job.transcode_complete":
        return {**base, "event_key": event_key,
                "transcode_duration_seconds": 0, "output_path": "/test"}
    if event_key == "job.failed":
        return {**base, "event_key": event_key,
                "phase": "rip",
                "error_message": "test send",
                "error_code": None}
    if event_key == "job.manual_wait_required":
        return {**base, "event_key": event_key,
                "wait_minutes_remaining": 0,
                "reason": "manual_mode_activated"}
    if event_key == "job.duplicate_detected":
        return {**base, "event_key": event_key,
                "existing_job_id": 0,
                "existing_output_path": None}
    raise HTTPException(400, f"unknown event_key: {event_key}")


@router.post("/notifications/channels/{channel_id}/test", status_code=202)
def test_send(channel_id: int, body: dict | None = None):
    ch = NotificationChannel.query.get(channel_id)
    if ch is None:
        raise HTTPException(404, "channel not found")

    now = datetime.datetime.utcnow()
    last = _test_send_last.get(channel_id)
    if last and (now - last).total_seconds() < _TEST_SEND_COOLDOWN_SECONDS:
        remaining = int(
            _TEST_SEND_COOLDOWN_SECONDS - (now - last).total_seconds())
        raise HTTPException(
            status_code=429,
            detail=f"test send cooldown, retry in {remaining}s",
            headers={"Retry-After": str(remaining)},
        )
    _test_send_last[channel_id] = now

    event_key = (body or {}).get("event_key", "job.started")
    payload = _synthetic_event(event_key)

    row = NotificationOutbox(
        channel_id=channel_id,
        event_key=event_key,
        event_payload=payload,
        status="pending",
        attempts=0,
        next_attempt_at=now,
    )
    db.session.add(row)
    db.session.commit()
    return {"sent_at": now.isoformat(), "dispatch_id": row.id}


@router.post("/notifications/test")
def test_config(body: dict):
    """Test-send. Two body shapes:

    - {type, config, event_key?} — unsaved test (Add form). Existing.
    - {channel_id, fields, event_key?} — saved channel with re-entered
      fields (editor Send test). Loads stored config, merges fields
      per the same <hidden>-preserve rules as PATCH, composes the url,
      sends synchronously. Returns {ok, error}.

    Only ``apprise`` and ``webhook`` (URL-based senders) can be tested
    unsaved. ``bash`` is intentionally excluded: it would execute an
    arbitrary request-supplied ``script_path`` before the channel is
    persisted. Bash channels are still testable via
    ``/channels/{id}/test`` after they're saved, where the operator has
    already committed the script path to the DB.
    """
    from arm.notifications.dispatcher import send_now, _reconstruct_event
    from arm.notifications.url_safety import (
        UnsafeUrlError,
        assert_public_http_url,
    )

    event_key = body.get("event_key", "job.started")

    # Branch A: saved-channel test with re-entered fields.
    if "channel_id" in body:
        ch = NotificationChannel.query.get(body["channel_id"])
        if ch is None:
            raise HTTPException(404, "channel not found")
        if ch.type != "apprise":
            raise HTTPException(422, "channel_id test path supports apprise only")
        incoming_fields = body.get("fields") or {}
        merged = _merge_patch_config(
            ch.config or {},
            {"type": "apprise", "service_id": ch.config.get("service_id"),
             "fields": incoming_fields},
        )
        url = merged.get("url")
        if not url:
            return {"ok": False, "error": "could not compose url from fields"}
        payload = _synthetic_event(event_key)
        event = _reconstruct_event(payload)
        try:
            ok, error = send_now("apprise", {"type": "apprise", "url": url}, event)
        except Exception:
            log.exception("editor apprise test send failed")
            return {"ok": False, "error": "test send failed; see server logs"}
        if ok:
            return {"ok": True, "error": None}
        log.warning("editor apprise test send failed: %s", error)
        return {"ok": False, "error": "test send failed; see server logs"}

    # Branch B: existing unsaved-config test (Add form).
    ch_type = body.get("type")
    if ch_type not in ("apprise", "webhook"):
        raise HTTPException(422, "unsaved test supports only apprise and webhook")
    config = body.get("config") or {}

    # The UI's apprise create path sends {service_id, fields} with url=""
    # and lets neu compose the url server-side (matches the create_channel
    # contract). Compose here too so the unsaved-test path works the same
    # as the create path — otherwise users hit "url is required" after
    # filling fields on the Add form.
    if (
        ch_type == "apprise"
        and not config.get("url")
        and isinstance(config.get("fields"), dict)
        and config.get("service_id")
    ):
        composed = _compose_apprise_url_from_fields(
            config["service_id"], config["fields"]
        )
        if composed:
            config = {**config, "url": composed}

    # Friendly (non-raising) validation so the form shows a message.
    url = config.get("url")
    if not url:
        return {"ok": False, "error": "url is required"}

    # The webhook sender fetches this URL directly with the server's
    # network identity, so a request-supplied URL is an SSRF risk. Apprise
    # URLs route through the apprise library against known service hosts.
    if ch_type == "webhook":
        try:
            assert_public_http_url(url)
        except UnsafeUrlError:
            # Fixed message: never echo the exception text (which could
            # reflect the resolved host) back to the caller.
            return {
                "ok": False,
                "error": "URL must be a public http(s) address",
            }

    payload = _synthetic_event(event_key)  # raises 400 on unknown key
    event = _reconstruct_event(payload)
    try:
        ok, error = send_now(ch_type, config, event)
    except Exception:
        # Don't echo exception/stack-trace text back to the caller.
        log.exception("unsaved %s test failed", ch_type)
        return {"ok": False, "error": "test send failed; see server logs"}
    if ok:
        return {"ok": True, "error": None}
    # The sender's error string can embed remote response text / exception
    # detail; log it server-side and return a fixed message instead.
    log.warning("unsaved %s test send failed: %s", ch_type, error)
    return {"ok": False, "error": "test send failed; see server logs"}


@router.get("/notifications/dispatch/{dispatch_id}")
def get_dispatch(dispatch_id: int):
    row = NotificationOutbox.query.get(dispatch_id)
    if row is None:
        raise HTTPException(404, "dispatch not found")
    return {
        "id": row.id,
        "status": row.status,
        "attempts": row.attempts,
        "last_error": row.last_error,
        "completed_at": (row.completed_at.isoformat()
                         if row.completed_at else None),
    }


@router.get("/notifications/dispatches")
def list_dispatches(
    channel_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
):
    if limit > 200:
        limit = 200
    q = NotificationOutbox.query
    if channel_id is not None:
        q = q.filter_by(channel_id=channel_id)
    if status is not None:
        q = q.filter_by(status=status)
    rows = q.order_by(NotificationOutbox.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "channel_id": r.channel_id,
            "event_key": r.event_key,
            "status": r.status,
            "attempts": r.attempts,
            "last_error": r.last_error,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": (r.completed_at.isoformat()
                             if r.completed_at else None),
        }
        for r in rows
    ]


# -------------------- Catalog --------------------

_catalog_cache: dict | None = None


@router.get("/notifications/services")
def get_services():
    """Apprise service catalog. Cached in-process for the lifetime of
    the worker — restarting picks up apprise updates."""
    global _catalog_cache
    if _catalog_cache is None:
        _catalog_cache = catalog_module.build_catalog()
    return _catalog_cache


@router.post("/notifications/services/{service_id}/compose-url")
def compose_url(service_id: str, body: dict):
    required = body.get("required") or {}
    advanced = body.get("advanced") or {}
    url = compose_apprise_url(
        service_id=service_id, required=required, advanced=advanced)
    return {"url": url}
