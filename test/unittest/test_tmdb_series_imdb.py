"""TMDB movie and TV ids overlap: a series result must use the TV external ids."""
import json
from types import SimpleNamespace

import pytest


def test_series_result_never_takes_the_movie_with_the_same_id(monkeypatch):
    import arm.config.config as cfg
    import arm.ui  # noqa: F401
    from arm.ui import metadata

    monkeypatch.setitem(cfg.arm_config, "TMDB_API_KEY", "fixture")
    requested = []

    def get(url, **kwargs):  # kwargs: e.g. a request timeout
        requested.append(url.split("?")[0])
        if "/tv/" in url:
            return SimpleNamespace(text=json.dumps({"imdb_id": "tt0903747"}))
        return SimpleNamespace(text=json.dumps({"external_ids": {"imdb_id": "tt0000001"}}))

    monkeypatch.setattr(metadata.requests, "get", get)
    assert metadata.tmdb_get_imdb(1396, "series") == "tt0903747"
    assert requested == ["https://api.themoviedb.org/3/tv/1396/external_ids"]
    assert metadata.tmdb_get_imdb(1396) == "tt0000001"


@pytest.mark.parametrize("timeout", [7, 30])
def test_series_external_id_lookup_uses_the_shared_timeout(monkeypatch, timeout):
    from arm.ui import metadata

    monkeypatch.setattr(metadata, "REQUEST_TIMEOUT", timeout)
    calls = []

    def get(url, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text=json.dumps({"imdb_id": "tt0903747"}))

    monkeypatch.setattr(metadata.requests, "get", get)
    assert metadata.tmdb_get_imdb(1396, "series") == "tt0903747"
    assert calls == [{"timeout": timeout}]


def test_series_lookup_does_not_fall_back_to_a_movie_after_a_timeout(monkeypatch):
    from arm.ui import metadata

    calls = []

    def get(url, **kwargs):
        calls.append(url)
        raise metadata.requests.Timeout("fixture timeout")

    monkeypatch.setattr(metadata.requests, "get", get)
    with pytest.raises(metadata.requests.Timeout, match="fixture timeout"):
        metadata.tmdb_get_imdb(1396, "series")
    assert len(calls) == 1
    assert "/tv/1396/external_ids" in calls[0]
