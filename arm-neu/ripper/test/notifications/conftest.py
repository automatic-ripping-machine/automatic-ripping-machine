"""Shared fixtures for notification tests.

Uses an in-memory SQLite database per test so persistence assertions
don't depend on the project's prod-shaped DB. The fixtures bind the
Flask-SQLAlchemy ``db`` to a temp engine, create the schema, run the
test, then tear down.
"""
import datetime
import json

import pytest
import sqlalchemy as sa
from sqlalchemy.pool import StaticPool

from arm.database import db


@pytest.fixture(autouse=True)
def _clear_catalog_cache():
    """Clear build_catalog() cache before each test so mocks work."""
    from arm.notifications.catalog import build_catalog
    build_catalog.cache_clear()
    yield
    build_catalog.cache_clear()


@pytest.fixture
def db_session(app_context):
    """Use the shared app_context fixture from test/conftest.py which
    already provides a clean in-memory DB with all models loaded."""
    _, db_obj = app_context
    yield db_obj.session


@pytest.fixture
def make_channel(db_session):
    """Factory for NotificationChannel rows."""
    from arm.notifications.models import NotificationChannel

    def _factory(*, type, config, subscribed_events,
                 name="test channel", enabled=True, templates=None):
        ch = NotificationChannel(
            type=type, name=name, enabled=enabled,
            config=config,
            subscribed_events=subscribed_events,
            templates=templates or {},
        )
        db_session.add(ch)
        db_session.commit()
        return ch

    return _factory
