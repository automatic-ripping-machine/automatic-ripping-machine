"""Unit tests for arm.ripper.aacs_keydb_download."""

import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

# Inject minimal arm.config.config so the module under test can import it.
# Load aacs_keydb_download by path to avoid pulling in arm.ripper (logger, utils, etc.).
_arm_config = types.ModuleType("arm.config.config")
_arm_config.arm_config = {}
_arm_config.arm_config_path = ""
_arm_config.abcde_config = {}
_arm_config.abcde_config_path = ""
_arm_config.apprise_config = {}
_arm_config.apprise_config_path = ""
sys.modules["arm.config.config"] = _arm_config

_test_root = Path(__file__).resolve().parents[2]
if str(_test_root) not in sys.path:
    sys.path.insert(0, str(_test_root))

_mod_path = _test_root / "arm" / "ripper" / "aacs_keydb_download.py"
_spec = importlib.util.spec_from_file_location("arm.ripper.aacs_keydb_download", _mod_path)
mod = importlib.util.module_from_spec(_spec)
sys.modules["arm.config.config"] = _arm_config
# Need arm, arm.config, and arm.ripper in sys.modules for the module's imports.
if "arm" not in sys.modules:
    sys.modules["arm"] = types.ModuleType("arm")
if "arm.config" not in sys.modules:
    _arm_cfg = types.ModuleType("arm.config")
    _arm_cfg.config = _arm_config
    sys.modules["arm.config"] = _arm_cfg
if "arm.ripper" not in sys.modules:
    sys.modules["arm.ripper"] = types.ModuleType("arm.ripper")
sys.modules["arm.config.config"] = _arm_config
_spec.loader.exec_module(mod)


class TestParseLastUpdate(unittest.TestCase):
    """Tests for parse_last_update."""

    def test_extracts_date(self):
        content = 'Some HTML\nLastUpdate: 2024-03-15\n</div>'
        self.assertEqual(mod.parse_last_update(content), "2024-03-15")

    def test_returns_none_when_missing(self):
        self.assertIsNone(mod.parse_last_update("No LastUpdate here"))
        self.assertIsNone(mod.parse_last_update(""))

    def test_strips_whitespace(self):
        content = "LastUpdate:  2024-01-01  "
        self.assertEqual(mod.parse_last_update(content), "2024-01-01")


class TestParseLinks(unittest.TestCase):
    """Tests for parse_links."""

    def test_finds_fv_download_links(self):
        content = '<a href="https://example.com/fv_download.php?lang=eng">'
        self.assertEqual(
            mod.parse_links(content),
            ["https://example.com/fv_download.php?lang=eng"],
        )

    def test_finds_multiple(self):
        content = (
            '<a href="https://a.com/fv_download.php?lang=eng"> '
            '<a href="https://b.com/fv_download.php?lang=de">'
        )
        links = mod.parse_links(content)
        self.assertEqual(len(links), 2)
        self.assertIn("https://a.com/fv_download.php?lang=eng", links)
        self.assertIn("https://b.com/fv_download.php?lang=de", links)

    def test_returns_empty_list_when_none(self):
        self.assertEqual(mod.parse_links("no links"), [])


class TestParseDateToTimestamp(unittest.TestCase):
    """Tests for parse_date_to_timestamp."""

    def test_parses_iso_date(self):
        ts = mod.parse_date_to_timestamp("2024-03-15")
        self.assertIsInstance(ts, int)
        self.assertGreater(ts, 0)

    def test_epoch_date(self):
        # Use a fixed past date; 1970-01-01 can raise OSError on some platforms.
        ts = mod.parse_date_to_timestamp("2000-01-01")
        self.assertIsInstance(ts, int)


class TestGetPrimaryDatabaseUrl(unittest.TestCase):
    """Tests for get_primary_database_url."""

    def test_returns_default_when_empty(self):
        with patch.object(mod.cfg, "arm_config", {"AACS_KEYDB_PRIMARY_URL": ""}):
            self.assertEqual(
                mod.get_primary_database_url(),
                "https://fvonline-db.bplaced.net/",
            )

    def test_returns_default_when_key_missing(self):
        with patch.object(mod.cfg, "arm_config", {}):
            self.assertEqual(
                mod.get_primary_database_url(),
                "https://fvonline-db.bplaced.net/",
            )

    def test_returns_config_value_when_set(self):
        url = "https://custom.example.com/aacs/"
        with patch.object(mod.cfg, "arm_config", {"AACS_KEYDB_PRIMARY_URL": url}):
            self.assertEqual(mod.get_primary_database_url(), url)

    def test_strips_whitespace(self):
        with patch.object(
            mod.cfg, "arm_config", {"AACS_KEYDB_PRIMARY_URL": "  https://x.com  "}
        ):
            self.assertEqual(mod.get_primary_database_url(), "https://x.com")


class TestGetAacsKeydbEnabled(unittest.TestCase):
    """Tests for get_aacs_keydb_enabled."""

    def test_returns_false_when_key_missing(self):
        with patch.object(mod.cfg, "arm_config", {}):
            self.assertFalse(mod.get_aacs_keydb_enabled())

    def test_returns_false_when_false(self):
        with patch.object(mod.cfg, "arm_config", {"AACS_KEYDB_ENABLED": False}):
            self.assertFalse(mod.get_aacs_keydb_enabled())

    def test_returns_true_when_true(self):
        with patch.object(mod.cfg, "arm_config", {"AACS_KEYDB_ENABLED": True}):
            self.assertTrue(mod.get_aacs_keydb_enabled())

    def test_parses_string_true(self):
        with patch.object(mod.cfg, "arm_config", {"AACS_KEYDB_ENABLED": "true"}):
            self.assertTrue(mod.get_aacs_keydb_enabled())
        with patch.object(mod.cfg, "arm_config", {"AACS_KEYDB_ENABLED": "yes"}):
            self.assertTrue(mod.get_aacs_keydb_enabled())

    def test_parses_string_false(self):
        with patch.object(mod.cfg, "arm_config", {"AACS_KEYDB_ENABLED": "false"}):
            self.assertFalse(mod.get_aacs_keydb_enabled())


