"""Smoke test for the ripper_only_app_client fixture."""

from __future__ import annotations


async def test_ripper_only_fixture_sets_flag_off(ripper_only_app_client):
    from backend.config import settings
    assert settings.transcoder_enabled is False


async def test_ripper_only_fixture_restores_default(app_client):
    """After a ripper_only_app_client test, the default app_client keeps flag True."""
    from backend.config import settings
    assert settings.transcoder_enabled is True
