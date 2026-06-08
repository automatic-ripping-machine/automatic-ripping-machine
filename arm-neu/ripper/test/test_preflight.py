"""Tests for preflight readiness checks."""

import asyncio
import os
import unittest.mock

import httpx
import pytest

from arm.services.tvdb import validate_tvdb_key


class TestTvdbKeyValidation:
    """Test validate_tvdb_key() API key validation."""

    def test_validate_tvdb_key_valid(self):
        """Successful TVDB login returns success=True."""
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = {"data": {"token": "tok_abc123"}}
        mock_response.raise_for_status = unittest.mock.MagicMock()

        async def mock_post(url, json=None):
            return mock_response

        mock_client = unittest.mock.MagicMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = unittest.mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = unittest.mock.AsyncMock(return_value=False)

        with unittest.mock.patch("arm.services.tvdb.httpx.AsyncClient",
                                 return_value=mock_client):
            result = asyncio.run(validate_tvdb_key("valid-api-key-123"))

        assert result["success"] is True
        assert "valid" in result["message"].lower()

    def test_validate_tvdb_key_invalid(self):
        """401 response returns success=False with 'Invalid' message."""
        mock_request = unittest.mock.MagicMock()
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 401

        async def mock_post(url, json=None):
            raise httpx.HTTPStatusError(
                "Unauthorized", request=mock_request, response=mock_resp
            )

        mock_client = unittest.mock.MagicMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = unittest.mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = unittest.mock.AsyncMock(return_value=False)

        with unittest.mock.patch("arm.services.tvdb.httpx.AsyncClient",
                                 return_value=mock_client):
            result = asyncio.run(validate_tvdb_key("bad-key"))

        assert result["success"] is False
        assert "Invalid" in result["message"]

    def test_validate_tvdb_key_timeout(self):
        """Timeout returns success=False with 'timeout' in message."""
        async def mock_post(url, json=None):
            raise httpx.ReadTimeout("timed out")

        mock_client = unittest.mock.MagicMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = unittest.mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = unittest.mock.AsyncMock(return_value=False)

        with unittest.mock.patch("arm.services.tvdb.httpx.AsyncClient",
                                 return_value=mock_client):
            result = asyncio.run(validate_tvdb_key("some-key"))

        assert result["success"] is False
        assert "timed out" in result["message"].lower()

    def test_validate_tvdb_key_empty(self):
        """Empty API key returns failure without making a network call."""
        result = asyncio.run(validate_tvdb_key(""))
        assert result["success"] is False
        assert "empty" in result["message"].lower()

    def test_validate_tvdb_key_whitespace_only(self):
        """Whitespace-only API key is treated as empty."""
        result = asyncio.run(validate_tvdb_key("   "))
        assert result["success"] is False
        assert "empty" in result["message"].lower()

    def test_validate_tvdb_key_none(self):
        """None API key returns failure."""
        result = asyncio.run(validate_tvdb_key(None))
        assert result["success"] is False
        assert "empty" in result["message"].lower()

    def test_validate_tvdb_key_no_token_in_response(self):
        """Login succeeds but response lacks a token."""
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = {"data": {}}
        mock_response.raise_for_status = unittest.mock.MagicMock()

        async def mock_post(url, json=None):
            return mock_response

        mock_client = unittest.mock.MagicMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = unittest.mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = unittest.mock.AsyncMock(return_value=False)

        with unittest.mock.patch("arm.services.tvdb.httpx.AsyncClient",
                                 return_value=mock_client):
            result = asyncio.run(validate_tvdb_key("some-key"))

        assert result["success"] is False
        assert "no token" in result["message"].lower()

    def test_validate_tvdb_key_connect_error(self):
        """Connection error returns failure with network message."""
        async def mock_post(url, json=None):
            raise httpx.ConnectError("DNS resolution failed")

        mock_client = unittest.mock.MagicMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = unittest.mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = unittest.mock.AsyncMock(return_value=False)

        with unittest.mock.patch("arm.services.tvdb.httpx.AsyncClient",
                                 return_value=mock_client):
            result = asyncio.run(validate_tvdb_key("some-key"))

        assert result["success"] is False
        assert "connect" in result["message"].lower()

    def test_validate_tvdb_key_server_error(self):
        """Non-401 HTTP error returns the status code."""
        mock_request = unittest.mock.MagicMock()
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 500

        async def mock_post(url, json=None):
            raise httpx.HTTPStatusError(
                "Internal Server Error", request=mock_request, response=mock_resp
            )

        mock_client = unittest.mock.MagicMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = unittest.mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = unittest.mock.AsyncMock(return_value=False)

        with unittest.mock.patch("arm.services.tvdb.httpx.AsyncClient",
                                 return_value=mock_client):
            result = asyncio.run(validate_tvdb_key("some-key"))

        assert result["success"] is False
        assert "500" in result["message"]

    def test_validate_tvdb_key_strips_whitespace(self):
        """API key with leading/trailing whitespace is stripped before use."""
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = {"data": {"token": "tok_abc"}}
        mock_response.raise_for_status = unittest.mock.MagicMock()

        posted_payloads = []

        async def mock_post(url, json=None):
            posted_payloads.append(json)
            return mock_response

        mock_client = unittest.mock.MagicMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = unittest.mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = unittest.mock.AsyncMock(return_value=False)

        with unittest.mock.patch("arm.services.tvdb.httpx.AsyncClient",
                                 return_value=mock_client):
            result = asyncio.run(validate_tvdb_key("  my-key  "))

        assert result["success"] is True
        assert posted_payloads[0]["apikey"] == "my-key"


