"""Tests for backend.routers.themes — theme API endpoints."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch

import pytest


SAMPLE_THEME = {
    "id": "test",
    "label": "Test",
    "version": 1,
    "swatch": "#ff0000",
    "tokens": {"--color-primary": "rgb(255, 0, 0)"},
    "css": '[data-scheme="test"] { color: red; }',
    "builtin": False,
}

SAMPLE_THEME_NO_CSS = {
    "id": "plain",
    "label": "Plain",
    "version": 1,
    "swatch": "#000",
    "tokens": {"--color-primary": "rgb(0, 0, 0)"},
    "css": "",
    "builtin": True,
}


# --- GET /api/themes ---

async def test_list_themes(app_client):
    themes = [{"id": "blue", "label": "Default", "tokens": {}, "builtin": True}]
    with patch("backend.routers.themes.theme_service.get_all_themes", return_value=themes):
        resp = await app_client.get("/api/themes")
    assert resp.status_code == 200
    assert resp.json() == themes


# --- GET /api/themes/{id} ---

async def test_get_theme(app_client):
    with patch("backend.routers.themes.theme_service.get_theme", return_value=SAMPLE_THEME):
        resp = await app_client.get("/api/themes/test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "test"
    assert "color: red" in data["css"]


async def test_get_theme_not_found(app_client):
    with patch("backend.routers.themes.theme_service.get_theme", return_value=None):
        resp = await app_client.get("/api/themes/nope")
    assert resp.status_code == 404


# --- GET /api/themes/{id}/download ---

async def test_download_theme(app_client):
    with patch("backend.routers.themes.theme_service.get_theme", return_value=SAMPLE_THEME):
        resp = await app_client.get("/api/themes/test/download")
    assert resp.status_code == 200
    data = resp.json()
    # Download should exclude builtin and css
    assert "builtin" not in data
    assert "css" not in data
    assert data["id"] == "test"


async def test_download_theme_not_found(app_client):
    with patch("backend.routers.themes.theme_service.get_theme", return_value=None):
        resp = await app_client.get("/api/themes/nope/download")
    assert resp.status_code == 404


# --- GET /api/themes/{id}/css ---

async def test_download_css(app_client):
    with patch("backend.routers.themes.theme_service.get_theme", return_value=SAMPLE_THEME):
        resp = await app_client.get("/api/themes/test/css")
    assert resp.status_code == 200
    assert "color: red" in resp.text


async def test_download_css_not_found(app_client):
    with patch("backend.routers.themes.theme_service.get_theme", return_value=None):
        resp = await app_client.get("/api/themes/nope/css")
    assert resp.status_code == 404


async def test_download_css_no_css(app_client):
    with patch("backend.routers.themes.theme_service.get_theme", return_value=SAMPLE_THEME_NO_CSS):
        resp = await app_client.get("/api/themes/plain/css")
    assert resp.status_code == 404
    assert "no custom CSS" in resp.json()["detail"]


# --- POST /api/themes ---

async def test_upload_theme(app_client):
    theme_data = {"id": "uploaded", "label": "Up", "tokens": {"--color-primary": "rgb(0,0,0)"}}
    saved = {**theme_data, "version": 1, "swatch": "#888888", "css": "", "builtin": False}
    with patch("backend.routers.themes.theme_service.save_user_theme", return_value=saved):
        resp = await app_client.post(
            "/api/themes",
            files={"theme_json": ("test.json", json.dumps(theme_data).encode(), "application/json")},
            data={"theme_css": ""},
        )
    assert resp.status_code == 201
    assert resp.json()["id"] == "uploaded"


async def test_upload_theme_with_css(app_client):
    theme_data = {"id": "styled", "label": "Styled", "tokens": {}}
    css = '[data-scheme="styled"] { color: blue; }'
    saved = {**theme_data, "version": 1, "swatch": "#888888", "css": css, "builtin": False}
    with patch("backend.routers.themes.theme_service.save_user_theme", return_value=saved) as mock_save:
        resp = await app_client.post(
            "/api/themes",
            files={"theme_json": ("styled.json", json.dumps(theme_data).encode(), "application/json")},
            data={"theme_css": css},
        )
    assert resp.status_code == 201
    mock_save.assert_called_once()
    call_args = mock_save.call_args
    assert call_args.kwargs["css"] == css


async def test_upload_theme_invalid_json(app_client):
    resp = await app_client.post(
        "/api/themes",
        files={"theme_json": ("bad.json", b"{not json", "application/json")},
        data={"theme_css": ""},
    )
    assert resp.status_code == 400
    assert "Invalid JSON" in resp.json()["detail"]


async def test_upload_theme_validation_error(app_client):
    theme_data = {"id": "x"}  # missing label and tokens
    with patch("backend.routers.themes.theme_service.save_user_theme", side_effect=ValueError("missing required fields")):
        resp = await app_client.post(
            "/api/themes",
            files={"theme_json": ("x.json", json.dumps(theme_data).encode(), "application/json")},
            data={"theme_css": ""},
        )
    assert resp.status_code == 400


# --- DELETE /api/themes/{id} ---

async def test_delete_theme(app_client):
    with patch("backend.routers.themes.theme_service.delete_user_theme", return_value=True):
        resp = await app_client.delete("/api/themes/mytest")
    assert resp.status_code == 200
    assert "deleted" in resp.json()["detail"]


async def test_delete_builtin_theme(app_client):
    with patch("backend.routers.themes.theme_service.delete_user_theme", return_value=False):
        resp = await app_client.delete("/api/themes/blue")
    assert resp.status_code == 400
