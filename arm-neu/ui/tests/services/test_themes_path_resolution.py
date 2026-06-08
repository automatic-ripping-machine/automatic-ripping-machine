"""Test _user_themes_dir() in isolation.

Lives in its own file so the test_themes.py autouse `patch_dirs` fixture
(which replaces _user_themes_dir with a lambda) does not apply.
"""

from __future__ import annotations

from backend.services import themes as theme_service


def test_user_themes_dir_uses_configured_path_and_creates_dir(tmp_path, monkeypatch):
    """_user_themes_dir reads settings.themes_path and mkdir-s the target."""
    target = tmp_path / "ui-themes-volume"
    monkeypatch.setattr(theme_service.settings, "themes_path", str(target))
    assert not target.exists()
    result = theme_service._user_themes_dir()
    assert result == target
    assert target.is_dir()
