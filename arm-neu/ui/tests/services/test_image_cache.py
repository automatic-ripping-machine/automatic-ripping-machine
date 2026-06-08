"""Tests for backend.services.image_cache — disk-backed image cache."""

from __future__ import annotations

import json
import time

import pytest

from backend.services import image_cache


@pytest.fixture(autouse=True)
def cache_dir(tmp_path):
    """Provide a temp cache dir and reset the service."""
    d = tmp_path / "images"
    d.mkdir()
    image_cache._index.clear()
    image_cache._cache_dir = str(d)
    yield d


def test_store_and_retrieve():
    """Stored image can be retrieved."""
    url = "https://m.media-amazon.com/images/test.jpg"
    data = b"\xff\xd8\xff\xe0fake-jpeg"
    image_cache.store(url, data, "image/jpeg")
    result = image_cache.retrieve(url)
    assert result is not None
    content, content_type = result
    assert content == data
    assert content_type == "image/jpeg"


def test_retrieve_miss():
    """Missing URL returns None."""
    assert image_cache.retrieve("https://example.com/nope.jpg") is None


def test_eviction_lru():
    """When cache exceeds max entries, LRU entry is evicted."""
    old_max = image_cache._MAX_ENTRIES
    image_cache._MAX_ENTRIES = 3
    try:
        for i in range(4):
            image_cache.store(f"https://example.com/{i}.jpg", b"img", "image/jpeg")
        assert image_cache.retrieve("https://example.com/0.jpg") is None
        assert image_cache.retrieve("https://example.com/3.jpg") is not None
    finally:
        image_cache._MAX_ENTRIES = old_max


def test_ttl_expiry(cache_dir):
    """Expired entries are not returned."""
    url = "https://example.com/old.jpg"
    image_cache.store(url, b"img", "image/jpeg")
    # Backdate the entry
    filename = image_cache._url_to_filename(url)
    meta_path = cache_dir / f"{filename}.json"
    meta = json.loads(meta_path.read_text())
    meta["cached_at"] = time.time() - image_cache._TTL_SECONDS - 1
    meta["accessed_at"] = meta["cached_at"]
    meta_path.write_text(json.dumps(meta))
    image_cache._index[url]["cached_at"] = meta["cached_at"]
    assert image_cache.retrieve(url) is None


def test_max_size_rejected():
    """Images exceeding max size are not stored."""
    url = "https://example.com/huge.jpg"
    data = b"x" * (image_cache._MAX_IMAGE_BYTES + 1)
    assert image_cache.store(url, data, "image/jpeg") is False
    assert image_cache.retrieve(url) is None


def test_clear():
    """clear() removes all entries and files."""
    image_cache.store("https://example.com/a.jpg", b"img", "image/jpeg")
    image_cache.store("https://example.com/b.jpg", b"img", "image/jpeg")
    result = image_cache.clear()
    assert result["cleared"] == 2
    assert result["freed_bytes"] > 0
    assert len(list((image_cache._ensure_dir()).iterdir())) == 0


def test_stats():
    """stats() returns correct counts."""
    image_cache.store("https://example.com/a.jpg", b"imgdata", "image/jpeg")
    s = image_cache.stats()
    assert s["count"] == 1
    assert s["size_bytes"] > 0
    assert "path" in s


def test_startup_scan(cache_dir):
    """startup_scan rebuilds index from disk."""
    url = "https://example.com/persist.jpg"
    image_cache.store(url, b"imgdata", "image/jpeg")
    image_cache._index.clear()
    assert image_cache.retrieve(url) is None
    image_cache.startup_scan()
    assert image_cache.retrieve(url) is not None


def test_orphaned_metadata_cleaned(cache_dir):
    """startup_scan removes metadata without matching image file."""
    filename = image_cache._url_to_filename("https://example.com/ghost.jpg")
    meta = {"url": "https://example.com/ghost.jpg", "content_type": "image/jpeg",
            "cached_at": time.time(), "accessed_at": time.time(), "size": 100}
    (cache_dir / f"{filename}.json").write_text(json.dumps(meta))
    image_cache.startup_scan()
    assert not (cache_dir / f"{filename}.json").exists()
