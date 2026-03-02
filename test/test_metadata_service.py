"""Tests for arm/services/metadata.py — async metadata service.

Covers: _get_keys, has_api_key, _extract_year, _escape_lucene,
_normalize_omdb, _build_artist_credit, _extract_label, _extract_catalog_number,
_extract_format, _omdb_search, _omdb_details, _tmdb_search, _tmdb_find,
_tmdb_get_imdb, search, get_details, search_music, get_music_details,
lookup_crc, test_configured_key.
"""

import asyncio
import unittest.mock

import httpx
import pytest


# ---------------------------------------------------------------------------
# Helper: run async functions from sync test methods
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Shared mock helpers
# ---------------------------------------------------------------------------

def _mock_httpx_responses(responses):
    """Create a mock httpx client context manager that returns sequential responses."""
    call_count = [0]

    async def mock_get(url, **kwargs):
        idx = min(call_count[0], len(responses) - 1)
        call_count[0] += 1
        resp = unittest.mock.MagicMock(spec=httpx.Response)
        data = responses[idx]
        resp.status_code = data.get("_status", 200)
        resp.json.return_value = {k: v for k, v in data.items() if k != "_status"}
        resp.text = str(resp.json.return_value)
        resp.raise_for_status = unittest.mock.MagicMock()
        if resp.status_code >= 400:
            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "error", request=unittest.mock.MagicMock(), response=resp
            )
        return resp

    ctx = unittest.mock.AsyncMock()
    ctx.get = mock_get
    return ctx


def _patch_http_client(responses):
    """Patch _http_client to return a mock with sequential responses."""
    ctx = _mock_httpx_responses(responses)
    mock_client = unittest.mock.patch('arm.services.metadata._http_client')
    return mock_client, ctx


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestExtractYear:
    def test_date_string(self):
        from arm.services.metadata import _extract_year
        assert _extract_year("1999-03-31") == "1999"

    def test_year_only(self):
        from arm.services.metadata import _extract_year
        assert _extract_year("2001") == "2001"

    def test_range_returns_first(self):
        from arm.services.metadata import _extract_year
        assert _extract_year("2011-2019") == "2011"

    def test_dash_range(self):
        from arm.services.metadata import _extract_year
        assert _extract_year("2011–2019") == "2011"

    def test_no_year_returns_raw(self):
        from arm.services.metadata import _extract_year
        assert _extract_year("unknown") == "unknown"

    def test_empty_string(self):
        from arm.services.metadata import _extract_year
        assert _extract_year("") == ""


class TestEscapeLucene:
    def test_no_special_chars(self):
        from arm.services.metadata import _escape_lucene
        assert _escape_lucene("hello world") == "hello world"

    def test_special_chars_escaped(self):
        from arm.services.metadata import _escape_lucene
        result = _escape_lucene("AC/DC (Live!)")
        assert "\\/" in result
        assert "\\(" in result
        assert "\\)" in result
        assert "\\!" in result

    def test_empty_string(self):
        from arm.services.metadata import _escape_lucene
        assert _escape_lucene("") == ""

    def test_plus_and_minus(self):
        from arm.services.metadata import _escape_lucene
        result = _escape_lucene("C++ and -flag")
        assert "\\+" in result
        assert "\\-" in result


class TestNormalizeOmdb:
    def test_movie_type(self):
        from arm.services.metadata import _normalize_omdb
        result = _normalize_omdb({"Title": "Matrix", "Year": "1999", "Type": "movie",
                                   "imdbID": "tt0133093", "Poster": "http://img.com/p.jpg"})
        assert result["title"] == "Matrix"
        assert result["year"] == "1999"
        assert result["media_type"] == "movie"
        assert result["imdb_id"] == "tt0133093"
        assert result["poster_url"] == "http://img.com/p.jpg"

    def test_series_type(self):
        from arm.services.metadata import _normalize_omdb
        result = _normalize_omdb({"Title": "Friends", "Year": "1994–2004", "Type": "series",
                                   "imdbID": "tt0108778", "Poster": "N/A"})
        assert result["media_type"] == "series"
        assert result["year"] == "1994"
        assert result["poster_url"] is None

    def test_unknown_type_defaults_to_movie(self):
        from arm.services.metadata import _normalize_omdb
        result = _normalize_omdb({"Title": "X", "Year": "2020", "Type": "game",
                                   "imdbID": "tt0000001"})
        assert result["media_type"] == "movie"

    def test_missing_type_defaults_to_movie(self):
        from arm.services.metadata import _normalize_omdb
        result = _normalize_omdb({"Title": "X", "Year": "2020", "imdbID": "tt0000001"})
        assert result["media_type"] == "movie"

    def test_poster_na_normalized_to_none(self):
        from arm.services.metadata import _normalize_omdb
        result = _normalize_omdb({"Title": "X", "Year": "2020", "Poster": "N/A"})
        assert result["poster_url"] is None

    def test_missing_poster(self):
        from arm.services.metadata import _normalize_omdb
        result = _normalize_omdb({"Title": "X", "Year": "2020"})
        assert result["poster_url"] is None


class TestBuildArtistCredit:
    def test_single_artist(self):
        from arm.services.metadata import _build_artist_credit
        result = _build_artist_credit([{"name": "Metallica"}])
        assert result == "Metallica"

    def test_multiple_artists_with_joinphrase(self):
        from arm.services.metadata import _build_artist_credit
        result = _build_artist_credit([
            {"name": "Simon", "joinphrase": " & "},
            {"name": "Garfunkel"},
        ])
        assert result == "Simon & Garfunkel"

    def test_empty_list(self):
        from arm.services.metadata import _build_artist_credit
        assert _build_artist_credit([]) == ""


