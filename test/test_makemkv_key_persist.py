"""Tests for prep_mkv() persisting key validity to AppState."""
import subprocess
import unittest.mock

import pytest

from arm.database import db
from arm.models.app_state import AppState


@pytest.fixture
def app_state(app_context):
    """Ensure AppState singleton exists."""
    state = AppState(id=1, ripping_paused=False, setup_complete=True)
    db.session.add(state)
    db.session.commit()
    return state


class TestPrepMkvPersistence:
    def test_success_persists_valid(self, app_state):
        """On successful key update, AppState.makemkv_key_valid is True."""
        with unittest.mock.patch("arm.ripper.makemkv.subprocess.run") as mock_run, \
             unittest.mock.patch("arm.ripper.makemkv.cfg.arm_config", {
                 "INSTALLPATH": "/opt/arm",
                 "MAKEMKV_PERMA_KEY": "",
             }):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=b"Key updated"
            )
            from arm.ripper.makemkv import prep_mkv
            prep_mkv()

        state = AppState.get()
        assert state.makemkv_key_valid is True
        assert state.makemkv_key_checked_at is not None

    def test_failure_persists_invalid(self, app_state):
        """On UpdateKeyRunTimeError, AppState.makemkv_key_valid is False."""
        from arm.ripper.makemkv import prep_mkv, UpdateKeyRunTimeError

        with unittest.mock.patch("arm.ripper.makemkv.subprocess.run") as mock_run, \
             unittest.mock.patch("arm.ripper.makemkv.cfg.arm_config", {
                 "INSTALLPATH": "/opt/arm",
                 "MAKEMKV_PERMA_KEY": "",
             }):
            mock_run.side_effect = subprocess.CalledProcessError(
                40, ["bash", "/opt/arm/scripts/update_key.sh"], output=b""
            )
            with pytest.raises(UpdateKeyRunTimeError):
                prep_mkv()

        state = AppState.get()
        assert state.makemkv_key_valid is False
        assert state.makemkv_key_checked_at is not None