# -------------------------------------------------------------------
# Preflight service tests
# -------------------------------------------------------------------

from arm.services.preflight import resolve_host_path, check_path, run_checks


class TestResolveHostPath:
    """Test resolve_host_path() bind-mount parsing and env var fallback."""

    def test_mountinfo_parsing(self, tmp_path):
        """Finds host path from a Docker bind-mount mountinfo line."""
        # Docker bind mounts have the host path in the root field (field 3)
        fake_mountinfo = (
            "36 1 8:1 / / rw - ext4 /dev/sda1 rw\n"
            "100 36 8:1 /home/arm/media /home/arm/media rw,relatime - ext4 /dev/sda1 rw\n"
        )
        with unittest.mock.patch(
            "builtins.open", unittest.mock.mock_open(read_data=fake_mountinfo)
        ):
            result = resolve_host_path("/home/arm/media")
        assert result == "/home/arm/media"

    def test_mountinfo_subpath(self):
        """Subpath under a bind mount resolves correctly."""
        fake_mountinfo = (
            "100 36 8:1 /nfs/shared/media /home/arm/media rw,relatime - ext4 /dev/sda1 rw\n"
        )
        with unittest.mock.patch(
            "builtins.open", unittest.mock.mock_open(read_data=fake_mountinfo)
        ):
            result = resolve_host_path("/home/arm/media/raw/movie.mkv")
        assert result == "/nfs/shared/media/raw/movie.mkv"

    def test_env_var_fallback(self):
        """Falls back to env var when mountinfo is not available."""
        with unittest.mock.patch(
            "builtins.open", side_effect=OSError("no mountinfo")
        ):
            with unittest.mock.patch.dict(
                os.environ, {"ARM_MEDIA_PATH": "/mnt/nas/media"}
            ):
                result = resolve_host_path("/home/arm/media")
        assert result == "/mnt/nas/media"

    def test_env_var_subpath(self):
        """Env var fallback preserves the path suffix."""
        with unittest.mock.patch(
            "builtins.open", side_effect=OSError("no mountinfo")
        ):
            with unittest.mock.patch.dict(
                os.environ, {"ARM_MEDIA_PATH": "/mnt/nas/media"}
            ):
                result = resolve_host_path("/home/arm/media/raw")
        assert result == "/mnt/nas/media/raw"

    def test_unknown_path_returns_none(self):
        """Unknown path with no mountinfo and no env var returns None."""
        with unittest.mock.patch(
            "builtins.open", side_effect=OSError("no mountinfo")
        ):
            with unittest.mock.patch.dict(os.environ, {}, clear=False):
                # Remove any ARM env vars that might interfere
                env_clean = {
                    k: v for k, v in os.environ.items()
                    if k not in ("ARM_MEDIA_PATH", "ARM_CONFIG_PATH",
                                 "ARM_LOGS_PATH", "ARM_MUSIC_PATH")
                }
                with unittest.mock.patch.dict(os.environ, env_clean, clear=True):
                    result = resolve_host_path("/some/random/path")
        assert result is None

    def test_empty_path_returns_none(self):
        """Empty container path returns None."""
        result = resolve_host_path("")
        assert result is None


class TestCheckPath:
    """Test check_path() existence, writability, and UID/GID checks."""

    def test_existing_writable_path(self, tmp_path):
        """Existing path with correct ownership passes all checks."""
        uid = os.getuid()
        gid = os.getgid()

        with unittest.mock.patch(
            "arm.services.preflight.resolve_host_path", return_value=None
        ):
            result = check_path("test_dir", str(tmp_path), uid, gid)

        assert result["name"] == "test_dir"
        assert result["exists"] is True
        assert result["writable"] is True
        assert result["owner_uid"] == uid
        assert result["owner_gid"] == gid
        assert result["match"] is True

    def test_nonexistent_path(self):
        """Non-existent path reports exists=False."""
        with unittest.mock.patch(
            "arm.services.preflight.resolve_host_path", return_value=None
        ):
            result = check_path(
                "missing", "/nonexistent/path/xyz", os.getuid(), os.getgid()
            )

        assert result["exists"] is False
        assert result["writable"] is False
        assert result["owner_uid"] is None

    def test_uid_mismatch(self, tmp_path):
        """Path owned by a different UID reports match=False."""
        uid = os.getuid()
        gid = os.getgid()
        wrong_uid = uid + 999

        with unittest.mock.patch(
            "arm.services.preflight.resolve_host_path", return_value=None
        ):
            result = check_path("test_dir", str(tmp_path), wrong_uid, gid)

        assert result["exists"] is True
        assert result["match"] is False
        assert result["expected_uid"] == wrong_uid
        assert result["owner_uid"] == uid


