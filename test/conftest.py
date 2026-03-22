"""
Test configuration — must be loaded before any ARM imports.

Sets up ARM_CONFIG_FILE env var, creates temporary ABCDE config,
patches INSTALLPATH so config.py can find setup/arm.yaml,
and stubs hardware-dependent modules (discid, pyudev) that fail
without physical devices or system libraries.
"""
import os
import sys
import tempfile
import types
import unittest.mock

import pytest
import yaml
from sqlalchemy.pool import StaticPool

# --- Stub hardware-dependent modules BEFORE any arm imports ---
# discid requires libdiscid.so.0 (C library) — stub it for CI/test
if "discid" not in sys.modules:
    _discid_stub = types.ModuleType("discid")
    _discid_stub.read = unittest.mock.MagicMock()
    _discid_stub.put = unittest.mock.MagicMock()
    _discid_stub.Disc = unittest.mock.MagicMock()
    _discid_stub.DiscError = type("DiscError", (Exception,), {})
    sys.modules["discid"] = _discid_stub
    sys.modules["discid.disc"] = _discid_stub
    sys.modules["discid.libdiscid"] = _discid_stub

# pyudev requires udev on the system — stub if not available
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
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_TEST_CONFIG = os.path.join(_TEST_DIR, "test_arm.yaml")

# Create a minimal abcde.conf for config.py
_ABCDE_TMP = tempfile.NamedTemporaryFile(
    mode="w", suffix=".conf", prefix="abcde_test_", delete=False
)
_ABCDE_TMP.write("# test abcde config\n")
_ABCDE_TMP.close()

# Create a temp DB file path (real file, not :memory:) for startup checks.
# ARM's startup calls check_db_version() with os.path.isfile().
_DB_TMP = tempfile.NamedTemporaryFile(
    suffix=".db", prefix="arm_test_db_", delete=False
)
_DB_TMP.close()
os.unlink(_DB_TMP.name)  # Remove so check_db_version() creates it via migrations

# Patch the test config with real paths
with open(_TEST_CONFIG, "r") as f:
    test_cfg = yaml.safe_load(f)
test_cfg["INSTALLPATH"] = _PROJECT_ROOT + "/"
test_cfg["ABCDE_CONFIG_FILE"] = _ABCDE_TMP.name
test_cfg["DBFILE"] = _DB_TMP.name

# Write a patched copy to a temp file (so we don't modify the committed yaml)
_PATCHED_CONFIG = tempfile.NamedTemporaryFile(
    mode="w", suffix=".yaml", prefix="arm_test_cfg_", delete=False
)
yaml.dump(test_cfg, _PATCHED_CONFIG)
_PATCHED_CONFIG.close()

# Set env var BEFORE importing arm.config.config
os.environ["ARM_CONFIG_FILE"] = _PATCHED_CONFIG.name

# Ensure project root is on PYTHONPATH
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


@pytest.fixture
def app_context():
    """Create standalone SQLAlchemy engine with in-memory test database."""
    from arm.database import db

    db.dispose()  # reset any prior engine (idempotent init_engine)
    db.init_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.create_all()
    yield None, db
    db.dispose()


@pytest.fixture
def sample_job(app_context):
    """Create a Job with realistic test data (no udev/hardware)."""
    from arm.database import db
    from arm.models.job import Job
    from arm.models.config import Config

    _, _ = app_context

    # Mock hardware-dependent methods, then create via normal constructor
    # so SQLAlchemy's instance state is properly initialized.
    with unittest.mock.patch.object(Job, 'parse_udev'), \
         unittest.mock.patch.object(Job, 'get_pid'):
        job = Job('/dev/sr0')

    # Override auto-detected attributes with test data
    job.arm_version = "test"
    job.crc_id = ""
    job.logfile = "test.log"
    job.start_time = None
    job.stop_time = None
    job.job_length = ""
    job.status = "active"
    job.stage = "170750493000"
    job.no_of_titles = 3
    job.title = "SERIAL_MOM"
    job.title_auto = "SERIAL_MOM"
    job.title_manual = None
    job.year = "1994"
    job.year_auto = "1994"
    job.year_manual = None
    job.video_type = "movie"
    job.video_type_auto = "movie"
    job.video_type_manual = None
    job.imdb_id = ""
    job.imdb_id_auto = ""
    job.imdb_id_manual = None
    job.poster_url = ""
    job.poster_url_auto = ""
    job.poster_url_manual = None
    job.devpath = "/dev/sr0"
    job.mountpoint = "/mnt/dev/sr0"
    job.hasnicetitle = True
    job.errors = None
    job.disctype = "bluray"
    job.label = "SERIAL_MOM"
    job.path = None
    job.raw_path = None
    job.transcode_path = None
    job.ejected = False
    job.updated = False
    job.pid = os.getpid()
    job.pid_hash = 0
    job.is_iso = False

    db.session.add(job)
    db.session.flush()  # assigns job_id

    # Config.__init__ takes (dict, job_id) — no hardware deps
    config = Config({
        'RAW_PATH': '/home/arm/media/raw',
        'TRANSCODE_PATH': '/home/arm/media/transcode',
        'COMPLETED_PATH': '/home/arm/media/completed',
        'LOGPATH': '/tmp/arm_test/logs',
        'EXTRAS_SUB': 'extras',
        'MINLENGTH': '600',
        'MAXLENGTH': '99999',
        'MAINFEATURE': False,
        'RIPMETHOD': 'mkv',
        'NOTIFY_RIP': True,
        'NOTIFY_TRANSCODE': True,
        'WEBSERVER_PORT': 8080,
    }, job.job_id)

    db.session.add(config)
    db.session.commit()

    # Refresh to get relationships loaded
    db.session.refresh(job)
    return job


@pytest.fixture
def tmp_media_dirs(tmp_path):
    """Create temporary raw/transcode/completed directories."""
    dirs = {
        "raw": tmp_path / "raw",
        "transcode": tmp_path / "transcode",
        "completed": tmp_path / "completed",
    }
    for d in dirs.values():
        d.mkdir()
    return dirs


# --- Folder import fixtures ---

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


# --- Maintenance fixtures ---

@pytest.fixture
def tmp_logs(tmp_path):
    """Create a temporary log directory with test log files."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "orphan1.log").write_text("log content")
    (log_dir / "orphan2.log").write_text("log content")
    (log_dir / "referenced.log").write_text("log content")
    (log_dir / "not-a-log.txt").write_text("ignored")
    return log_dir


@pytest.fixture
def tmp_media(tmp_path):
    """Create temporary raw and completed directories with test folders."""
    raw = tmp_path / "raw"
    completed = tmp_path / "completed" / "movies"
    raw.mkdir()
    completed.mkdir(parents=True)
    (raw / "Orphan Movie").mkdir()
    (raw / "Orphan Movie" / "title.mkv").write_bytes(b"\x00" * 1024)
    (raw / "SERIAL_MOM").mkdir()  # matches sample_job.title
    (completed / "Another Orphan").mkdir()
    return {"raw": str(raw), "completed": str(tmp_path / "completed")}
