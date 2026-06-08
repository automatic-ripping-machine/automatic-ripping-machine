"""Tests for GET /api/config feature-flag discovery endpoint."""

from __future__ import annotations


async def test_config_endpoint_returns_flag_true_by_default(app_client):
    resp = await app_client.get("/api/config")
    assert resp.status_code == 200
    assert resp.json() == {"transcoder_enabled": True}


async def test_config_endpoint_returns_flag_false_when_disabled(ripper_only_app_client):
    resp = await ripper_only_app_client.get("/api/config")
    assert resp.status_code == 200
    assert resp.json() == {"transcoder_enabled": False}
