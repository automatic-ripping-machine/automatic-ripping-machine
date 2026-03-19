"""Tests for the setup wizard API endpoints (arm/api/v1/setup.py)."""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app_context):
    """FastAPI test client."""
    from arm.app import app
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


class TestSetupStatus:
    """Test GET /api/v1/setup/status endpoint."""

    def test_returns_200(self, client):
        response = client.get('/api/v1/setup/status')
        assert response.status_code == 200

    def test_returns_required_fields(self, client):
        response = client.get('/api/v1/setup/status')
        data = response.json()
        assert 'db_exists' in data
        assert 'db_initialized' in data
        assert 'db_current' in data
        assert 'first_run' in data
        assert 'arm_version' in data
        assert 'setup_steps' in data

    def test_first_run_true_on_fresh_db(self, client):
        """Fresh DB has setup_complete=False, so first_run should be True."""
        response = client.get('/api/v1/setup/status')
        data = response.json()
        assert data['first_run'] is True

    def test_setup_steps_database_present(self, client):
        """Database step should be present in setup_steps."""
        response = client.get('/api/v1/setup/status')
        data = response.json()
        assert 'database' in data['setup_steps']
        assert data['setup_steps']['database'] in ('complete', 'pending')

    def test_setup_steps_settings_pending(self, client):
        """Fresh DB has setup_complete=False, so settings_reviewed should be pending."""
        response = client.get('/api/v1/setup/status')
        data = response.json()
        assert data['setup_steps']['settings_reviewed'] == 'pending'

    def test_drives_step_shows_count(self, client):
        """Drives step should show a count string."""
        response = client.get('/api/v1/setup/status')
        data = response.json()
        assert 'detected' in data['setup_steps']['drives']

    def test_first_run_false_after_complete(self, client):
        """After completing setup, first_run should be False."""
        client.post('/api/v1/setup/complete')
        response = client.get('/api/v1/setup/status')
        data = response.json()
        assert data['first_run'] is False

    def test_db_not_initialized_when_check_fails(self, client):
        """When arm_db_check raises, db_initialized should be False."""
        with patch('arm.api.v1.setup.arm_db_check', side_effect=Exception('fail')):
            response = client.get('/api/v1/setup/status')
            data = response.json()
            assert data['db_initialized'] is False

    def test_arm_version_returned(self, client):
        """Should return a version string."""
        response = client.get('/api/v1/setup/status')
        data = response.json()
        assert isinstance(data['arm_version'], str)


class TestSetupComplete:
    """Test POST /api/v1/setup/complete endpoint."""

    def test_returns_success(self, client):
        response = client.post('/api/v1/setup/complete')
        assert response.status_code == 200
        assert response.json()['success'] is True

    def test_sets_setup_complete_flag(self, client):
        """After POST, AppState.setup_complete should be True."""
        client.post('/api/v1/setup/complete')

        from arm.models.app_state import AppState
        state = AppState.get()
        assert state.setup_complete is True

    def test_idempotent(self, client):
        """Calling complete twice should not error."""
        resp1 = client.post('/api/v1/setup/complete')
        resp2 = client.post('/api/v1/setup/complete')
        assert resp1.status_code == 200
        assert resp2.status_code == 200

    def test_complete_then_status_shows_done(self, client):
        """After completing, settings_reviewed should show complete."""
        client.post('/api/v1/setup/complete')
        response = client.get('/api/v1/setup/status')
        data = response.json()
        assert data['setup_steps']['settings_reviewed'] == 'complete'
        assert data['first_run'] is False