class TestExtractLabel:
    def test_valid_label(self):
        from arm.services.metadata import _extract_label
        result = _extract_label([{"label": {"name": "Virgin Records"}}])
        assert result == "Virgin Records"

    def test_empty_list(self):
        from arm.services.metadata import _extract_label
        assert _extract_label([]) is None

    def test_missing_label_key(self):
        from arm.services.metadata import _extract_label
        assert _extract_label([{"catalog-number": "123"}]) is None


class TestExtractCatalogNumber:
    def test_valid_catalog(self):
        from arm.services.metadata import _extract_catalog_number
        assert _extract_catalog_number([{"catalog-number": "CDP 7464"}]) == "CDP 7464"

    def test_empty_list(self):
        from arm.services.metadata import _extract_catalog_number
        assert _extract_catalog_number([]) is None


class TestExtractFormat:
    def test_valid_format(self):
        from arm.services.metadata import _extract_format
        assert _extract_format([{"format": "CD"}]) == "CD"

    def test_empty_list(self):
        from arm.services.metadata import _extract_format
        assert _extract_format([]) is None

    def test_missing_format(self):
        from arm.services.metadata import _extract_format
        assert _extract_format([{"tracks": []}]) is None


# ---------------------------------------------------------------------------
# _get_keys / has_api_key
# ---------------------------------------------------------------------------


class TestGetKeys:
    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'tmdb', 'OMDB_API_KEY': 'omdb123', 'TMDB_API_KEY': 'tmdb456',
    })
    def test_all_keys_present(self):
        from arm.services.metadata import _get_keys
        keys = _get_keys()
        assert keys["provider"] == "tmdb"
        assert keys["omdb_key"] == "omdb123"
        assert keys["tmdb_key"] == "tmdb456"

    @unittest.mock.patch.dict('arm.config.config.arm_config', {}, clear=True)
    def test_defaults_to_omdb(self):
        from arm.services.metadata import _get_keys
        keys = _get_keys()
        assert keys["provider"] == "omdb"
        assert not keys["omdb_key"]  # None or empty
        assert not keys["tmdb_key"]  # None or empty


class TestHasApiKey:
    @unittest.mock.patch.dict('arm.config.config.arm_config', {'ARM_API_KEY': 'secret'})
    def test_key_configured(self):
        from arm.services.metadata import has_api_key
        assert has_api_key() is True

    @unittest.mock.patch.dict('arm.config.config.arm_config', {'ARM_API_KEY': ''})
    def test_empty_key(self):
        from arm.services.metadata import has_api_key
        assert has_api_key() is False

    @unittest.mock.patch.dict('arm.config.config.arm_config', {})
    def test_missing_key(self):
        from arm.services.metadata import has_api_key
        assert has_api_key() is False


# ---------------------------------------------------------------------------
# search() — provider routing
# ---------------------------------------------------------------------------


class TestSearch:
    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': 'key123',
    })
    def test_omdb_provider(self):
        from arm.services.metadata import search
        with unittest.mock.patch('arm.services.metadata._omdb_search',
                                 return_value=[{"title": "Test"}]) as mock_omdb:
            result = _run(search("Matrix", "1999"))
            mock_omdb.assert_called_once_with("Matrix", "1999", "key123")
        assert result == [{"title": "Test"}]

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'tmdb', 'TMDB_API_KEY': 'tmdb_key',
    })
    def test_tmdb_provider(self):
        from arm.services.metadata import search
        with unittest.mock.patch('arm.services.metadata._tmdb_search',
                                 return_value=[{"title": "Test"}]) as mock_tmdb:
            result = _run(search("Matrix"))
            mock_tmdb.assert_called_once_with("Matrix", None, "tmdb_key")
        assert result == [{"title": "Test"}]

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'tmdb', 'TMDB_API_KEY': '', 'OMDB_API_KEY': 'omdb_fallback',
    })
    def test_tmdb_falls_back_to_omdb(self):
        from arm.services.metadata import search
        with unittest.mock.patch('arm.services.metadata._omdb_search',
                                 return_value=[]) as mock_omdb:
            _run(search("Matrix"))
            mock_omdb.assert_called_once_with("Matrix", None, "omdb_fallback")

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'tmdb', 'TMDB_API_KEY': '', 'OMDB_API_KEY': '',
    })
    def test_tmdb_no_fallback_raises(self):
        from arm.services.metadata import search, MetadataConfigError
        with pytest.raises(MetadataConfigError):
            _run(search("Matrix"))

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': '',
    })
    def test_no_keys_raises(self):
        from arm.services.metadata import search, MetadataConfigError
        with pytest.raises(MetadataConfigError):
            _run(search("Matrix"))


# ---------------------------------------------------------------------------
# get_details() — provider routing
# ---------------------------------------------------------------------------


