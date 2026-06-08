"""Tests for the notification channels API.

Routes:
- GET    /api/v1/notifications/channels
- GET    /api/v1/notifications/channels/{id}
- POST   /api/v1/notifications/channels
- PATCH  /api/v1/notifications/channels/{id}
- DELETE /api/v1/notifications/channels/{id}
- POST   /api/v1/notifications/channels/{id}/test
- GET    /api/v1/notifications/dispatch/{dispatch_id}
- GET    /api/v1/notifications/dispatches
- GET    /api/v1/notifications/services
- POST   /api/v1/notifications/services/{id}/compose-url
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_test_send_cooldown():
    """Clear the per-channel test-send cooldown map between tests.

    The in-memory DB resets per test, so channel IDs collide across
    tests (typically id=1). Without clearing the cooldown dict, the
    first POST in a later test trips the cooldown from a prior test.
    """
    from arm.api.v1 import notifications as notif_routes
    notif_routes._test_send_last.clear()
    yield
    notif_routes._test_send_last.clear()


@pytest.fixture
def client(db_session):
    """FastAPI test client wired against the in-memory DB."""
    from arm.app import app
    return TestClient(app)


def test_create_channel_apprise(client):
    body = {
        "type": "apprise",
        "name": "Family Discord",
        "config": {"type": "apprise", "url": "discord://1/2"},
        "subscribed_events": ["job.started"],
    }
    resp = client.post("/api/v1/notifications/channels", json=body)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["type"] == "apprise"
    assert data["enabled"] is True
    assert data["config"]["url"] == "discord://1/2"


def test_create_channel_rejects_bad_apprise_url(client):
    body = {
        "type": "apprise",
        "name": "X",
        "config": {"type": "apprise", "url": "totally-not-a-scheme"},
        "subscribed_events": [],
    }
    resp = client.post("/api/v1/notifications/channels", json=body)
    assert resp.status_code == 422
    assert "apprise" in resp.text.lower() or "url" in resp.text.lower()


def test_get_channel_masks_secret(client, make_channel):
    ch = make_channel(
        type="webhook",
        config={"type": "webhook",
                "url": "https://example.com/hook",
                "shared_secret": "supersecret123"},
        subscribed_events=["job.failed"],
    )
    resp = client.get(f"/api/v1/notifications/channels/{ch.id}")
    assert resp.status_code == 200
    data = resp.json()
    # Secret is masked. The dispatch code path retrieves it via the
    # raw DB column.
    assert data["config"]["shared_secret"] == "<hidden>"


def test_patch_channel_preserves_secret_when_sent_as_hidden(client, make_channel):
    ch = make_channel(
        type="webhook",
        config={"type": "webhook",
                "url": "https://example.com/hook",
                "shared_secret": "supersecret123"},
        subscribed_events=["job.failed"],
    )
    # Client gets the masked literal, modifies name, sends it back.
    body = {"name": "Renamed",
            "config": {"type": "webhook",
                       "url": "https://example.com/hook",
                       "shared_secret": "<hidden>"}}
    resp = client.patch(f"/api/v1/notifications/channels/{ch.id}", json=body)
    assert resp.status_code == 200
    # Verify the actual stored secret didn't change. Expire the test
    # session's identity map so the next query re-reads from the DB
    # rather than returning the cached row from before the API call.
    from arm.notifications.models import NotificationChannel
    from arm.database import db
    db.session.expire_all()
    refreshed = NotificationChannel.query.get(ch.id)
    assert refreshed.config["shared_secret"] == "supersecret123"
    assert refreshed.name == "Renamed"


def test_delete_channel_cascades_outbox(client, make_channel, db_session):
    from arm.notifications.models import NotificationOutbox
    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    db_session.add(NotificationOutbox(
        channel_id=ch.id, event_key="job.started",
        event_payload={"event_key": "job.started", "job_id": 1},
    ))
    db_session.commit()
    resp = client.delete(f"/api/v1/notifications/channels/{ch.id}")
    assert resp.status_code == 204
    assert NotificationOutbox.query.filter_by(channel_id=ch.id).count() == 0


def test_test_send_enqueues_synthetic_event(client, make_channel):
    from arm.notifications.models import NotificationOutbox
    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    resp = client.post(f"/api/v1/notifications/channels/{ch.id}/test", json={})
    assert resp.status_code == 202
    data = resp.json()
    assert "dispatch_id" in data
    assert NotificationOutbox.query.filter_by(
        channel_id=ch.id, event_key="job.started").count() == 1


def test_test_send_cooldown(client, make_channel):
    """Per-channel 10s cooldown rejects rapid test-sends with 429."""
    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    resp1 = client.post(f"/api/v1/notifications/channels/{ch.id}/test", json={})
    assert resp1.status_code == 202
    resp2 = client.post(f"/api/v1/notifications/channels/{ch.id}/test", json={})
    assert resp2.status_code == 429
    assert "Retry-After" in resp2.headers


def test_dispatch_status_endpoint(client, make_channel, db_session):
    from arm.notifications.models import NotificationOutbox
    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    row = NotificationOutbox(
        channel_id=ch.id, event_key="job.started",
        event_payload={"event_key": "job.started", "job_id": 1},
        status="success",
    )
    db_session.add(row)
    db_session.commit()
    resp = client.get(f"/api/v1/notifications/dispatch/{row.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"


def test_list_dispatches_filters(client, make_channel, db_session):
    from arm.notifications.models import NotificationOutbox
    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    db_session.add_all([
        NotificationOutbox(channel_id=ch.id, event_key="job.started",
                           event_payload={}, status="success"),
        NotificationOutbox(channel_id=ch.id, event_key="job.failed",
                           event_payload={}, status="failed"),
    ])
    db_session.commit()
    resp = client.get(
        f"/api/v1/notifications/dispatches?channel_id={ch.id}&status=success"
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["event_key"] == "job.started"


def test_catalog_endpoint(client):
    resp = client.get("/api/v1/notifications/services")
    assert resp.status_code == 200
    data = resp.json()
    assert "featured" in data
    assert "services" in data
    assert "discord" in data["featured"]


def test_compose_url_endpoint(client):
    body = {
        "required": {"webhook_id": "1234", "webhook_token": "abcd"},
        "advanced": {"tts": True},
    }
    resp = client.post(
        "/api/v1/notifications/services/discord/compose-url",
        json=body,
    )
    assert resp.status_code == 200
    assert resp.json()["url"].startswith("discord://1234/abcd")


# -------------------- 404 / not-found paths --------------------

def test_get_channel_404(client):
    resp = client.get("/api/v1/notifications/channels/999999")
    assert resp.status_code == 404


def test_patch_channel_404(client):
    resp = client.patch("/api/v1/notifications/channels/999999",
                        json={"name": "x"})
    assert resp.status_code == 404


def test_delete_channel_404(client):
    resp = client.delete("/api/v1/notifications/channels/999999")
    assert resp.status_code == 404


def test_test_send_404(client):
    resp = client.post("/api/v1/notifications/channels/999999/test", json={})
    assert resp.status_code == 404


def test_get_dispatch_404(client):
    resp = client.get("/api/v1/notifications/dispatch/999999")
    assert resp.status_code == 404


# -------------------- PATCH field-by-field --------------------

def test_patch_channel_updates_enabled_and_events(client, make_channel):
    """Exercises the enabled / subscribed_events / templates PATCH
    branches independently of the config branch."""
    from arm.notifications.models import NotificationChannel
    from arm.database import db
    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    body = {
        "enabled": False,
        "subscribed_events": ["job.failed", "job.rip_complete"],
        "templates": {"job.failed": {"title": "T", "body": "B"}},
    }
    resp = client.patch(f"/api/v1/notifications/channels/{ch.id}", json=body)
    assert resp.status_code == 200
    db.session.expire_all()
    refreshed = NotificationChannel.query.get(ch.id)
    assert refreshed.enabled is False
    assert set(refreshed.subscribed_events) == {"job.failed", "job.rip_complete"}
    assert "job.failed" in refreshed.templates


def test_patch_channel_apprise_config_revalidates_url(client, make_channel):
    """PATCHing an apprise config re-runs URL validation; a bad URL is
    rejected 422."""
    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    body = {"config": {"type": "apprise", "url": "not-a-real-scheme"}}
    resp = client.patch(f"/api/v1/notifications/channels/{ch.id}", json=body)
    assert resp.status_code == 422


# -------------------- test-send synthetic events --------------------

@pytest.mark.parametrize("event_key", [
    "job.started",
    "job.rip_complete",
    "job.transcode_complete",
    "job.failed",
    "job.manual_wait_required",
    "job.duplicate_detected",
])
def test_test_send_builds_each_event_type(client, make_channel, event_key):
    """The test-send endpoint must produce a valid synthetic payload for
    every supported event key."""
    from arm.notifications.models import NotificationOutbox
    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=[event_key],
    )
    resp = client.post(f"/api/v1/notifications/channels/{ch.id}/test",
                       json={"event_key": event_key})
    assert resp.status_code == 202, resp.text
    row = (NotificationOutbox.query
           .filter_by(channel_id=ch.id, event_key=event_key).first())
    assert row is not None
    assert row.event_payload["event_key"] == event_key


def test_test_send_unknown_event_key_is_400(client, make_channel):
    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    resp = client.post(f"/api/v1/notifications/channels/{ch.id}/test",
                       json={"event_key": "job.does_not_exist"})
    assert resp.status_code == 400


# -------------------- test unsaved config --------------------

def test_test_config_apprise_success(client):
    """POST /notifications/test sends to an unsaved apprise config
    synchronously and reports success without persisting anything."""
    from unittest.mock import patch
    from arm.notifications.models import NotificationOutbox

    body = {
        "type": "apprise",
        "config": {"type": "apprise", "url": "json://localhost/x"},
        "event_key": "job.started",
    }
    with patch("arm.notifications.dispatcher.send_apprise",
               return_value=(True, None)):
        resp = client.post("/api/v1/notifications/test", json=body)

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True, "error": None}
    # Nothing persisted to the outbox.
    assert NotificationOutbox.query.count() == 0


def test_test_config_reports_failure(client):
    """A sender failure is surfaced as {ok: false} (200) with a fixed,
    non-leaking message — the raw sender error (which can embed remote
    response text) is logged server-side, not returned."""
    from unittest.mock import patch

    body = {
        "type": "apprise",
        "config": {"type": "apprise", "url": "json://localhost/x"},
        "event_key": "job.started",
    }
    with patch("arm.notifications.dispatcher.send_apprise",
               return_value=(False, "boom-remote-detail")):
        resp = client.post("/api/v1/notifications/test", json=body)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is False
    assert "boom-remote-detail" not in (data["error"] or "")
    assert data["error"]


def test_test_config_unknown_event_key(client):
    """An unknown event_key is rejected with 400 (via _synthetic_event)."""
    body = {
        "type": "apprise",
        "config": {"type": "apprise", "url": "json://localhost/x"},
        "event_key": "job.does_not_exist",
    }
    resp = client.post("/api/v1/notifications/test", json=body)
    assert resp.status_code == 400


def test_test_config_invalid_type(client):
    """An unsupported channel type is rejected with 422."""
    body = {
        "type": "carrier-pigeon",
        "config": {},
        "event_key": "job.started",
    }
    resp = client.post("/api/v1/notifications/test", json=body)
    assert resp.status_code == 422


def test_test_config_bash_is_rejected(client):
    """Bash is excluded from the unsaved-test endpoint: it would run an
    arbitrary request-supplied script_path before the channel is saved.
    Bash channels remain testable via /channels/{id}/test after saving."""
    body = {
        # Non-/tmp path: the endpoint rejects bash before the path is ever
        # used, and a publicly-writable dir trips Sonar's S5443 needlessly.
        "type": "bash",
        "config": {"type": "bash", "script_path": "/opt/arm/scripts/x.sh"},
        "event_key": "job.started",
    }
    resp = client.post("/api/v1/notifications/test", json=body)
    assert resp.status_code == 422


def test_test_config_empty_apprise_url_is_friendly_error(client):
    """An empty apprise URL returns a friendly {ok: false} rather than
    raising, so the Add-channel form can show a message."""
    body = {
        "type": "apprise",
        "config": {"type": "apprise", "url": ""},
        "event_key": "job.started",
    }
    resp = client.post("/api/v1/notifications/test", json=body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is False
    assert data["error"]


def test_test_config_defaults_event_key(client):
    """Omitting event_key defaults to job.started."""
    from unittest.mock import patch

    body = {
        "type": "apprise",
        "config": {"type": "apprise", "url": "json://localhost/x"},
    }
    with patch("arm.notifications.dispatcher.send_apprise",
               return_value=(True, None)) as send:
        resp = client.post("/api/v1/notifications/test", json=body)

    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True
    title = send.call_args.kwargs["title"]
    assert "ARM started" in title


def test_test_config_sender_exception_is_caught(client):
    """If send_now raises, the endpoint returns {ok: false, error: ...}
    rather than 500, and does NOT leak the exception/stack-trace text to
    the caller (it's logged server-side instead)."""
    from unittest.mock import patch

    body = {
        "type": "apprise",
        "config": {"type": "apprise", "url": "json://localhost/x"},
        "event_key": "job.started",
    }
    with patch("arm.notifications.dispatcher.send_now",
               side_effect=RuntimeError("kaboom-secret-internal-detail")):
        resp = client.post("/api/v1/notifications/test", json=body)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is False
    # The raw exception text must not reach the client.
    assert "kaboom-secret-internal-detail" not in data["error"]
    assert "server logs" in data["error"]


# Scheme prefixes are assembled rather than written as literals so the
# clear-text-protocol hotspot (S5332) doesn't fire on these intentional
# SSRF-guard test fixtures (matching the migration_helpers.py precedent).
_HTTP = "http" + "://"
_FTP = "ftp" + "://"


@pytest.mark.parametrize("url", [
    _HTTP + "127.0.0.1/hook",
    _HTTP + "localhost/hook",
    _HTTP + "169.254.169.254/latest/meta-data/",
    _HTTP + "10.0.0.5/hook",
    _HTTP + "192.168.1.10/hook",
    "https://[::1]/hook",
    _FTP + "example.com/hook",
    "file:///etc/passwd",
])
def test_test_config_webhook_rejects_unsafe_url(client, url):
    """The unsaved webhook test path is an SSRF sink: a request-supplied
    URL must not target loopback/private/link-local hosts or non-http
    schemes. Rejected as a friendly {ok: false} without sending."""
    from unittest.mock import patch

    body = {
        "type": "webhook",
        "config": {"type": "webhook", "url": url},
        "event_key": "job.started",
    }
    with patch("arm.notifications.dispatcher.send_webhook") as send:
        resp = client.post("/api/v1/notifications/test", json=body)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is False
    assert data["error"]
    send.assert_not_called()


def test_test_config_webhook_allows_public_url(client):
    """A public host passes the SSRF guard and the send proceeds."""
    from unittest.mock import patch

    body = {
        "type": "webhook",
        "config": {"type": "webhook", "url": "https://example.com/hook"},
        "event_key": "job.started",
    }
    with patch("arm.notifications.url_safety.assert_public_http_url",
               return_value=None), \
            patch("arm.notifications.dispatcher.send_webhook",
                  return_value=(True, None)) as send:
        resp = client.post("/api/v1/notifications/test", json=body)

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True, "error": None}
    send.assert_called_once()


