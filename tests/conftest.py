"""Shared fixtures for folder import tests.

Sets up ARM_CONFIG_FILE env var and stubs hardware-dependent modules
so that importing arm.ripper.folder_scan (which triggers arm.__init__)
works without /etc/arm/config/arm.yaml or physical devices.
"""
import os
import sys
import tempfile
import types
import unittest.mock

import pytest
import yaml

# --- Stub hardware-dependent modules BEFORE any arm imports ---
if "discid" not in sys.modules:
    _discid_stub = types.ModuleType("discid")
    _discid_stub.read = unittest.mock.MagicMock()
    _discid_stub.put = unittest.mock.MagicMock()
    _discid_stub.Disc = unittest.mock.MagicMock()
    _discid_stub.DiscError = type("DiscError", (Exception,), {})
    sys.modules["discid"] = _discid_stub
    sys.modules["discid.disc"] = _discid_stub
    sys.modules["discid.libdiscid"] = _discid_stub

try:
    import pyudev  # noqa: F401
except (ImportError, OSError):
    _pyudev_stub = types.ModuleType("pyudev")
    _pyudev_stub.Context = unittest.mock.MagicMock()
    _pyudev_stub.Devices = unittest.mock.MagicMock()
    _pyudev_stub.Device = unittest.mock.MagicMock()
    sys.modules["pyudev"] = _pyudev_stub

# --- Bootstrap config BEFORE any arm imports ---
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test")
_TEST_CONFIG = os.path.join(_TEST_DIR, "test_arm.yaml")

_ABCDE_TMP = tempfile.NamedTemporaryFile(
    mode="w", suffix=".conf", prefix="abcde_test_", delete=False
)
_ABCDE_TMP.write("# test abcde config\n")
_ABCDE_TMP.close()

_DB_TMP = tempfile.NamedTemporaryFile(
    suffix=".db", prefix="arm_test_db_", delete=False
)
_DB_TMP.close()
os.unlink(_DB_TMP.name)

with open(_TEST_CONFIG, "r") as f:
    test_cfg = yaml.safe_load(f)
test_cfg["INSTALLPATH"] = _PROJECT_ROOT + "/"
test_cfg["ABCDE_CONFIG_FILE"] = _ABCDE_TMP.name
test_cfg["DBFILE"] = _DB_TMP.name

_PATCHED_CONFIG = tempfile.NamedTemporaryFile(
    mode="w", suffix=".yaml", prefix="arm_test_cfg_", delete=False
)
yaml.dump(test_cfg, _PATCHED_CONFIG)
_PATCHED_CONFIG.close()

os.environ["ARM_CONFIG_FILE"] = _PATCHED_CONFIG.name

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


@pytest.fixture
def tmp_ingress(tmp_path):
    """Create a temporary ingress directory."""
    ingress = tmp_path / "ingress"
    ingress.mkdir()
    return ingress


@pytest.fixture
def bdmv_folder(tmp_ingress):
    """Create a minimal BDMV folder structure."""
    movie = tmp_ingress / "Test Movie 2024"
    bdmv = movie / "BDMV"
    (bdmv / "STREAM").mkdir(parents=True)
    (bdmv / "META" / "DL").mkdir(parents=True)
    (bdmv / "CLIPINF").mkdir(parents=True)
    (bdmv / "PLAYLIST").mkdir(parents=True)
    stream = bdmv / "STREAM" / "00000.m2ts"
    stream.write_bytes(b"\x00" * 1024)
    xml_path = bdmv / "META" / "DL" / "bdmt_eng.xml"
    xml_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<disclib><di:discinfo xmlns:di="urn:BDA:bdmv;discinfo">'
        '<di:title><di:name>TEST MOVIE</di:name></di:title>'
        '</di:discinfo></disclib>'
    )
    cert = movie / "CERTIFICATE"
    cert.mkdir()
    return movie


@pytest.fixture
def bdmv_uhd_folder(bdmv_folder):
    """Extend BDMV folder with UHD indicator."""
    (bdmv_folder / "CERTIFICATE" / "id.bdmv").write_bytes(b"\x00" * 16)
    return bdmv_folder


@pytest.fixture
def dvd_folder(tmp_ingress):
    """Create a minimal VIDEO_TS folder structure."""
    movie = tmp_ingress / "DVD Movie 2020"
    vts = movie / "VIDEO_TS"
    vts.mkdir(parents=True)
    (vts / "VIDEO_TS.IFO").write_bytes(b"\x00" * 512)
    (vts / "VTS_01_1.VOB").write_bytes(b"\x00" * 1024)
    return movie


@pytest.fixture
def mock_config(tmp_ingress, tmp_path):
    """Mock ARM config with INGRESS_PATH set."""
    return {
        'INGRESS_PATH': str(tmp_ingress),
        'RAW_PATH': str(tmp_path / "raw"),
        'COMPLETED_PATH': str(tmp_path / "completed"),
        'TRANSCODE_PATH': str(tmp_path / "transcode"),
        'MINLENGTH': '600',
        'MAXLENGTH': '99999',
        'RIPMETHOD': 'mkv',
        'MAINFEATURE': False,
        'MKV_ARGS': '',
        'INSTALLPATH': '/opt/arm/',
        'VIDEOTYPE': 'auto',
        'TRANSCODER_URL': '',
        'TRANSCODER_WEBHOOK_SECRET': '',
        'LOCAL_RAW_PATH': '',
        'SHARED_RAW_PATH': '',
    }