class TestGetDetails:
    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': 'key123',
    })
    def test_omdb_provider(self):
        from arm.services.metadata import get_details
        with unittest.mock.patch('arm.services.metadata._omdb_details',
                                 return_value={"title": "Matrix"}) as mock_fn:
            result = _run(get_details("tt0133093"))
            mock_fn.assert_called_once_with("tt0133093", "key123")
        assert result["title"] == "Matrix"

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'tmdb', 'TMDB_API_KEY': 'tmdb_key',
    })
    def test_tmdb_provider(self):
        from arm.services.metadata import get_details
        with unittest.mock.patch('arm.services.metadata._tmdb_find',
                                 return_value={"title": "Matrix"}) as mock_fn:
            result = _run(get_details("tt0133093"))
            mock_fn.assert_called_once_with("tt0133093", "tmdb_key")
        assert result["title"] == "Matrix"

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': 'key123',
    })
    def test_returns_none_when_not_found(self):
        from arm.services.metadata import get_details
        with unittest.mock.patch('arm.services.metadata._omdb_details', return_value=None):
            result = _run(get_details("tt9999999"))
        assert result is None

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': '',
    })
    def test_no_keys_raises(self):
        from arm.services.metadata import get_details, MetadataConfigError
        with pytest.raises(MetadataConfigError):
            _run(get_details("tt0133093"))


# ---------------------------------------------------------------------------
# _omdb_search
# ---------------------------------------------------------------------------