class TestGetMinRefetchHours(unittest.TestCase):
    """Tests for get_min_refetch_hours."""

    def test_returns_24_when_key_missing(self):
        with patch.object(mod.cfg, "arm_config", {}):
            self.assertEqual(mod.get_min_refetch_hours(), 24)

    def test_returns_config_value(self):
        with patch.object(mod.cfg, "arm_config", {"AACS_KEYDB_MIN_REFETCH_HOURS": 48}):
            self.assertEqual(mod.get_min_refetch_hours(), 48)

    def test_parses_string_number(self):
        with patch.object(mod.cfg, "arm_config", {"AACS_KEYDB_MIN_REFETCH_HOURS": "12"}):
            self.assertEqual(mod.get_min_refetch_hours(), 12)

    def test_returns_0_when_zero(self):
        with patch.object(mod.cfg, "arm_config", {"AACS_KEYDB_MIN_REFETCH_HOURS": 0}):
            self.assertEqual(mod.get_min_refetch_hours(), 0)


class TestRefetchPeriod(unittest.TestCase):
    """Tests for _is_within_refetch_period and _write_last_fetch_time."""

    def test_not_within_period_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(mod._is_within_refetch_period(Path(tmp), 24))

    def test_within_period_after_recent_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            mod._write_last_fetch_time(path)
            self.assertTrue(mod._last_fetch_file(path).is_file())
            self.assertTrue(mod._is_within_refetch_period(path, 24))


class TestTryDownloadKeydbWhenDisabled(unittest.TestCase):
    """When AACS_KEYDB_ENABLED is false, try_download_keydb does nothing and returns 0."""

    def test_returns_zero_when_disabled(self):
        with patch.object(mod.cfg, "arm_config", {"AACS_KEYDB_ENABLED": False}):
            self.assertEqual(mod.try_download_keydb(), 0)


class TestGetExtraSourcesFromConfig(unittest.TestCase):
    """Tests for get_extra_sources_from_config."""

    def test_returns_empty_when_empty_string(self):
        with patch.object(mod.cfg, "arm_config", {"AACS_KEYDB_EXTRA_SOURCES": ""}):
            self.assertEqual(mod.get_extra_sources_from_config(), [])

    def test_returns_empty_when_key_missing(self):
        with patch.object(mod.cfg, "arm_config", {}):
            self.assertEqual(mod.get_extra_sources_from_config(), [])

    def test_parses_comma_separated(self):
        with patch.object(
            mod.cfg,
            "arm_config",
            {"AACS_KEYDB_EXTRA_SOURCES": "https://a.com/keydb.cfg, /path/to/local.cfg"},
        ):
            self.assertEqual(
                mod.get_extra_sources_from_config(),
                ["https://a.com/keydb.cfg", "/path/to/local.cfg"],
            )

    def test_strips_each_item(self):
        with patch.object(
            mod.cfg,
            "arm_config",
            {"AACS_KEYDB_EXTRA_SOURCES": "  url1  ,  url2  "},
        ):
            self.assertEqual(
                mod.get_extra_sources_from_config(),
                ["url1", "url2"],
            )

    def test_returns_empty_when_not_string(self):
        with patch.object(mod.cfg, "arm_config", {"AACS_KEYDB_EXTRA_SOURCES": 123}):
            self.assertEqual(mod.get_extra_sources_from_config(), [])


class TestLoadLocalUpdate(unittest.TestCase):
    """Tests for load_local_update."""

    def test_returns_epoch_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(mod.load_local_update(Path(tmp)), "1970-01-01")

    def test_returns_file_content_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "lastupdate.txt").write_text("2024-02-01")
            self.assertEqual(mod.load_local_update(path), "2024-02-01")


class TestResolveTargetDirectory(unittest.TestCase):
    """Tests for resolve_target_directory (Unix os.getuid)."""

    @unittest.skipIf(not hasattr(os, "getuid"), "os.getuid not available (e.g. Windows)")
    def test_returns_etc_xdg_when_root(self):
        with patch("os.getuid", return_value=0):
            self.assertEqual(
                mod.resolve_target_directory(),
                Path("/etc/xdg/aacs"),
            )

    @unittest.skipIf(not hasattr(os, "getuid"), "os.getuid not available (e.g. Windows)")
    def test_returns_home_config_when_non_root(self):
        with patch("os.getuid", return_value=1000), patch(
            "os.path.expanduser", return_value="/home/user"
        ):
            self.assertEqual(
                mod.resolve_target_directory(),
                Path("/home/user/.config/aacs"),
            )

    def test_returns_etc_xdg_when_getuid_unavailable(self):
        """When os.getuid is missing (e.g. Windows), returns /etc/xdg/aacs."""
        self.assertEqual(mod.resolve_target_directory(), Path("/etc/xdg/aacs"))


if __name__ == "__main__":
    unittest.main()
