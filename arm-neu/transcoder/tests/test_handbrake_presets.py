"""Tests for the HandBrakeCLI preset list helper + endpoint."""

from unittest.mock import AsyncMock, patch

import pytest

import handbrake_presets
from handbrake_presets import _parse_preset_list, list_handbrake_presets


# ---- Parser unit tests -----------------------------------------------------


class TestParsePresetList:
    def test_canonical_format(self):
        output = """\
General/
    Fast 1080p30
    HQ 1080p30 Surround
    Super HQ 1080p30 Surround
Web/
    Vimeo YouTube HQ 1080p60
"""
        result = _parse_preset_list(output)
        assert result == {
            "General": [
                "Fast 1080p30",
                "HQ 1080p30 Surround",
                "Super HQ 1080p30 Surround",
            ],
            "Web": ["Vimeo YouTube HQ 1080p60"],
        }

    def test_skips_blank_lines(self):
        output = """\
General/
    Fast 1080p30

    HQ 1080p30 Surround
"""
        result = _parse_preset_list(output)
        assert result == {"General": ["Fast 1080p30", "HQ 1080p30 Surround"]}

    def test_drops_empty_categories(self):
        # A category with no presets shouldn't appear in the result.
        output = """\
General/
    Fast 1080p30
Web/
"""
        result = _parse_preset_list(output)
        assert result == {"General": ["Fast 1080p30"]}
        assert "Web" not in result

    def test_handles_status_chatter_before_first_category(self):
        # Some HandBrake versions emit version banners on stderr before
        # the preset list. Anything before the first "Category/" line
        # must be ignored without raising.
        output = """\
HandBrake 1.7.3 (2024010500) - Linux x86_64
General/
    Fast 1080p30
"""
        result = _parse_preset_list(output)
        assert result == {"General": ["Fast 1080p30"]}

    def test_empty_input(self):
        assert _parse_preset_list("") == {}

    def test_garbage_input_returns_empty(self):
        # No category lines at all, just noise.
        output = "this is not a preset list\nat all\n"
        assert _parse_preset_list(output) == {}


# ---- Endpoint integration --------------------------------------------------


class TestListHandbrakePresets:
    @pytest.fixture(autouse=True)
    def _reset_cache(self):
        handbrake_presets._reset_cache_for_tests()
        yield
        handbrake_presets._reset_cache_for_tests()

    @pytest.mark.asyncio
    async def test_happy_path(self):
        fake_proc = AsyncMock()
        fake_proc.communicate = AsyncMock(return_value=(b"General/\n    Fast 1080p30\n", b""))

        with patch(
            "handbrake_presets.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=fake_proc),
        ):
            result = await list_handbrake_presets()

        assert result == {"General": ["Fast 1080p30"]}

    @pytest.mark.asyncio
    async def test_handbrake_missing(self):
        with patch(
            "handbrake_presets.asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=FileNotFoundError("HandBrakeCLI not found")),
        ):
            result = await list_handbrake_presets()

        assert result == {}

    @pytest.mark.asyncio
    async def test_subprocess_timeout(self):
        # Mock communicate() to hang past the timeout. The helper should
        # cancel and return {} rather than re-raising.
        async def _hang(*_a, **_kw):
            import asyncio as _aio
            await _aio.sleep(60)

        fake_proc = AsyncMock()
        fake_proc.communicate = _hang
        fake_proc.kill = lambda: None

        with (
            patch(
                "handbrake_presets.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=fake_proc),
            ),
            patch("handbrake_presets._PRESET_LIST_TIMEOUT", 0.05),
        ):
            result = await list_handbrake_presets()

        assert result == {}

    @pytest.mark.asyncio
    async def test_caches_result(self):
        # Second call should not re-invoke create_subprocess_exec.
        fake_proc = AsyncMock()
        fake_proc.communicate = AsyncMock(return_value=(b"General/\n    Fast 1080p30\n", b""))
        spy = AsyncMock(return_value=fake_proc)

        with patch("handbrake_presets.asyncio.create_subprocess_exec", new=spy):
            await list_handbrake_presets()
            await list_handbrake_presets()

        assert spy.call_count == 1