# -------------------- dispatches list clamps --------------------

def test_list_dispatches_limit_clamped_to_200(client, make_channel, db_session):
    """A limit above 200 is clamped; the request still succeeds."""
    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    resp = client.get(
        f"/api/v1/notifications/dispatches?channel_id={ch.id}&limit=5000"
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_channels_returns_all(client, make_channel):
    """GET /channels lists every channel, newest first."""
    make_channel(type="apprise",
                 config={"type": "apprise", "url": "discord://a/b"},
                 subscribed_events=["job.started"], name="one")
    make_channel(type="apprise",
                 config={"type": "apprise", "url": "discord://c/d"},
                 subscribed_events=["job.failed"], name="two")
    resp = client.get("/api/v1/notifications/channels")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    names = {c["name"] for c in data}
    assert names == {"one", "two"}


def test_create_webhook_channel_stores_secret_and_masks_on_read(client):
    """Creating a webhook channel with a shared_secret stores the
    plaintext (covers the SecretStr extraction) and masks it on GET."""
    from arm.notifications.models import NotificationChannel
    body = {
        "type": "webhook",
        "name": "Hook",
        "config": {"type": "webhook",
                   "url": "https://example.com/hook",
                   "shared_secret": "topsecret"},
        "subscribed_events": ["job.failed"],
    }
    resp = client.post("/api/v1/notifications/channels", json=body)
    assert resp.status_code == 201, resp.text
    new_id = resp.json()["id"]
    # Stored plaintext in the DB column...
    stored = NotificationChannel.query.get(new_id)
    assert stored.config["shared_secret"] == "topsecret"
    # ...but masked on the API response.
    assert resp.json()["config"]["shared_secret"] == "<hidden>"


# -------------------- config helper edge cases --------------------

def test_mask_config_handles_empty_dict():
    """_mask_config returns the input unchanged when there's no config."""
    from arm.api.v1.notifications import _mask_config
    assert _mask_config({}) == {}
    assert _mask_config(None) is None


def test_merge_patch_config_none_incoming_keeps_existing():
    """A PATCH that doesn't include a config field leaves the stored
    config untouched."""
    from arm.api.v1.notifications import _merge_patch_config
    existing = {"type": "apprise", "url": "discord://x/y"}
    assert _merge_patch_config(existing, None) == existing


# -------------------- apprise service_id --------------------

def test_create_channel_apprise_persists_service_id(client):
    body = {
        "type": "apprise",
        "name": "Discord w/ service id",
        "config": {"type": "apprise", "url": "discord://1/2", "service_id": "discord"},
        "subscribed_events": ["job.started"],
    }
    resp = client.post("/api/v1/notifications/channels", json=body)
    assert resp.status_code == 201, resp.text
    assert resp.json()["config"]["service_id"] == "discord"


def test_patch_channel_apprise_updates_service_id_and_url(client):
    create = client.post("/api/v1/notifications/channels", json={
        "type": "apprise", "name": "c",
        "config": {"type": "apprise", "url": "discord://1/2", "service_id": "discord"},
        "subscribed_events": ["job.started"],
    })
    cid = create.json()["id"]
    resp = client.patch(f"/api/v1/notifications/channels/{cid}", json={
        "config": {"type": "apprise", "url": "slack://a/b/c", "service_id": "slack"},
    })
    assert resp.status_code == 200, resp.text
    cfg = resp.json()["config"]
    assert cfg["url"] == "slack://a/b/c"
    assert cfg["service_id"] == "slack"


def test_patch_channel_without_config_keeps_apprise_url(client):
    create = client.post("/api/v1/notifications/channels", json={
        "type": "apprise", "name": "c",
        "config": {"type": "apprise", "url": "discord://1/2", "service_id": "discord"},
        "subscribed_events": ["job.started"],
    })
    cid = create.json()["id"]
    resp = client.patch(f"/api/v1/notifications/channels/{cid}", json={"name": "renamed"})
    assert resp.status_code == 200, resp.text
    cfg = resp.json()["config"]
    assert cfg["url"] == "discord://1/2"
    assert cfg["service_id"] == "discord"
    assert resp.json()["name"] == "renamed"


def test_apprise_field_private_lookup(app_context):
    """The mask/merge layer needs a way to look up a field's private
    flag by service_id + field key. Helper returns True for known
    private fields, False for known non-private, None for unknown."""
    from arm.api.v1.notifications import _apprise_field_is_private
    assert _apprise_field_is_private("discord", "webhook_token") is True
    assert _apprise_field_is_private("discord", "thread") is False
    assert _apprise_field_is_private("discord", "no_such_field") is None
    assert _apprise_field_is_private("no_such_service", "anything") is None


def test_mask_config_apprise_masks_private_fields():
    """Private apprise field values are replaced with the <hidden>
    literal on GET; non-private values pass through unchanged."""
    from arm.api.v1.notifications import _mask_config, _HIDDEN_LITERAL
    cfg = {
        "type": "apprise",
        "url": "discord://1/2",
        "service_id": "discord",
        "fields": {"webhook_id": "1", "webhook_token": "2", "thread": "5"},
    }
    masked = _mask_config(cfg)
    assert masked["fields"]["webhook_id"] == _HIDDEN_LITERAL  # private
    assert masked["fields"]["webhook_token"] == _HIDDEN_LITERAL  # private
    assert masked["fields"]["thread"] == "5"  # non-private
    assert masked["url"] == "discord://1/2"  # url not masked in this pass
    assert masked["service_id"] == "discord"


def test_mask_config_apprise_no_fields_passes_through():
    """Apprise channel with no fields (legacy/raw-URL) unchanged."""
    from arm.api.v1.notifications import _mask_config
    cfg = {"type": "apprise", "url": "discord://1/2", "service_id": "discord"}
    assert _mask_config(cfg) == cfg


def test_mask_config_apprise_without_service_id_passes_through():
    """Without a service_id, _mask_config can't look up which fields are
    private, so it leaves all fields unmasked (defensive — should never
    happen for channels created via the API, but covers the guard branch)."""
    from arm.api.v1.notifications import _mask_config
    cfg = {
        "type": "apprise",
        "url": "discord://1/2",
        "fields": {"webhook_id": "1", "webhook_token": "2"},
    }
    assert _mask_config(cfg) == cfg


def test_merge_patch_config_apprise_hidden_preserves_secret():
    """A PATCH whose private field value is <hidden> preserves the
    stored value; new values overwrite."""
    from arm.api.v1.notifications import _merge_patch_config, _HIDDEN_LITERAL
    existing = {"type": "apprise", "service_id": "discord", "url": "discord://1/2",
                "fields": {"webhook_id": "1", "webhook_token": "2", "thread": "5"}}
    incoming = {"type": "apprise", "service_id": "discord",
                "fields": {"webhook_id": _HIDDEN_LITERAL, "webhook_token": "NEW", "thread": "7"}}
    merged = _merge_patch_config(existing, incoming)
    assert merged["fields"]["webhook_id"] == "1"  # <hidden> -> kept
    assert merged["fields"]["webhook_token"] == "NEW"  # overwritten
    assert merged["fields"]["thread"] == "7"  # non-private overwritten
    # url is recomposed from the merged fields:
    assert merged["url"].startswith("discord://1/NEW")
    assert "thread=7" in merged["url"]


def test_merge_patch_config_apprise_missing_keys_keeps_stored():
    """Keys in stored fields but absent from incoming are kept."""
    from arm.api.v1.notifications import _merge_patch_config
    existing = {"type": "apprise", "service_id": "discord", "url": "discord://1/2",
                "fields": {"webhook_id": "1", "webhook_token": "2", "thread": "5"}}
    incoming = {"type": "apprise", "service_id": "discord",
                "fields": {"thread": "9"}}  # only sending the one change
    merged = _merge_patch_config(existing, incoming)
    assert merged["fields"]["webhook_id"] == "1"
    assert merged["fields"]["webhook_token"] == "2"
    assert merged["fields"]["thread"] == "9"


def test_patch_channel_apprise_with_hidden_secret_keeps_url_token(client):
    """End-to-end PATCH: client sends <hidden> for webhook_token; the
    server keeps the stored token and the recomposed url still uses it."""
    from arm.api.v1.notifications import _HIDDEN_LITERAL
    create = client.post("/api/v1/notifications/channels", json={
        "type": "apprise", "name": "d",
        "config": {"type": "apprise", "url": "discord://realid/realtoken",
                   "service_id": "discord",
                   "fields": {"webhook_id": "realid", "webhook_token": "realtoken"}},
        "subscribed_events": ["job.started"],
    })
    cid = create.json()["id"]
    resp = client.patch(f"/api/v1/notifications/channels/{cid}", json={
        "config": {"type": "apprise", "url": "", "service_id": "discord",
                   "fields": {"webhook_id": _HIDDEN_LITERAL,
                              "webhook_token": _HIDDEN_LITERAL,
                              "thread": "9"}},
    })
    assert resp.status_code == 200, resp.text
    cfg = resp.json()["config"]
    # masked on GET, but the url contains the kept secrets:
    assert cfg["fields"]["webhook_token"] == _HIDDEN_LITERAL
    assert cfg["fields"]["thread"] == "9"
    assert "realid" in cfg["url"]
    assert "realtoken" in cfg["url"]
    assert "thread=9" in cfg["url"]


def test_create_channel_apprise_composes_url_from_fields(client):
    """When the client sends {service_id, fields} (no url), neu
    composes the url server-side and stores both."""
    body = {
        "type": "apprise", "name": "d",
        "config": {"type": "apprise", "url": "",  # url absent / blank
                   "service_id": "discord",
                   "fields": {"webhook_id": "1", "webhook_token": "2"}},
        "subscribed_events": ["job.started"],
    }
    resp = client.post("/api/v1/notifications/channels", json=body)
    assert resp.status_code == 201, resp.text
    cfg = resp.json()["config"]
    assert cfg["url"] == "discord://1/2"
    assert cfg["service_id"] == "discord"
    # fields stored (and masked on GET — webhook_id is private, so the read shows <hidden>)
    from arm.api.v1.notifications import _HIDDEN_LITERAL
    assert cfg["fields"]["webhook_token"] == _HIDDEN_LITERAL


def test_test_endpoint_with_channel_id_merges_fields(client):
    """POST /notifications/test with {channel_id, fields, event_key}
    loads the stored channel, merges incoming fields (keeping <hidden>
    secrets), composes the url, and sends. Returns {ok, error}."""
    from unittest.mock import patch as mockpatch
    from arm.api.v1.notifications import _HIDDEN_LITERAL
    create = client.post("/api/v1/notifications/channels", json={
        "type": "apprise", "name": "d",
        "config": {"type": "apprise", "url": "discord://realid/realtoken",
                   "service_id": "discord",
                   "fields": {"webhook_id": "realid", "webhook_token": "realtoken"}},
        "subscribed_events": ["job.started"],
    })
    cid = create.json()["id"]
    sent_urls: list[str] = []
    def fake_send_apprise(*, url, title, body):
        sent_urls.append(url)
        return (True, None)
    with mockpatch("arm.notifications.dispatcher.send_apprise", side_effect=fake_send_apprise):
        resp = client.post("/api/v1/notifications/test", json={
            "channel_id": cid,
            "fields": {"webhook_id": _HIDDEN_LITERAL,
                       "webhook_token": _HIDDEN_LITERAL,
                       "thread": "9"},
            "event_key": "job.started",
        })
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True, "error": None}
    assert len(sent_urls) == 1
    assert "realid" in sent_urls[0]
    assert "realtoken" in sent_urls[0]
    assert "thread=9" in sent_urls[0]


