"""Theme loading and management service."""

import json
import re
from pathlib import Path
from typing import Any

from backend.common.path_safety import safe_join
from backend.config import settings

# Built-in themes ship with the package
_BUILTIN_DIR = Path(__file__).parent.parent / "themes" / "builtin"


def _load_theme_file(path: Path) -> dict[str, Any] | None:
    """Load a theme JSON file and its optional sidecar CSS."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not _validate_theme(data):
            return None
        # Read sidecar CSS if it exists (new split format)
        css_path = path.with_suffix(".css")
        if css_path.is_file():
            data["css"] = css_path.read_text(encoding="utf-8")
        else:
            data.setdefault("css", "")
        return data
    except (json.JSONDecodeError, OSError):
        return None


_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _safe_theme_id(theme_id: str) -> str:
    """Validate a theme ID is safe for use as a filename. Raises ValueError if not."""
    if not _SAFE_ID.match(theme_id) or ".." in theme_id:
        raise ValueError(f"Invalid theme id: {theme_id!r}")
    return theme_id


def _safe_path(directory: Path, filename: str) -> Path:
    """Build a path inside *directory* and verify it resolves within it.

    Delegates to safe_join so the realpath+containment pattern is consistent
    across the codebase and recognised by static analysis tools.
    """
    return Path(safe_join(directory, filename))


def _validate_theme(data: Any) -> bool:
    """Check required fields are present."""
    if not isinstance(data, dict):
        return False
    required = {"id", "label", "tokens"}
    return required.issubset(data.keys()) and isinstance(data["tokens"], dict)


def _user_themes_dir() -> Path:
    """Return the user themes directory, creating it if needed."""
    p = Path(settings.themes_path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _load_all() -> dict[str, dict[str, Any]]:
    """Load all themes, user themes override built-ins with same id."""
    themes: dict[str, dict[str, Any]] = {}

    # Built-in themes
    if _BUILTIN_DIR.is_dir():
        for f in sorted(_BUILTIN_DIR.glob("*.json")):
            t = _load_theme_file(f)
            if t:
                t["builtin"] = True
                themes[t["id"]] = t

    # User themes (override built-ins)
    user_dir = _user_themes_dir()
    if user_dir.is_dir():
        for f in sorted(user_dir.glob("*.json")):
            t = _load_theme_file(f)
            if t:
                t["builtin"] = False
                themes[t["id"]] = t

    return themes


def get_all_themes() -> list[dict[str, Any]]:
    """Return metadata for all themes (no CSS)."""
    themes = _load_all()
    result = []
    for t in themes.values():
        meta = {k: v for k, v in t.items() if k != "css"}
        result.append(meta)
    return result


def get_theme(theme_id: str) -> dict[str, Any] | None:
    """Return full theme data including CSS."""
    themes = _load_all()
    return themes.get(theme_id)


def save_user_theme(data: dict[str, Any], css: str = "") -> dict[str, Any]:
    """Save a user theme. JSON and CSS are written as separate files."""
    if not _validate_theme(data):
        raise ValueError("Invalid theme: missing required fields (id, label, tokens)")

    theme_id = _safe_theme_id(data["id"])
    data.setdefault("version", 1)
    data.setdefault("swatch", "#888888")

    user_dir = _user_themes_dir()
    json_path = Path(safe_join(user_dir, f"{theme_id}.json"))
    css_path = Path(safe_join(user_dir, f"{theme_id}.css"))

    # Save JSON without css or builtin fields
    save_data = {k: v for k, v in data.items() if k not in ("builtin", "css")}
    json_path.write_text(json.dumps(save_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Save or remove CSS sidecar
    if css.strip():
        css_path.write_text(css, encoding="utf-8")
        data["css"] = css
    else:
        css_path.unlink(missing_ok=True)
        data["css"] = ""

    data["builtin"] = False
    return data


def delete_user_theme(theme_id: str) -> bool:
    """Delete a user theme. Returns False if it's a built-in or doesn't exist."""
    theme_id = _safe_theme_id(theme_id)
    builtin_path = Path(safe_join(_BUILTIN_DIR, f"{theme_id}.json"))
    if builtin_path.exists():
        return False

    user_dir = _user_themes_dir()
    json_path = Path(safe_join(user_dir, f"{theme_id}.json"))
    css_path = Path(safe_join(user_dir, f"{theme_id}.css"))
    if not json_path.exists():
        return False

    json_path.unlink()
    # Also remove sidecar CSS
    css_path.unlink(missing_ok=True)
    return True
