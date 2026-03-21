"""Shared fixtures for folder import tests."""
import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch


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
