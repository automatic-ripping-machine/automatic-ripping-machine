"""Tests for arm/services/metadata_sync.py — sync wrappers for the ripper.

Covers: search_sync, get_details_sync, lookup_crc_sync — including
MetadataConfigError propagation and network error handling.
"""

import unittest.mock

import httpx
import pytest


class TestSearchSync:
    def test_returns_results(self):
        from arm.services.metadata_sync import search_sync
        results = [{"title": "Matrix", "year": "1999"}]
        with unittest.mock.patch('arm.services.metadata.search',
                                 return_value=results):
            result = search_sync("Matrix", "1999")
            # asyncio.run calls the coroutine
        assert result == results

    def test_propagates_metadata_config_error(self):
        from arm.services.metadata import MetadataConfigError
        from arm.services.metadata_sync import search_sync
        with unittest.mock.patch('arm.services.metadata.search',
                                 side_effect=MetadataConfigError("no key")):
            with pytest.raises(MetadataConfigError):
                search_sync("Matrix")

    def test_network_error_returns_empty(self):
        from arm.services.metadata_sync import search_sync
        with unittest.mock.patch('arm.services.metadata.search',
                                 side_effect=httpx.ConnectError("offline")):
            result = search_sync("Matrix")
        assert result == []

    def test_timeout_returns_empty(self):
        from arm.services.metadata_sync import search_sync
        with unittest.mock.patch('arm.services.metadata.search',
                                 side_effect=httpx.TimeoutException("timeout")):
            result = search_sync("Matrix")
        assert result == []

    def test_http_error_returns_empty(self):
        from arm.services.metadata_sync import search_sync
        with unittest.mock.patch('arm.services.metadata.search',
                                 side_effect=httpx.HTTPError("500")):
            result = search_sync("Matrix")
        assert result == []


class TestGetDetailsSync:
    def test_returns_details(self):
        from arm.services.metadata_sync import get_details_sync
        detail = {"title": "Matrix", "year": "1999", "imdb_id": "tt0133093"}
        with unittest.mock.patch('arm.services.metadata.get_details',
                                 return_value=detail):
            result = get_details_sync("tt0133093")
        assert result == detail

    def test_returns_none(self):
        from arm.services.metadata_sync import get_details_sync
        with unittest.mock.patch('arm.services.metadata.get_details',
                                 return_value=None):
            result = get_details_sync("tt9999999")
        assert result is None

    def test_propagates_metadata_config_error(self):
        from arm.services.metadata import MetadataConfigError
        from arm.services.metadata_sync import get_details_sync
        with unittest.mock.patch('arm.services.metadata.get_details',
                                 side_effect=MetadataConfigError("no key")):
            with pytest.raises(MetadataConfigError):
                get_details_sync("tt0133093")

    def test_network_error_returns_none(self):
        from arm.services.metadata_sync import get_details_sync
        with unittest.mock.patch('arm.services.metadata.get_details',
                                 side_effect=httpx.ConnectError("offline")):
            result = get_details_sync("tt0133093")
        assert result is None


class TestLookupCrcSync:
    def test_returns_result(self):
        from arm.services.metadata_sync import lookup_crc_sync
        crc_result = {"found": True, "results": [{"title": "Matrix"}]}
        with unittest.mock.patch('arm.services.metadata.lookup_crc',
                                 return_value=crc_result):
            result = lookup_crc_sync("abc123")
        assert result["found"] is True

    def test_not_found(self):
        from arm.services.metadata_sync import lookup_crc_sync
        crc_result = {"found": False, "results": []}
        with unittest.mock.patch('arm.services.metadata.lookup_crc',
                                 return_value=crc_result):
            result = lookup_crc_sync("unknown")
        assert result["found"] is False