class TestOmdbSearch:
    def test_search_success(self):
        from arm.services.metadata import _omdb_search
        search_resp = {
            "Response": "True",
            "Search": [{"Title": "The Matrix", "Year": "1999", "imdbID": "tt0133093",
                         "Type": "movie", "Poster": "http://img.com/matrix.jpg"}],
        }
        ctx = _mock_httpx_responses([search_resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_omdb_search("The Matrix", "1999", "test_key"))
        assert len(result) == 1
        assert result[0]["title"] == "The Matrix"

    def test_search_fails_fallback_to_exact(self):
        from arm.services.metadata import _omdb_search
        search_fail = {"Response": "False", "Error": "Too many results."}
        exact_match = {"Response": "True", "Title": "9", "Year": "2009",
                       "Type": "movie", "imdbID": "tt0472033", "Poster": "N/A"}
        ctx = _mock_httpx_responses([search_fail, exact_match])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_omdb_search("9", "2009", "test_key"))
        assert len(result) == 1
        assert result[0]["title"] == "9"

    def test_both_fail_returns_empty(self):
        from arm.services.metadata import _omdb_search
        fail_resp = {"Response": "False", "Error": "Movie not found!"}
        ctx = _mock_httpx_responses([fail_resp, fail_resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_omdb_search("xyznonexistent", None, "test_key"))
        assert result == []

    def test_auth_error_raises(self):
        from arm.services.metadata import _omdb_search, MetadataConfigError
        ctx = _mock_httpx_responses([{"_status": 401}])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            with pytest.raises(MetadataConfigError):
                _run(_omdb_search("Matrix", None, "bad_key"))


# ---------------------------------------------------------------------------
# _omdb_details
# ---------------------------------------------------------------------------


class TestOmdbDetails:
    def test_valid_result(self):
        from arm.services.metadata import _omdb_details
        resp = {"Response": "True", "Title": "Matrix", "Year": "1999", "Type": "movie",
                "imdbID": "tt0133093", "Poster": "http://img.com/p.jpg",
                "Plot": "A computer hacker learns..."}
        ctx = _mock_httpx_responses([resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_omdb_details("tt0133093", "test_key"))
        assert result["title"] == "Matrix"
        assert result["plot"] == "A computer hacker learns..."
        assert result["background_url"] is None

    def test_plot_na_normalized(self):
        from arm.services.metadata import _omdb_details
        resp = {"Response": "True", "Title": "X", "Year": "2020", "Type": "movie",
                "imdbID": "tt0000001", "Plot": "N/A"}
        ctx = _mock_httpx_responses([resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_omdb_details("tt0000001", "test_key"))
        assert result["plot"] is None

    def test_not_found_returns_none(self):
        from arm.services.metadata import _omdb_details
        resp = {"Response": "False", "Error": "Incorrect IMDb ID."}
        ctx = _mock_httpx_responses([resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_omdb_details("tt9999999", "test_key"))
        assert result is None

    def test_auth_error_raises(self):
        from arm.services.metadata import _omdb_details, MetadataConfigError
        ctx = _mock_httpx_responses([{"_status": 403}])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            with pytest.raises(MetadataConfigError):
                _run(_omdb_details("tt0133093", "bad_key"))


# ---------------------------------------------------------------------------
# _tmdb_search
# ---------------------------------------------------------------------------


class TestTmdbSearch:
    def test_movie_results(self):
        from arm.services.metadata import _tmdb_search
        movie_resp = {
            "total_results": 1,
            "results": [{"id": 603, "title": "The Matrix", "release_date": "1999-03-31",
                         "poster_path": "/poster.jpg"}],
        }
        ctx = _mock_httpx_responses([movie_resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client, \
             unittest.mock.patch('arm.services.metadata._tmdb_get_imdb', return_value="tt0133093"):
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_tmdb_search("The Matrix", "1999", "tmdb_key"))
        assert len(result) == 1
        assert result[0]["title"] == "The Matrix"
        assert result[0]["imdb_id"] == "tt0133093"

    def test_no_movies_falls_back_to_tv(self):
        from arm.services.metadata import _tmdb_search
        empty_movies = {"total_results": 0, "results": []}
        tv_resp = {
            "total_results": 1,
            "results": [{"id": 1396, "name": "Breaking Bad", "first_air_date": "2008-01-20",
                         "poster_path": "/bb.jpg"}],
        }
        ctx = _mock_httpx_responses([empty_movies, tv_resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client, \
             unittest.mock.patch('arm.services.metadata._tmdb_get_imdb', return_value="tt0903747"):
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_tmdb_search("Breaking Bad", None, "tmdb_key"))
        assert len(result) == 1
        assert result[0]["title"] == "Breaking Bad"
        assert result[0]["media_type"] == "series"

    def test_auth_error_raises(self):
        from arm.services.metadata import _tmdb_search, MetadataConfigError
        ctx = _mock_httpx_responses([{"_status": 401}])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            with pytest.raises(MetadataConfigError):
                _run(_tmdb_search("Matrix", None, "bad_key"))

    def test_no_results_returns_empty(self):
        from arm.services.metadata import _tmdb_search
        empty = {"total_results": 0, "results": []}
        ctx = _mock_httpx_responses([empty, empty])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_tmdb_search("xyznonexistent", None, "tmdb_key"))
        assert result == []


# ---------------------------------------------------------------------------
# _tmdb_find
# ---------------------------------------------------------------------------


class TestTmdbFind:
    def test_movie_result(self):
        from arm.services.metadata import _tmdb_find
        resp = {
            "movie_results": [{"title": "The Matrix", "release_date": "1999-03-31",
                               "poster_path": "/matrix.jpg", "backdrop_path": "/matrix_bg.jpg",
                               "overview": "A hacker discovers reality."}],
            "tv_results": [],
        }
        ctx = _mock_httpx_responses([resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_tmdb_find("tt0133093", "tmdb_key"))
        assert result["title"] == "The Matrix"
        assert result["media_type"] == "movie"
        assert result["poster_url"] is not None
        assert result["background_url"] is not None
        assert result["plot"] == "A hacker discovers reality."

    def test_tv_result(self):
        from arm.services.metadata import _tmdb_find
        resp = {
            "movie_results": [],
            "tv_results": [{"name": "Breaking Bad", "first_air_date": "2008-01-20",
                            "poster_path": "/bb.jpg", "backdrop_path": None, "overview": ""}],
        }
        ctx = _mock_httpx_responses([resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_tmdb_find("tt0903747", "tmdb_key"))
        assert result["title"] == "Breaking Bad"
        assert result["media_type"] == "series"
        assert result["background_url"] is None
        assert result["plot"] is None  # empty string → None

    def test_not_found_returns_none(self):
        from arm.services.metadata import _tmdb_find
        resp = {"movie_results": [], "tv_results": []}
        ctx = _mock_httpx_responses([resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_tmdb_find("tt9999999", "tmdb_key"))
        assert result is None

    def test_auth_error_raises(self):
        from arm.services.metadata import _tmdb_find, MetadataConfigError
        ctx = _mock_httpx_responses([{"_status": 401}])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            with pytest.raises(MetadataConfigError):
                _run(_tmdb_find("tt0133093", "bad_key"))


# ---------------------------------------------------------------------------
# _tmdb_get_imdb
# ---------------------------------------------------------------------------


class TestTmdbGetImdb:
    def test_movie_direct(self):
        from arm.services.metadata import _tmdb_get_imdb
        movie_resp = {"external_ids": {"imdb_id": "tt0133093"}}
        ctx = _mock_httpx_responses([movie_resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_tmdb_get_imdb(603, "movie", "key"))
        assert result == "tt0133093"

    def test_series_direct(self):
        from arm.services.metadata import _tmdb_get_imdb
        tv_resp = {"imdb_id": "tt0903747"}
        ctx = _mock_httpx_responses([tv_resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_tmdb_get_imdb(1396, "series", "key"))
        assert result == "tt0903747"

    def test_series_fallback_to_movie(self):
        from arm.services.metadata import _tmdb_get_imdb
        tv_fail = {"status_code": 34, "status_message": "not found"}
        movie_resp = {"external_ids": {"imdb_id": "tt0133093"}}
        ctx = _mock_httpx_responses([tv_fail, movie_resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_tmdb_get_imdb(603, "series", "key"))
        assert result == "tt0133093"

    def test_movie_fallback_to_tv(self):
        """Movie endpoint fails (status_code in response) → falls back to TV external_ids."""
        from arm.services.metadata import _tmdb_get_imdb
        movie_fail = {"status_code": 34, "status_message": "not found"}
        tv_resp = {"imdb_id": "tt0903747"}
        ctx = _mock_httpx_responses([movie_fail, tv_resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_tmdb_get_imdb(1396, "movie", "key"))
        assert result == "tt0903747"

    def test_movie_both_fail_returns_none(self):
        """Both movie and TV endpoints fail → returns None."""
        from arm.services.metadata import _tmdb_get_imdb
        fail = {"status_code": 34, "status_message": "not found"}
        ctx = _mock_httpx_responses([fail, fail])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_tmdb_get_imdb(999, "movie", "key"))
        assert result is None

    def test_series_both_fail_returns_none(self):
        """Series TV and movie fallback both fail → returns None."""
        from arm.services.metadata import _tmdb_get_imdb
        fail = {"status_code": 34, "status_message": "not found"}
        ctx = _mock_httpx_responses([fail, fail])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_tmdb_get_imdb(999, "series", "key"))
        assert result is None

    def test_exception_returns_none(self):
        from arm.services.metadata import _tmdb_get_imdb
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(
                side_effect=httpx.ConnectError("offline"))
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_tmdb_get_imdb(603, "movie", "key"))
        assert result is None

    def test_value_error_returns_none(self):
        """Non-httpx exceptions (ValueError, KeyError) also caught → returns None."""
        from arm.services.metadata import _tmdb_get_imdb
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(
                side_effect=ValueError("bad json"))
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(_tmdb_get_imdb(603, "movie", "key"))
        assert result is None


# ---------------------------------------------------------------------------
# search_music / get_music_details
# ---------------------------------------------------------------------------


class TestSearchMusic:
    def test_basic_search(self):
        from arm.services.metadata import search_music
        mb_resp = {
            "count": 1,
            "releases": [{
                "id": "mbid-123",
                "title": "Master of Puppets",
                "artist-credit": [{"name": "Metallica"}],
                "date": "1986-03-03",
                "track-count": 8,
                "media": [{"format": "CD"}],
                "label-info": [{"label": {"name": "Elektra"}}],
                "release-group": {"primary-type": "Album"},
                "country": "US",
            }],
        }
        mock_resp = unittest.mock.MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mb_resp
        mock_resp.raise_for_status = unittest.mock.MagicMock()

        ctx = unittest.mock.AsyncMock()
        ctx.get = unittest.mock.AsyncMock(return_value=mock_resp)

        with unittest.mock.patch('arm.services.metadata._mb_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(search_music("Metallica"))

        assert result["total"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Master of Puppets"
        assert result["results"][0]["artist"] == "Metallica"
        assert result["results"][0]["format"] == "CD"
        assert result["results"][0]["label"] == "Elektra"

    def test_with_artist_filter(self):
        """Artist filter wraps query in release:"..." AND artist:"..." Lucene syntax."""
        from arm.services.metadata import search_music
        mb_resp = {"count": 0, "releases": []}
        mock_resp = unittest.mock.MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mb_resp
        mock_resp.raise_for_status = unittest.mock.MagicMock()

        ctx = unittest.mock.AsyncMock()
        ctx.get = unittest.mock.AsyncMock(return_value=mock_resp)

        with unittest.mock.patch('arm.services.metadata._mb_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            _run(search_music("Master of Puppets", artist="Metallica"))

        call_params = ctx.get.call_args[1]["params"]
        assert 'artist:"Metallica"' in call_params["query"]
        assert 'release:"Master of Puppets"' in call_params["query"]

    def test_with_all_filters(self):
        """All optional filters are included in the Lucene query."""
        from arm.services.metadata import search_music
        mb_resp = {"count": 0, "releases": []}
        mock_resp = unittest.mock.MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mb_resp
        mock_resp.raise_for_status = unittest.mock.MagicMock()

        ctx = unittest.mock.AsyncMock()
        ctx.get = unittest.mock.AsyncMock(return_value=mock_resp)

        with unittest.mock.patch('arm.services.metadata._mb_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            _run(search_music("Test", release_type="Album", format="CD",
                              country="US", status="Official", tracks=12))

        call_params = ctx.get.call_args[1]["params"]
        query = call_params["query"]
        assert "type:Album" in query
        assert 'format:"CD"' in query
        assert "country:US" in query
        assert "status:Official" in query
        assert "tracks:12" in query

    def test_offset_passed_when_nonzero(self):
        """Offset > 0 is included in the HTTP params."""
        from arm.services.metadata import search_music
        mb_resp = {"count": 0, "releases": []}
        mock_resp = unittest.mock.MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mb_resp
        mock_resp.raise_for_status = unittest.mock.MagicMock()

        ctx = unittest.mock.AsyncMock()
        ctx.get = unittest.mock.AsyncMock(return_value=mock_resp)

        with unittest.mock.patch('arm.services.metadata._mb_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            _run(search_music("Test", offset=30))

        call_params = ctx.get.call_args[1]["params"]
        assert call_params["offset"] == "30"

    def test_network_error_returns_empty(self):
        from arm.services.metadata import search_music
        with unittest.mock.patch('arm.services.metadata._mb_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(
                side_effect=httpx.ConnectError("offline"))
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(search_music("Metallica"))
        assert result == {"results": [], "total": 0}


class TestGetMusicDetails:
    def test_valid_release(self):
        from arm.services.metadata import get_music_details
        mb_resp = {
            "id": "mbid-123",
            "title": "Master of Puppets",
            "artist-credit": [{"name": "Metallica"}],
            "date": "1986-03-03",
            "media": [{"format": "CD", "track-count": 2, "tracks": [
                {"number": "1", "title": "Battery", "length": 312000,
                 "recording": {"title": "Battery", "length": 312000}},
                {"number": "2", "title": "Master", "length": 515000,
                 "recording": {"title": "Master of Puppets", "length": 515000}},
            ]}],
            "label-info": [{"label": {"name": "Elektra"}, "catalog-number": "9 60439-2"}],
            "release-group": {"primary-type": "Album"},
            "country": "US",
            "barcode": "075596043922",
            "status": "Official",
        }
        mock_resp = unittest.mock.MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mb_resp
        mock_resp.raise_for_status = unittest.mock.MagicMock()

        ctx = unittest.mock.AsyncMock()
        ctx.get = unittest.mock.AsyncMock(return_value=mock_resp)

        with unittest.mock.patch('arm.services.metadata._mb_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(get_music_details("mbid-123"))

        assert result["title"] == "Master of Puppets"
        assert result["artist"] == "Metallica"
        assert len(result["tracks"]) == 2
        assert result["tracks"][0]["title"] == "Battery"
        assert result["barcode"] == "075596043922"
        assert result["catalog_number"] == "9 60439-2"

    def test_track_length_fallback_to_recording(self):
        """When track.length is None, falls back to recording.length."""
        from arm.services.metadata import get_music_details
        mb_resp = {
            "id": "mbid-456", "title": "Album",
            "artist-credit": [{"name": "Artist"}], "date": "2020",
            "media": [{"format": "CD", "track-count": 1, "tracks": [
                {"number": "1", "title": "Song", "length": None,
                 "recording": {"title": "Song", "length": 240000}},
            ]}],
            "label-info": [], "release-group": {},
        }
        mock_resp = unittest.mock.MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mb_resp
        mock_resp.raise_for_status = unittest.mock.MagicMock()
        ctx = unittest.mock.AsyncMock()
        ctx.get = unittest.mock.AsyncMock(return_value=mock_resp)

        with unittest.mock.patch('arm.services.metadata._mb_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(get_music_details("mbid-456"))

        assert result["tracks"][0]["length_ms"] == 240000

    def test_multiple_media(self):
        """Release with 2 discs (media) accumulates all tracks."""
        from arm.services.metadata import get_music_details
        mb_resp = {
            "id": "mbid-789", "title": "Double Album",
            "artist-credit": [{"name": "Artist"}], "date": "2020",
            "media": [
                {"format": "CD", "track-count": 1, "tracks": [
                    {"number": "1", "length": 100, "recording": {"title": "Disc 1 Track"}},
                ]},
                {"format": "CD", "track-count": 1, "tracks": [
                    {"number": "1", "length": 200, "recording": {"title": "Disc 2 Track"}},
                ]},
            ],
            "label-info": [], "release-group": {},
        }
        mock_resp = unittest.mock.MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mb_resp
        mock_resp.raise_for_status = unittest.mock.MagicMock()
        ctx = unittest.mock.AsyncMock()
        ctx.get = unittest.mock.AsyncMock(return_value=mock_resp)

        with unittest.mock.patch('arm.services.metadata._mb_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(get_music_details("mbid-789"))

        assert len(result["tracks"]) == 2
        assert result["track_count"] == 2

    def test_empty_barcode_normalized_to_none(self):
        """Empty barcode string becomes None."""
        from arm.services.metadata import get_music_details
        mb_resp = {
            "id": "mbid-abc", "title": "Album",
            "artist-credit": [{"name": "X"}], "date": "",
            "media": [{"format": "CD", "track-count": 0, "tracks": []}],
            "label-info": [], "release-group": {}, "barcode": "",
        }
        mock_resp = unittest.mock.MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mb_resp
        mock_resp.raise_for_status = unittest.mock.MagicMock()
        ctx = unittest.mock.AsyncMock()
        ctx.get = unittest.mock.AsyncMock(return_value=mock_resp)

        with unittest.mock.patch('arm.services.metadata._mb_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(get_music_details("mbid-abc"))

        assert result["barcode"] is None

    def test_404_returns_none(self):
        from arm.services.metadata import get_music_details
        mock_resp = unittest.mock.MagicMock(spec=httpx.Response)
        mock_resp.status_code = 404
        ctx = unittest.mock.AsyncMock()
        ctx.get = unittest.mock.AsyncMock(return_value=mock_resp)

        with unittest.mock.patch('arm.services.metadata._mb_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(get_music_details("bad-mbid"))
        assert result is None

    def test_network_error_returns_none(self):
        from arm.services.metadata import get_music_details
        with unittest.mock.patch('arm.services.metadata._mb_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(
                side_effect=httpx.ConnectError("offline"))
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(get_music_details("mbid-123"))
        assert result is None


# ---------------------------------------------------------------------------
# lookup_crc
# ---------------------------------------------------------------------------


class TestLookupCrc:
    def test_found(self):
        from arm.services.metadata import lookup_crc
        crc_resp = {
            "success": True,
            "results": {"0": {
                "title": "The Matrix", "year": "1999", "imdb_id": "tt0133093",
                "tmdb_id": "603", "video_type": "movie", "disctype": "dvd",
                "label": "MATRIX", "poster_img": "http://img.com/p.jpg",
                "hasnicetitle": "True", "validated": "True", "date_added": "2023-01-01",
            }},
        }
        mock_resp = unittest.mock.MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = crc_resp
        mock_resp.raise_for_status = unittest.mock.MagicMock()

        with unittest.mock.patch('httpx.AsyncClient') as mock_cls:
            ctx = unittest.mock.AsyncMock()
            ctx.get = unittest.mock.AsyncMock(return_value=mock_resp)
            mock_cls.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_cls.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(lookup_crc("abc123"))

        assert result["found"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "The Matrix"
        assert result["results"][0]["poster_url"] == "http://img.com/p.jpg"

    def test_not_found(self):
        from arm.services.metadata import lookup_crc
        crc_resp = {"success": False}
        mock_resp = unittest.mock.MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = crc_resp
        mock_resp.raise_for_status = unittest.mock.MagicMock()

        with unittest.mock.patch('httpx.AsyncClient') as mock_cls:
            ctx = unittest.mock.AsyncMock()
            ctx.get = unittest.mock.AsyncMock(return_value=mock_resp)
            mock_cls.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_cls.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(lookup_crc("unknown_crc"))

        assert result["found"] is False
        assert result["results"] == []

    def test_network_error(self):
        from arm.services.metadata import lookup_crc
        with unittest.mock.patch('httpx.AsyncClient') as mock_cls:
            mock_cls.return_value.__aenter__ = unittest.mock.AsyncMock(
                side_effect=httpx.ConnectError("offline"))
            mock_cls.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(lookup_crc("abc123"))

        assert result["found"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# test_configured_key
# ---------------------------------------------------------------------------


class TestConfiguredKey:
    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': '',
    })
    def test_no_key_returns_failure(self):
        from arm.services.metadata import test_configured_key
        result = _run(test_configured_key())
        assert result["success"] is False
        assert "No API key" in result["message"]

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': 'valid_key',
    })
    def test_omdb_valid_key(self):
        from arm.services.metadata import test_configured_key
        resp = {"Response": "True", "Title": "The Matrix"}
        ctx = _mock_httpx_responses([resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(test_configured_key())
        assert result["success"] is True
        assert result["provider"] == "omdb"

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': 'bad_key',
    })
    def test_omdb_auth_error(self):
        from arm.services.metadata import test_configured_key
        ctx = _mock_httpx_responses([{"_status": 401}])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(test_configured_key())
        assert result["success"] is False
        assert "Invalid" in result["message"]

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': 'key',
    })
    def test_omdb_invalid_key_in_response(self):
        from arm.services.metadata import test_configured_key
        resp = {"Response": "False", "Error": "Invalid API key!"}
        ctx = _mock_httpx_responses([resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(test_configured_key())
        assert result["success"] is False
        assert "Invalid" in result["message"]

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'tmdb', 'TMDB_API_KEY': 'tmdb_key',
    })
    def test_tmdb_valid_key(self):
        from arm.services.metadata import test_configured_key
        ctx = _mock_httpx_responses([{"images": {}}])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(test_configured_key())
        assert result["success"] is True
        assert result["provider"] == "tmdb"

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': 'key',
    })
    def test_timeout(self):
        from arm.services.metadata import test_configured_key
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(
                side_effect=httpx.TimeoutException("timeout"))
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(test_configured_key())
        assert result["success"] is False
        assert "timed out" in result["message"]

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': 'key',
    })
    def test_connect_error(self):
        from arm.services.metadata import test_configured_key
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(
                side_effect=httpx.ConnectError("dns failure"))
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(test_configured_key())
        assert result["success"] is False
        assert "network" in result["message"].lower() or "connect" in result["message"].lower()

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': 'key',
    })
    def test_omdb_non_json_unicode_error(self):
        """UnicodeDecodeError from resp.json() is handled like ValueError."""
        from arm.services.metadata import test_configured_key

        async def mock_get(url, **kwargs):
            resp = unittest.mock.MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.json.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "bad")
            resp.text = ""
            return resp

        ctx = unittest.mock.AsyncMock()
        ctx.get = mock_get
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(test_configured_key())
        assert result["success"] is False

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': 'key',
    })
    def test_omdb_non_json_non_200(self):
        """Non-JSON response with non-200 status returns HTTP status in message."""
        from arm.services.metadata import test_configured_key

        async def mock_get(url, **kwargs):
            resp = unittest.mock.MagicMock(spec=httpx.Response)
            resp.status_code = 500
            resp.json.side_effect = ValueError("not JSON")
            resp.text = "Server Error"
            return resp

        ctx = unittest.mock.AsyncMock()
        ctx.get = mock_get
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(test_configured_key())
        assert result["success"] is False
        assert "500" in result["message"]

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': 'key',
    })
    def test_omdb_error_message_not_invalid_key(self):
        """OMDb error message that isn't 'Invalid API key' returns the actual error."""
        from arm.services.metadata import test_configured_key
        resp = {"Response": "False", "Error": "Request limit reached!"}
        ctx = _mock_httpx_responses([resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(test_configured_key())
        assert result["success"] is False
        assert "Request limit reached" in result["message"]

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': 'key',
    })
    def test_omdb_no_response_no_error_accepted(self):
        """OMDb response without Response=True and no Error → key accepted."""
        from arm.services.metadata import test_configured_key
        resp = {"some": "data"}  # no Response, no Error
        ctx = _mock_httpx_responses([resp])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(test_configured_key())
        assert result["success"] is True
        assert "accepted" in result["message"].lower()

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'tmdb', 'TMDB_API_KEY': 'key',
    })
    def test_tmdb_unexpected_status(self):
        """TMDb returns unexpected status code (not 200, 401, 403)."""
        from arm.services.metadata import test_configured_key
        ctx = _mock_httpx_responses([{"_status": 500}])
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(test_configured_key())
        assert result["success"] is False
        assert "500" in result["message"]

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': 'key',
    })
    def test_generic_exception(self):
        """Generic Exception is caught and returns failure with type name."""
        from arm.services.metadata import test_configured_key
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(
                side_effect=RuntimeError("unexpected"))
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(test_configured_key())
        assert result["success"] is False
        assert "RuntimeError" in result["message"]

    @unittest.mock.patch.dict('arm.config.config.arm_config', {
        'METADATA_PROVIDER': 'omdb', 'OMDB_API_KEY': 'key',
    })
    def test_omdb_non_json_response(self):
        from arm.services.metadata import test_configured_key

        async def mock_get(url, **kwargs):
            resp = unittest.mock.MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.json.side_effect = ValueError("not JSON")
            resp.text = "<html>error</html>"
            return resp

        ctx = unittest.mock.AsyncMock()
        ctx.get = mock_get
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            result = _run(test_configured_key())
        assert result["success"] is False
        assert "invalid response" in result["message"].lower()


