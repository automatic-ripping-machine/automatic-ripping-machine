"""Disk-backed image cache with LRU eviction and TTL expiry."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

from backend.config import settings

log = logging.getLogger(__name__)

_cache_dir: str = settings.image_cache_path
_index: dict[str, dict[str, Any]] = {}

_MAX_ENTRIES = 1000
_MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2 MB
_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _url_to_filename(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def _ensure_dir() -> Path:
    p = Path(_cache_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_path(base: Path, filename: str, ext: str) -> Path:
    """Build a path within base and verify containment (prevents path traversal)."""
    target = (base / f"{filename}{ext}").resolve()
    if not target.is_relative_to(base.resolve()):
        raise ValueError(f"Path traversal blocked: {target}")
    return target


def store(url: str, data: bytes, content_type: str) -> bool:
    """Store an image in the cache. Returns False if too large."""
    if len(data) > _MAX_IMAGE_BYTES:
        return False

    # Evict LRU if full
    while len(_index) >= _MAX_ENTRIES:
        oldest_url = min(_index, key=lambda u: _index[u]["accessed_at"])
        _remove(oldest_url)

    d = _ensure_dir()
    filename = _url_to_filename(url)
    now = time.time()

    img_path = _safe_path(d, filename, ".img")
    meta_path = _safe_path(d, filename, ".json")
    img_path.write_bytes(data)
    meta = {
        "url": url,
        "content_type": content_type,
        "cached_at": now,
        "accessed_at": now,
        "size": len(data),
    }
    meta_path.write_text(json.dumps(meta))

    _index[url] = {
        "filename": filename,
        "content_type": content_type,
        "cached_at": now,
        "accessed_at": now,
        "size": len(data),
    }
    return True


def retrieve(url: str) -> tuple[bytes, str] | None:
    """Retrieve a cached image. Returns (bytes, content_type) or None."""
    entry = _index.get(url)
    if entry is None:
        return None

    # Check TTL
    if time.time() - entry["cached_at"] > _TTL_SECONDS:
        _remove(url)
        return None

    d = Path(_cache_dir)
    img_path = _safe_path(d, entry["filename"], ".img")
    if not img_path.exists():
        _remove(url)
        return None

    # Update access time
    entry["accessed_at"] = time.time()
    return img_path.read_bytes(), entry["content_type"]


def _remove(url: str) -> int:
    """Remove an entry from cache. Returns freed bytes."""
    entry = _index.pop(url, None)
    if entry is None:
        return 0
    d = Path(_cache_dir)
    freed = 0
    for ext in (".img", ".json"):
        p = _safe_path(d, entry["filename"], ext)
        if p.exists():
            freed += p.stat().st_size
            p.unlink()
    return freed


def clear() -> dict[str, Any]:
    """Remove all cached images. Returns stats about what was cleared."""
    count = len(_index)
    freed = 0
    for url in list(_index):
        freed += _remove(url)
    return {"success": True, "cleared": count, "freed_bytes": freed}


def stats() -> dict[str, Any]:
    """Return cache statistics."""
    total_bytes = sum(e["size"] for e in _index.values())
    oldest = min((e["cached_at"] for e in _index.values()), default=None)
    return {
        "count": len(_index),
        "size_bytes": total_bytes,
        "size_mb": round(total_bytes / 1048576, 1),
        "oldest": oldest,
        "path": _cache_dir,
    }


def startup_scan() -> None:
    """Rebuild in-memory index from disk on startup."""
    _index.clear()
    d = Path(_cache_dir)
    if not d.exists():
        return
    now = time.time()
    for meta_path in d.glob("*.json"):
        try:
            meta = json.loads(meta_path.read_text())
            img_path = meta_path.with_suffix(".img")
            if not img_path.exists():
                meta_path.unlink()
                log.debug("Removed orphaned metadata: %s", meta_path.name)
                continue
            if now - meta["cached_at"] > _TTL_SECONDS:
                meta_path.unlink()
                img_path.unlink()
                log.debug("Removed expired cache entry: %s", meta_path.name)
                continue
            _index[meta["url"]] = {
                "filename": meta_path.stem,
                "content_type": meta["content_type"],
                "cached_at": meta["cached_at"],
                "accessed_at": meta.get("accessed_at", meta["cached_at"]),
                "size": meta["size"],
            }
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            log.warning("Skipping corrupt cache entry %s: %s", meta_path.name, exc)
    log.info("Image cache loaded: %d entries from %s", len(_index), _cache_dir)