class TestRunChecks:
    """Test run_checks() response shape and content."""

    def test_response_shape(self):
        """run_checks() returns arm_uid, arm_gid, checks (4 items), paths."""
        omdb_check = {"name": "omdb_key", "success": True, "message": "OK", "fixable": False}
        tmdb_check = {"name": "tmdb_key", "success": False, "message": "Not configured", "fixable": False}
        tvdb_check = {"name": "tvdb_key", "success": False, "message": "Not configured", "fixable": False}
        makemkv_check = {"name": "makemkv_key", "success": True, "message": "Valid", "fixable": True}

        mock_paths = [
            {
                "name": "RAW_PATH",
                "container_path": "/home/arm/media/raw",
                "host_path": None,
                "exists": True,
                "writable": True,
                "owner_uid": 1000,
                "owner_gid": 1000,
                "expected_uid": 1000,
                "expected_gid": 1000,
                "match": True,
                "fixable": False,
            }
        ]

        async def fake_omdb():
            return omdb_check

        async def fake_tmdb():
            return tmdb_check

        async def fake_tvdb():
            return tvdb_check

        async def fake_makemkv():
            return makemkv_check

        with unittest.mock.patch("arm.services.preflight._check_omdb_key", fake_omdb), \
             unittest.mock.patch("arm.services.preflight._check_tmdb_key", fake_tmdb), \
             unittest.mock.patch("arm.services.preflight._check_tvdb_key", fake_tvdb), \
             unittest.mock.patch("arm.services.preflight._check_makemkv_key", fake_makemkv), \
             unittest.mock.patch("arm.services.preflight._get_path_checks", return_value=mock_paths):
            result = asyncio.run(run_checks())

        assert "arm_uid" in result
        assert "arm_gid" in result
        assert isinstance(result["arm_uid"], int)
        assert isinstance(result["arm_gid"], int)

        assert "checks" in result
        assert len(result["checks"]) == 4
        check_names = [c["name"] for c in result["checks"]]
        assert check_names == ["omdb_key", "tmdb_key", "tvdb_key", "makemkv_key"]

        assert "paths" in result
        assert isinstance(result["paths"], list)
        assert len(result["paths"]) == 1
        assert result["paths"][0]["name"] == "RAW_PATH"

    def test_checks_have_required_fields(self):
        """Each check in the response has name, success, message, fixable."""
        async def fake_check():
            return {"name": "test", "success": True, "message": "OK", "fixable": False}

        mock_paths = []

        with unittest.mock.patch("arm.services.preflight._check_omdb_key", fake_check), \
             unittest.mock.patch("arm.services.preflight._check_tmdb_key", fake_check), \
             unittest.mock.patch("arm.services.preflight._check_tvdb_key", fake_check), \
             unittest.mock.patch("arm.services.preflight._check_makemkv_key", fake_check), \
             unittest.mock.patch("arm.services.preflight._get_path_checks", return_value=mock_paths):
            result = asyncio.run(run_checks())

        for check in result["checks"]:
            assert "name" in check
            assert "success" in check
            assert "message" in check
            assert "fixable" in check


class TestCheckMakemkvKeyExecutor:
    """_check_makemkv_key() must offload prep_mkv() to a thread executor.

    prep_mkv() spawns a blocking subprocess that hits forum.makemkv.com.
    Running it on the asyncio loop starves all other concurrent requests
    until it returns. The fix is to dispatch via run_in_executor.
    """

    def test_prep_mkv_runs_off_event_loop(self):
        """While prep_mkv() blocks, other coroutines must still run."""
        from arm.services.preflight import _check_makemkv_key

        progress = {"ticks": 0, "prep_done": False}

        def slow_prep_mkv():
            # Simulate forum.makemkv.com hanging for ~0.5s of wall time.
            import time
            time.sleep(0.3)
            progress["prep_done"] = True

        async def ticker():
            for _ in range(5):
                await asyncio.sleep(0.05)
                progress["ticks"] += 1

        async def driver():
            with unittest.mock.patch(
                "arm.ripper.makemkv.prep_mkv", side_effect=slow_prep_mkv
            ):
                check_task = asyncio.create_task(_check_makemkv_key())
                tick_task = asyncio.create_task(ticker())
                result = await check_task
                await tick_task
                return result

        result = asyncio.run(driver())

        # The ticker must have made progress *while* prep_mkv was sleeping.
        # If prep_mkv blocked the loop, ticks would be 0 until prep_done.
        assert progress["prep_done"] is True
        assert progress["ticks"] >= 3, (
            f"event loop was starved during prep_mkv() (ticks={progress['ticks']})"
        )
        assert result["success"] is True
        assert result["name"] == "makemkv_key"
