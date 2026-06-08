"""Tests for the SQLAlchemy models that back the notifications module.

We exercise field presence and defaults via direct construction. The
real persistence path is exercised in test_outbox.py and the alembic
migration test in test_migration_helpers.py.
"""
import datetime

import pytest


def test_notification_channel_fields_match_spec():
    from arm.notifications.models import NotificationChannel
    cols = NotificationChannel.__table__.columns.keys()
    assert set(cols) == {
        "id", "type", "name", "enabled", "config",
        "subscribed_events", "templates",
        "last_fired_at", "last_success_at", "last_error",
        "created_at", "updated_at",
    }


def test_notification_outbox_fields_match_spec():
    from arm.notifications.models import NotificationOutbox
    cols = NotificationOutbox.__table__.columns.keys()
    assert set(cols) == {
        "id", "channel_id", "event_key", "event_payload",
        "status", "attempts", "next_attempt_at",
        "last_error", "created_at", "completed_at",
    }


def test_notification_outbox_status_default_is_pending():
    from arm.notifications.models import NotificationOutbox
    row = NotificationOutbox(channel_id=1, event_key="job.started",
                             event_payload={}, next_attempt_at=datetime.datetime.utcnow())
    # Defaults aren't applied until commit; check the column default directly.
    default = NotificationOutbox.__table__.columns["status"].default
    assert default is not None
    assert default.arg == "pending"


def test_notification_outbox_attempts_default_zero():
    from arm.notifications.models import NotificationOutbox
    default = NotificationOutbox.__table__.columns["attempts"].default
    assert default is not None
    assert default.arg == 0
