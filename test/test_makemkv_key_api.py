"""Tests for MakeMKV key check API endpoints."""
import unittest.mock

import pytest

from arm.database import db
from arm.models.app_state import AppState


@pytest.fixture
def app_state(app_context):
    state = AppState(id=1, ripping_paused=False, setup_complete=True)
    db.session.add(state)
    db.session.commit()
    return state


@pytest.fixture
def client(app_context):
    """FastAPI test client."""
    from arm.app import app
    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


class TestRippingEnabledKeyStatus:
    """GET /api/v1/system/ripping-enabled includes key status."""

    def test_includes_key_fields_when_never_checked(self, client, app_state):
        response = client.get('/api/v1/system/ripping-enabled')
        data = response.json()
        assert data["ripping_enabled"] is True
        assert data["makemkv_key_valid"] is None
        assert data["makemkv_key_checked_at"] is None

    def test_includes_key_fields_when_valid(self, client, app_state):
        from datetime import datetime, timezone
        app_state.makemkv_key_valid = True
        app_state.makemkv_key_checked_at = datetime(2026, 3, 22, 12, 0, 0, tzinfo=timezone.utc)
        db.session.commit()

        response = client.get('/api/v1/system/ripping-enabled')
        data = response.json()
        assert data["makemkv_key_valid"] is True
        assert data["makemkv_key_checked_at"] is not None


class TestMakemkvKeyCheck:
    """POST /api/v1/system/makemkv-key-check endpoint."""

    def test_success_returns_valid(self, client, app_state):
        with unittest.mock.patch("arm.api.v1.system.prep_mkv") as mock_prep:
            mock_prep.return_value = None
            # Simulate what prep_mkv does internally
            app_state.makemkv_key_valid = True
            db.session.commit()

            response = client.post('/api/v1/system/makemkv-key-check')

        assert response.status_code == 200
        data = response.json()
        assert data["key_valid"] is True
        assert "message" in data

    def test_failure_returns_invalid(self, client, app_state):
        from arm.ripper.makemkv import UpdateKeyRunTimeError

        with unittest.mock.patch("arm.api.v1.system.prep_mkv") as mock_prep:
            mock_prep.side_effect = UpdateKeyRunTimeError(
                40, ["bash", "/opt/arm/scripts/update_key.sh"], output=""
            )
            # Simulate what prep_mkv does internally
            app_state.makemkv_key_valid = False
            db.session.commit()

            response = client.post('/api/v1/system/makemkv-key-check')

        assert response.status_code == 200
        data = response.json()
        assert data["key_valid"] is False
        assert "message" in data