# ---------------------------------------------------------------------------
# _omdb_search — fallback ?t= auth error
# ---------------------------------------------------------------------------


class TestOmdbSearchFallback:
    """Test _omdb_search fallback ?t= exact match path."""

    def test_fallback_auth_error_raises(self):
        """Auth error (401/403) on fallback ?t= raises MetadataConfigError."""
        from arm.services.metadata import _omdb_search, MetadataConfigError

        call_count = [0]

        async def mock_get(url, **kwargs):
            call_count[0] += 1
            resp = unittest.mock.MagicMock(spec=httpx.Response)
            if call_count[0] == 1:
                # First ?s= call returns no results
                resp.status_code = 200
                resp.json.return_value = {"Response": "False"}
            else:
                # Second ?t= call returns 401
                resp.status_code = 401
            return resp

        ctx = unittest.mock.AsyncMock()
        ctx.get = mock_get
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            with pytest.raises(MetadataConfigError):
                _run(_omdb_search("test", None, "badkey"))

    def test_fallback_returns_single_result(self):
        """Fallback ?t= returns a single result when ?s= finds nothing."""
        from arm.services.metadata import _omdb_search

        call_count = [0]

        async def mock_get(url, **kwargs):
            call_count[0] += 1
            resp = unittest.mock.MagicMock(spec=httpx.Response)
            resp.status_code = 200
            if call_count[0] == 1:
                resp.json.return_value = {"Response": "False"}
            else:
                resp.json.return_value = {
                    "Response": "True", "Title": "42", "Year": "2013",
                    "imdbID": "tt0453562", "Type": "movie", "Poster": "N/A"
                }
            return resp

        ctx = unittest.mock.AsyncMock()
        ctx.get = mock_get
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            results = _run(_omdb_search("42", None, "key"))
        assert len(results) == 1
        assert results[0]["title"] == "42"

    def test_fallback_no_results(self):
        """Fallback ?t= also returns nothing — empty list."""
        from arm.services.metadata import _omdb_search

        call_count = [0]

        async def mock_get(url, **kwargs):
            call_count[0] += 1
            resp = unittest.mock.MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.json.return_value = {"Response": "False"}
            return resp

        ctx = unittest.mock.AsyncMock()
        ctx.get = mock_get
        with unittest.mock.patch('arm.services.metadata._http_client') as mock_client:
            mock_client.return_value.__aenter__ = unittest.mock.AsyncMock(return_value=ctx)
            mock_client.return_value.__aexit__ = unittest.mock.AsyncMock(return_value=False)
            results = _run(_omdb_search("nonexistent", None, "key"))
        assert results == []


