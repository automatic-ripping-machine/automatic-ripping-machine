"""Tests for backend.services.themes — theme loading, saving, deletion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.services import themes as theme_service


@pytest.fixture
def tmp_themes(tmp_path):
    """Set up builtin + user theme directories with test data."""
    builtin = tmp_path / "builtin"
    builtin.mkdir()
    user = tmp_path / "user"
    user.mkdir()

    # Simple theme (no CSS)
    (builtin / "blue.json").write_text(json.dumps({
        "id": "blue", "label": "Default", "swatch": "#3b82f6",
        "tokens": {"--color-primary": "rgb(37, 99, 235)"},
    }))

    # Theme with sidecar CSS
    (builtin / "cinema.json").write_text(json.dumps({
        "id": "cinema", "label": "Cinema", "swatch": "#ca8a04", "mode": "dark",
        "tokens": {"--color-primary": "rgb(212, 175, 55)"},
    }))
    (builtin / "cinema.css").write_text('[data-scheme="cinema"] { font-family: serif; }\n')

    # Invalid theme (missing tokens)
    (builtin / "bad.json").write_text(json.dumps({"id": "bad", "label": "Bad"}))

    # Malformed JSON
    (builtin / "broken.json").write_text("{invalid json")

    return builtin, user


@pytest.fixture(autouse=True)
def patch_dirs(tmp_themes, monkeypatch):
    builtin, user = tmp_themes
    monkeypatch.setattr(theme_service, "_BUILTIN_DIR", builtin)
    monkeypatch.setattr(theme_service, "_user_themes_dir", lambda: user)


# --- _load_theme_file ---

def test_load_theme_file_simple(tmp_themes):
    builtin, _ = tmp_themes
    t = theme_service._load_theme_file(builtin / "blue.json")
    assert t is not None
    assert t["id"] == "blue"
    assert t["css"] == ""


def test_load_theme_file_with_sidecar_css(tmp_themes):
    builtin, _ = tmp_themes
    t = theme_service._load_theme_file(builtin / "cinema.json")
    assert t is not None
    assert "font-family: serif" in t["css"]


def test_load_theme_file_invalid_returns_none(tmp_themes):
    builtin, _ = tmp_themes
    assert theme_service._load_theme_file(builtin / "bad.json") is None


def test_load_theme_file_malformed_json_returns_none(tmp_themes):
    builtin, _ = tmp_themes
    assert theme_service._load_theme_file(builtin / "broken.json") is None


def test_load_theme_file_missing_returns_none(tmp_themes):
    builtin, _ = tmp_themes
    assert theme_service._load_theme_file(builtin / "nonexistent.json") is None


# --- _validate_theme ---

def test_validate_theme_valid():
    assert theme_service._validate_theme({"id": "x", "label": "X", "tokens": {}}) is True


def test_validate_theme_missing_field():
    assert theme_service._validate_theme({"id": "x", "label": "X"}) is False


def test_validate_theme_tokens_not_dict():
    assert theme_service._validate_theme({"id": "x", "label": "X", "tokens": "bad"}) is False


def test_validate_theme_not_dict():
    assert theme_service._validate_theme("not a dict") is False


# --- _safe_path ---

def test_safe_path_valid(tmp_path):
    result = theme_service._safe_path(tmp_path, "test.json")
    assert result == (tmp_path / "test.json").resolve()


def test_safe_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="Path traversal"):
        theme_service._safe_path(tmp_path, "../../etc/passwd")


# --- get_all_themes / get_theme ---

def test_get_all_themes():
    themes = theme_service.get_all_themes()
    ids = [t["id"] for t in themes]
    assert "blue" in ids
    assert "cinema" in ids
    assert "bad" not in ids
    assert "broken" not in ids
    # CSS should be excluded from list
    for t in themes:
        assert "css" not in t


def test_get_theme_existing():
    t = theme_service.get_theme("cinema")
    assert t is not None
    assert t["id"] == "cinema"
    assert "font-family: serif" in t["css"]
    assert t["builtin"] is True


def test_get_theme_not_found():
    assert theme_service.get_theme("nonexistent") is None


# --- save_user_theme ---

def test_save_user_theme_json_only(tmp_themes):
    _, user = tmp_themes
    data = {"id": "test", "label": "Test", "tokens": {"--color-primary": "rgb(0,0,0)"}}
    saved = theme_service.save_user_theme(data)
    assert saved["id"] == "test"
    assert saved["builtin"] is False
    assert (user / "test.json").exists()
    assert not (user / "test.css").exists()
    # Verify JSON doesn't contain css or builtin
    on_disk = json.loads((user / "test.json").read_text())
    assert "css" not in on_disk
    assert "builtin" not in on_disk


def test_save_user_theme_with_css(tmp_themes):
    _, user = tmp_themes
    data = {"id": "styled", "label": "Styled", "tokens": {"--color-primary": "rgb(0,0,0)"}}
    css = '[data-scheme="styled"] { color: red; }'
    saved = theme_service.save_user_theme(data, css=css)
    assert saved["css"] == css
    assert (user / "styled.css").exists()
    assert (user / "styled.css").read_text() == css


def test_save_user_theme_removes_old_css(tmp_themes):
    _, user = tmp_themes
    data = {"id": "evolve", "label": "Evolve", "tokens": {"--color-primary": "rgb(0,0,0)"}}
    # First save with CSS
    theme_service.save_user_theme(data, css="body { color: red; }")
    assert (user / "evolve.css").exists()
    # Save again without CSS
    theme_service.save_user_theme(data, css="")
    assert not (user / "evolve.css").exists()


def test_save_user_theme_invalid():
    with pytest.raises(ValueError, match="missing required fields"):
        theme_service.save_user_theme({"id": "x"})


def test_save_user_theme_path_traversal():
    data = {"id": "../../../etc/evil", "label": "Evil", "tokens": {}}
    with pytest.raises(ValueError, match="Invalid theme id"):
        theme_service.save_user_theme(data)


def test_delete_user_theme_path_traversal():
    with pytest.raises(ValueError, match="Invalid theme id"):
        theme_service.delete_user_theme("../../../etc/passwd")


def test_save_user_theme_defaults(tmp_themes):
    _builtin, _user = tmp_themes
    data = {"id": "minimal", "label": "Min", "tokens": {}}
    saved = theme_service.save_user_theme(data)
    assert saved["version"] == 1
    assert saved["swatch"] == "#888888"


# --- delete_user_theme ---

def test_delete_user_theme(tmp_themes):
    _, user = tmp_themes
    # Create a user theme with CSS
    data = {"id": "deleteme", "label": "Delete Me", "tokens": {}}
    theme_service.save_user_theme(data, css="body {}")
    assert (user / "deleteme.json").exists()
    assert (user / "deleteme.css").exists()
    # Delete
    assert theme_service.delete_user_theme("deleteme") is True
    assert not (user / "deleteme.json").exists()
    assert not (user / "deleteme.css").exists()


def test_delete_builtin_returns_false():
    assert theme_service.delete_user_theme("blue") is False


def test_delete_nonexistent_returns_false():
    assert theme_service.delete_user_theme("nosuchtheme") is False


# --- User themes override built-ins ---

def test_user_theme_overrides_builtin(tmp_themes):
    _builtin, _user = tmp_themes
    # Save a user theme with same id as builtin
    data = {"id": "blue", "label": "My Blue", "tokens": {"--color-primary": "rgb(0,0,255)"}}
    theme_service.save_user_theme(data)
    t = theme_service.get_theme("blue")
    assert t["label"] == "My Blue"
    assert t["builtin"] is False
