"""TMDB movie and TV ids overlap: a series result must use the TV external ids."""
import json
from types import SimpleNamespace


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