# ---------------------------------------------------------------------------
# lookup_crc — entries with missing optional keys
# ---------------------------------------------------------------------------


class TestLookupCrcEdgeCases:
    """Test lookup_crc with missing fields in CRC database results."""

    def test_missing_optional_fields_default_to_empty(self):
        """CRC result entries with missing keys get empty string defaults."""
        from arm.services.metadata import lookup_crc

        raw_response = {
            "success": True,
            "results": {
                "1": {"title": "Matrix"}  # all other fields missing
            }
        }
        with unittest.mock.patch('arm.services.metadata.httpx') as mock_httpx:
            mock_client = unittest.mock.AsyncMock()
            mock_resp = unittest.mock.MagicMock(spec=httpx.Response)
            mock_resp.status_code = 200
            mock_resp.json.return_value = raw_response
            mock_resp.raise_for_status = unittest.mock.MagicMock()
            mock_client.get.return_value = mock_resp
            mock_httpx.AsyncClient.return_value.__aenter__ = unittest.mock.AsyncMock(
                return_value=mock_client)
            mock_httpx.AsyncClient.return_value.__aexit__ = unittest.mock.AsyncMock(
                return_value=False)
            result = _run(lookup_crc("abc123"))
        assert result["found"] is True
        assert len(result["results"]) == 1
        entry = result["results"][0]
        assert entry["title"] == "Matrix"
        assert entry["year"] == ""
        assert entry["imdb_id"] == ""
        assert entry["video_type"] == ""

    def test_empty_results_dict(self):
        """Success=True but empty results dict returns found=False."""
        from arm.services.metadata import lookup_crc

        raw_response = {"success": True, "results": {}}
        with unittest.mock.patch('arm.services.metadata.httpx') as mock_httpx:
            mock_client = unittest.mock.AsyncMock()
            mock_resp = unittest.mock.MagicMock(spec=httpx.Response)
            mock_resp.status_code = 200
            mock_resp.json.return_value = raw_response
            mock_resp.raise_for_status = unittest.mock.MagicMock()
            mock_client.get.return_value = mock_resp
            mock_httpx.AsyncClient.return_value.__aenter__ = unittest.mock.AsyncMock(
                return_value=mock_client)
            mock_httpx.AsyncClient.return_value.__aexit__ = unittest.mock.AsyncMock(
                return_value=False)
            result = _run(lookup_crc("abc123"))
        assert result["found"] is False
        assert result["results"] == []

    def test_multiple_crc_results(self):
        """Multiple results in the CRC database response are all returned."""
        from arm.services.metadata import lookup_crc

        raw_response = {
            "success": True,
            "results": {
                "1": {"title": "Matrix", "year": "1999", "imdb_id": "tt0133093",
                       "video_type": "movie", "poster_img": "http://img/1.jpg"},
                "2": {"title": "Matrix Reloaded", "year": "2003",
                       "imdb_id": "tt0234215", "video_type": "movie"},
            }
        }
        with unittest.mock.patch('arm.services.metadata.httpx') as mock_httpx:
            mock_client = unittest.mock.AsyncMock()
            mock_resp = unittest.mock.MagicMock(spec=httpx.Response)
            mock_resp.status_code = 200
            mock_resp.json.return_value = raw_response
            mock_resp.raise_for_status = unittest.mock.MagicMock()
            mock_client.get.return_value = mock_resp
            mock_httpx.AsyncClient.return_value.__aenter__ = unittest.mock.AsyncMock(
                return_value=mock_client)
            mock_httpx.AsyncClient.return_value.__aexit__ = unittest.mock.AsyncMock(
                return_value=False)
            result = _run(lookup_crc("abc123"))
        assert result["found"] is True
        assert len(result["results"]) == 2