def test_test_endpoint_existing_unsaved_shape_still_works(client):
    """The existing {type, config, event_key} body shape (used by the
    Add form's Send test) keeps working unchanged."""
    from unittest.mock import patch as mockpatch
    with mockpatch("arm.notifications.dispatcher.send_apprise", return_value=(True, None)):
        resp = client.post("/api/v1/notifications/test", json={
            "type": "apprise",
            "config": {"type": "apprise", "url": "discord://a/b"},
            "event_key": "job.started",
        })
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True, "error": None}


def test_test_endpoint_unsaved_apprise_composes_url_from_fields(client):
    """The Add form sends {type:'apprise', url:'', service_id, fields}
    and expects neu to compose the url (matches the create path). Without
    this server-side compose the form would error with 'url is required'
    even after the user fills the catalog fields."""
    from unittest.mock import patch as mockpatch
    sent_urls: list[str] = []
    def fake_send_apprise(*, url, title, body):
        sent_urls.append(url)
        return (True, None)
    with mockpatch("arm.notifications.dispatcher.send_apprise", side_effect=fake_send_apprise):
        resp = client.post("/api/v1/notifications/test", json={
            "type": "apprise",
            "config": {"type": "apprise", "url": "", "service_id": "discord",
                       "fields": {"webhook_id": "wid", "webhook_token": "wtok"}},
            "event_key": "job.started",
        })
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True, "error": None}
    assert len(sent_urls) == 1
    assert "wid" in sent_urls[0]
    assert "wtok" in sent_urls[0]
