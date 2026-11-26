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


def test_tmdb_find_keeps_the_imdb_id_inside_the_find_path(metadata, monkeypatch):
    requested = []

    def get(url, timeout=None):
        requested.append(url.split("?")[0])
        movie = {"poster_path": "/p.jpg", "overview": "", "backdrop_path": "/b.jpg", "release_date": "1997-06-13",
                 "title": "Hercules"}
        return SimpleNamespace(text=json.dumps({"movie_results": [movie], "tv_results": []}))

    monkeypatch.setattr(metadata.module.requests, "get", get)
    metadata.module.tmdb_find("../movie/1")
    assert requested == ["https://api.themoviedb.org/3/find/..%2Fmovie%2F1"]
