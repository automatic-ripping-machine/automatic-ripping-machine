"""SQLAlchemy models for notification channels and the dispatch outbox.

These tables back the user-facing notification redesign. They are
module-internal: no other arm-neu module should query them directly.
All access goes through the public ``publish_event`` function and the
FastAPI router in ``arm.notifications.api``.
"""
import datetime

from arm.database import db


class NotificationChannel(db.Model):
    """One user-configured channel instance (a Discord webhook, an
    HMAC-signed outbound webhook, a local bash script).

    The ``type`` column duplicates ``config["type"]`` for query
    efficiency; the API layer (Channel Pydantic model) enforces they
    match. ``subscribed_events`` and ``templates`` are JSON columns
    because they are user-editable lists/maps that are read on every
    dispatch — splitting them into separate tables would not pay off
    at single-user scale.
    """
    __tablename__ = "notification_channel"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type = db.Column(db.String(16), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    config = db.Column(db.JSON, nullable=False)
    subscribed_events = db.Column(db.JSON, nullable=False, default=list)
    templates = db.Column(db.JSON, nullable=False, default=dict)

    last_fired_at = db.Column(db.DateTime, nullable=True)
    last_success_at = db.Column(db.DateTime, nullable=True)
    last_error = db.Column(db.String(512), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.datetime.utcnow,
                           onupdate=datetime.datetime.utcnow)


class NotificationOutbox(db.Model):
    """One pending or completed dispatch attempt for a single channel.

    The dispatcher polls ``(status='pending', next_attempt_at <= now)``
    rows, marks them ``in_flight``, attempts the send, then transitions
    to ``success`` or ``pending`` (with backoff) or ``failed``. The
    ``in_flight`` reaper on startup rescues rows abandoned mid-flight
    by a crash.
    """
    __tablename__ = "notification_outbox"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    channel_id = db.Column(db.Integer,
                           db.ForeignKey("notification_channel.id",
                                         ondelete="CASCADE"),
                           nullable=False, index=True)
    event_key = db.Column(db.String(64), nullable=False)
    event_payload = db.Column(db.JSON, nullable=False)

    status = db.Column(db.String(16), nullable=False, default="pending",
                       index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    next_attempt_at = db.Column(db.DateTime, nullable=False,
                                default=datetime.datetime.utcnow,
                                index=True)
    last_error = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index("ix_notification_outbox_status_next",
                 "status", "next_attempt_at"),
    )
