"""OMDb/TMDB requests cannot hang identification or the UI indefinitely."""

import json
from types import SimpleNamespace

import pytest


@pytest.fixture
def metadata(monkeypatch):
    import arm.config.config as cfg
    import arm.ui  # noqa: F401
    from arm.ui import metadata

    monkeypatch.setitem(cfg.arm_config, "TMDB_API_KEY", "k")
    monkeypatch.setitem(cfg.arm_config, "OMDB_API_KEY", "k")
    calls = []

    def get(url, timeout=None):
        calls.append(timeout)
        if "/search/" in url:
            body = {"total_results": 1, "results": [{"id": 1, "title": "Hercules", "release_date": "1997-06-13",
                                                     "poster_path": None, "backdrop_path": None, "overview": ""}]}
        else:
            body = {"external_ids": {"imdb_id": "tt0119282"}, "movie_results": [], "tv_results": []}
        return SimpleNamespace(text=json.dumps(body))

    def urlopen(url, timeout=None):
        calls.append(timeout)
        search = [{"Poster": "p", "imdbID": "tt0119282"}]
        return SimpleNamespace(read=lambda: json.dumps({"Response": "True", "Search": search}).encode())

    monkeypatch.setattr(metadata.requests, "get", get)
    monkeypatch.setattr(metadata.urllib.request, "urlopen", urlopen)
    return SimpleNamespace(module=metadata, calls=calls)


def test_tmdb_and_omdb_requests_have_a_timeout(metadata):
    metadata.module.tmdb_search("Hercules", "1997")
    metadata.module.tmdb_get_imdb(1)
    metadata.module.call_omdb_api("Hercules", "1997")
    metadata.module.get_omdb_poster("Hercules", "1997")
    assert len(metadata.calls) >= 5
    assert set(metadata.calls) == {metadata.module.REQUEST_TIMEOUT}
