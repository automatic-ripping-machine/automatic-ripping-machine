# Folder Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable users to import Blu-ray (BDMV) and DVD (VIDEO_TS) folders into the ARM pipeline via a three-step UI wizard, sharing the existing MakeMKV → metadata → transcode flow.

**Architecture:** New `source_type` field on Job model (`disc` | `folder`). Folder jobs bypass udev/drive logic and use MakeMKV's `file:` source prefix. A new `folder_ripper.py` module orchestrates the pipeline. A new API router (`folder.py`) exposes scan and create endpoints. The SvelteKit UI adds a three-step import wizard modal on the dashboard.

**Tech Stack:** Python 3 / FastAPI / SQLAlchemy / Alembic (backend), SvelteKit 5 / TypeScript / Tailwind (frontend), MakeMKV CLI (`file:` source mode)

**Spec:** `docs/superpowers/specs/2026-03-21-folder-import-design.md`

---

## File Map

### Backend (automatic-ripping-machine-neu)

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `arm/models/job.py` | Add `source_type`, `source_path` columns; `from_folder()` classmethod; `makemkv_source` property |
| Create | `arm/migrations/versions/j4k5l6m7n8o9_job_add_folder_import.py` | Alembic migration for new columns + nullable devpath |
| Modify | `setup/arm.yaml` | Add `INGRESS_PATH` config key |
| Modify | `arm/services/file_browser.py:36-46` | Add `ingress` to allowed roots mapping |
| Create | `arm/ripper/folder_ripper.py` | Folder import pipeline orchestration |
| Create | `arm/ripper/folder_scan.py` | Folder structure detection and metadata extraction |
| Modify | `arm/ripper/makemkv.py:741,918,1028,1082` | Replace `dev:{job.devpath}` with `job.makemkv_source`; guard `prescan_resolve_mdisc` for folder jobs |
| Create | `arm/api/v1/folder.py` | New API router with scan and create endpoints |
| Modify | `arm/app.py:32-42` | Include folder router |

### Frontend (automatic-ripping-machine-ui)

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `frontend/src/lib/api/folder.ts` | API client for scan and create folder job |
| Create | `frontend/src/lib/components/FolderImportWizard.svelte` | Three-step modal wizard |
| Create | `frontend/src/lib/components/FolderBrowser.svelte` | Directory picker scoped to ingress root |
| Modify | `frontend/src/routes/+page.svelte` | Add "Import Folder" button to dashboard |
| Modify | `frontend/src/lib/types/arm.ts` | Add `source_type`, `source_path` to Job interface; add FolderScanResult type |

### Tests (automatic-ripping-machine-neu)

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `tests/test_folder_scan.py` | Folder detection, metadata extraction, path validation |
| Create | `tests/test_folder_ripper.py` | MakeMKV command construction, pipeline orchestration |
| Create | `tests/test_folder_api.py` | API endpoint validation, error responses |
| Create | `tests/conftest.py` | Shared test fixtures (mock DB, mock filesystem, mock config) |

---

## Task 1: Test Infrastructure & Fixtures

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create test directory and conftest**

```bash
mkdir -p tests
```

```python
# tests/__init__.py
# (empty)
```

```python
# tests/conftest.py
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

    # Create a fake m2ts stream file
    stream = bdmv / "STREAM" / "00000.m2ts"
    stream.write_bytes(b"\x00" * 1024)

    # Create bdmt_eng.xml with title
    xml_path = bdmv / "META" / "DL" / "bdmt_eng.xml"
    xml_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<disclib><di:discinfo xmlns:di="urn:BDA:bdmv;discinfo">'
        '<di:title><di:name>TEST MOVIE</di:name></di:title>'
        '</di:discinfo></disclib>'
    )

    # Create CERTIFICATE for non-UHD detection
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
```

- [ ] **Step 2: Verify test infrastructure**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest tests/ --collect-only 2>&1 | head -20`
Expected: No collection errors (may show "no tests ran" which is fine)

- [ ] **Step 3: Commit**

```bash
git add tests/__init__.py tests/conftest.py
git commit -m "test: add test infrastructure and fixtures for folder import"
```

---

## Task 2: Folder Scan Module

**Files:**
- Create: `arm/ripper/folder_scan.py`
- Create: `tests/test_folder_scan.py`

- [ ] **Step 1: Write failing tests for folder scanning**

```python
# tests/test_folder_scan.py
"""Tests for folder structure detection and metadata extraction."""
import os
import pytest
from unittest.mock import patch


class TestDetectDiscType:
    """Test disc type detection from folder structure."""

    def test_bdmv_detected_as_bluray(self, bdmv_folder):
        from arm.ripper.folder_scan import detect_disc_type
        result = detect_disc_type(str(bdmv_folder))
        assert result == "bluray"

    def test_bdmv_uhd_detected_as_bluray4k(self, bdmv_uhd_folder):
        from arm.ripper.folder_scan import detect_disc_type
        result = detect_disc_type(str(bdmv_uhd_folder))
        assert result == "bluray4k"

    def test_dvd_detected(self, dvd_folder):
        from arm.ripper.folder_scan import detect_disc_type
        result = detect_disc_type(str(dvd_folder))
        assert result == "dvd"

    def test_unknown_folder_raises(self, tmp_ingress):
        from arm.ripper.folder_scan import detect_disc_type
        empty = tmp_ingress / "empty"
        empty.mkdir()
        with pytest.raises(ValueError, match="No disc structure"):
            detect_disc_type(str(empty))

    def test_nonexistent_path_raises(self):
        from arm.ripper.folder_scan import detect_disc_type
        with pytest.raises(FileNotFoundError):
            detect_disc_type("/nonexistent/path")


class TestExtractMetadata:
    """Test metadata extraction from disc folders."""

    def test_bluray_title_from_xml(self, bdmv_folder):
        from arm.ripper.folder_scan import extract_metadata
        meta = extract_metadata(str(bdmv_folder), "bluray")
        assert meta["label"] == "TEST MOVIE"

    def test_bluray_missing_xml_returns_folder_name(self, bdmv_folder):
        from arm.ripper.folder_scan import extract_metadata
        os.remove(os.path.join(str(bdmv_folder), "BDMV", "META", "DL", "bdmt_eng.xml"))
        meta = extract_metadata(str(bdmv_folder), "bluray")
        assert meta["label"] == "Test Movie 2024"

    def test_dvd_uses_folder_name(self, dvd_folder):
        from arm.ripper.folder_scan import extract_metadata
        meta = extract_metadata(str(dvd_folder), "dvd")
        assert meta["label"] == "DVD Movie 2020"

    def test_stream_count_counted(self, bdmv_folder):
        from arm.ripper.folder_scan import extract_metadata
        meta = extract_metadata(str(bdmv_folder), "bluray")
        assert meta["stream_count"] == 1

    def test_folder_size_calculated(self, bdmv_folder):
        from arm.ripper.folder_scan import extract_metadata
        meta = extract_metadata(str(bdmv_folder), "bluray")
        assert meta["folder_size_bytes"] > 0


class TestValidateIngressPath:
    """Test path validation for security."""

    def test_valid_path_passes(self, tmp_ingress, bdmv_folder):
        from arm.ripper.folder_scan import validate_ingress_path
        # Should not raise
        validate_ingress_path(str(bdmv_folder), str(tmp_ingress))

    def test_traversal_blocked(self, tmp_ingress):
        from arm.ripper.folder_scan import validate_ingress_path
        with pytest.raises(ValueError, match="outside"):
            validate_ingress_path("/etc/passwd", str(tmp_ingress))

    def test_symlink_traversal_blocked(self, tmp_ingress, tmp_path):
        from arm.ripper.folder_scan import validate_ingress_path
        outside = tmp_path / "outside"
        outside.mkdir()
        link = tmp_ingress / "sneaky_link"
        link.symlink_to(outside)
        with pytest.raises(ValueError, match="outside"):
            validate_ingress_path(str(link), str(tmp_ingress))


class TestScanFolder:
    """Test the top-level scan_folder function."""

    def test_scan_bluray_folder(self, bdmv_folder, tmp_ingress):
        from arm.ripper.folder_scan import scan_folder
        result = scan_folder(str(bdmv_folder), str(tmp_ingress))
        assert result["disc_type"] == "bluray"
        assert result["label"] == "TEST MOVIE"
        assert "title_suggestion" in result
        assert "folder_size_bytes" in result
        assert "stream_count" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest tests/test_folder_scan.py -v 2>&1 | tail -20`
Expected: FAIL — `ModuleNotFoundError: No module named 'arm.ripper.folder_scan'`

- [ ] **Step 3: Implement folder_scan.py**

```python
# arm/ripper/folder_scan.py
"""Folder structure detection and metadata extraction for folder imports.

Detects BDMV (Blu-ray) and VIDEO_TS (DVD) folder structures, extracts
metadata from disc files, and validates paths against the ingress root.
"""
import logging
import os
import re

import xmltodict

logger = logging.getLogger(__name__)


def validate_ingress_path(path: str, ingress_root: str) -> None:
    """Validate that path is under ingress_root after resolving symlinks.

    Raises:
        ValueError: If path is outside ingress_root.
        FileNotFoundError: If path does not exist.
    """
    real_path = os.path.realpath(path)
    real_root = os.path.realpath(ingress_root)
    if not real_path.startswith(real_root + os.sep) and real_path != real_root:
        raise ValueError(f"Path {path} resolves outside ingress root")
    if not os.path.exists(real_path):
        raise FileNotFoundError(f"Path does not exist: {path}")


def detect_disc_type(folder_path: str) -> str:
    """Detect disc type from folder structure.

    Returns:
        'bluray4k', 'bluray', or 'dvd'

    Raises:
        FileNotFoundError: If folder_path does not exist.
        ValueError: If no disc structure is detected.
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    bdmv = os.path.join(folder_path, "BDMV")
    video_ts = os.path.join(folder_path, "VIDEO_TS")

    if os.path.isdir(bdmv):
        uhd_marker = os.path.join(folder_path, "CERTIFICATE", "id.bdmv")
        if os.path.isfile(uhd_marker):
            return "bluray4k"
        return "bluray"

    if os.path.isdir(video_ts):
        return "dvd"

    raise ValueError(f"No disc structure (BDMV or VIDEO_TS) found in {folder_path}")


def extract_metadata(folder_path: str, disc_type: str) -> dict:
    """Extract metadata from a disc folder.

    Returns dict with: label, title_suggestion, year_suggestion,
    folder_size_bytes, stream_count.
    """
    label = _extract_label(folder_path, disc_type)
    title_suggestion, year_suggestion = _parse_title_year(label, folder_path)
    folder_size = _calculate_folder_size(folder_path)
    stream_count = _count_streams(folder_path, disc_type)

    return {
        "label": label,
        "title_suggestion": title_suggestion,
        "year_suggestion": year_suggestion,
        "folder_size_bytes": folder_size,
        "stream_count": stream_count,
    }


def scan_folder(folder_path: str, ingress_root: str) -> dict:
    """Top-level scan: validate, detect type, extract metadata.

    Returns dict with: disc_type, label, title_suggestion, year_suggestion,
    folder_size_bytes, stream_count.
    """
    validate_ingress_path(folder_path, ingress_root)
    disc_type = detect_disc_type(folder_path)
    metadata = extract_metadata(folder_path, disc_type)
    return {"disc_type": disc_type, **metadata}


def _extract_label(folder_path: str, disc_type: str) -> str:
    """Extract disc label from metadata files or folder name."""
    if disc_type in ("bluray", "bluray4k"):
        xml_label = _label_from_bluray_xml(folder_path)
        if xml_label:
            return xml_label
    return os.path.basename(folder_path)


def _label_from_bluray_xml(folder_path: str) -> str | None:
    """Read Blu-ray title from bdmt_eng.xml."""
    xml_path = os.path.join(folder_path, "BDMV", "META", "DL", "bdmt_eng.xml")
    if not os.path.isfile(xml_path):
        return None
    try:
        with open(xml_path, "r", encoding="utf-8") as f:
            doc = xmltodict.parse(f.read())
        title = doc["disclib"]["di:discinfo"]["di:title"]["di:name"]
        return str(title).strip()
    except Exception:
        logger.warning("Failed to parse bdmt_eng.xml at %s", xml_path, exc_info=True)
        return None


def _parse_title_year(label: str, folder_path: str) -> tuple[str, str | None]:
    """Attempt to extract title and year from label or folder name."""
    # Try "Title (Year)" pattern
    folder_name = os.path.basename(folder_path)
    match = re.search(r"^(.+?)\s*\((\d{4})\)", folder_name)
    if match:
        return match.group(1).strip(), match.group(2)

    # Try "Title Year" pattern
    match = re.search(r"^(.+?)\s+(\d{4})\b", folder_name)
    if match:
        return match.group(1).strip(), match.group(2)

    # Clean up the label as title, no year
    clean = re.sub(r"[_.]", " ", label).strip()
    return clean, None


def _calculate_folder_size(folder_path: str) -> int:
    """Calculate total size of all files in folder tree."""
    total = 0
    for dirpath, _, filenames in os.walk(folder_path):
        for f in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total


def _count_streams(folder_path: str, disc_type: str) -> int:
    """Count stream files in the disc structure."""
    if disc_type in ("bluray", "bluray4k"):
        stream_dir = os.path.join(folder_path, "BDMV", "STREAM")
    elif disc_type == "dvd":
        stream_dir = os.path.join(folder_path, "VIDEO_TS")
    else:
        return 0

    if not os.path.isdir(stream_dir):
        return 0

    return len([f for f in os.listdir(stream_dir) if os.path.isfile(os.path.join(stream_dir, f))])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest tests/test_folder_scan.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add arm/ripper/folder_scan.py tests/test_folder_scan.py
git commit -m "feat: add folder scan module for disc type detection and metadata extraction"
```

---

## Task 3: Job Model Changes

**Files:**
- Modify: `arm/models/job.py:90-182`
- Create: `arm/migrations/versions/j4k5l6m7n8o9_job_add_folder_import.py`
- Modify: `setup/arm.yaml:169-216`

- [ ] **Step 1: Add source_type and source_path columns to Job model**

In `arm/models/job.py`, after line 158 (`is_iso = db.Column(db.Boolean)`), add:

```python
    source_type = db.Column(db.String(16), default="disc", nullable=False, server_default="disc")
    source_path = db.Column(db.String(1024), nullable=True)
```

- [ ] **Step 2: Add makemkv_source property to Job model**

In `arm/models/job.py`, after the `ripping_finished` property (after line 370), add:

```python
    @property
    def makemkv_source(self) -> str:
        """Return the MakeMKV source string for this job."""
        if self.source_type == "folder":
            return f"file:{self.source_path}"
        return f"dev:{self.devpath}"

    @property
    def is_folder_import(self) -> bool:
        """Return True if this job was created from a folder import."""
        return self.source_type == "folder"
```

- [ ] **Step 3: Add from_folder classmethod**

In `arm/models/job.py`, after the `__init__` method (after line 182), add:

```python
    @classmethod
    def from_folder(cls, source_path: str, disctype: str):
        """Create a Job from a folder path, bypassing udev/drive detection.

        Parameters:
            source_path: Absolute path to BDMV or VIDEO_TS folder.
            disctype: One of 'bluray', 'bluray4k', 'dvd'.
        """
        job = cls.__new__(cls)
        # Initialize SQLAlchemy instance state
        db.Model.__init__(job)
        # Set folder-specific fields
        job.source_type = "folder"
        job.source_path = source_path
        job.devpath = None
        job.disctype = disctype
        job.start_time = dt.now()
        # Set defaults matching __init__
        job.mountpoint = ""
        job.hasnicetitle = False
        job.video_type = "unknown"
        job.ejected = False
        job.updated = False
        job.stage = ""
        job.manual_start = False
        job.manual_pause = False
        job.manual_mode = False
        job.has_track_99 = False
        job.is_iso = False
        if cfg.arm_config.get('VIDEOTYPE', 'auto') != "auto":
            job.video_type = cfg.arm_config['VIDEOTYPE']
        return job
```

- [ ] **Step 4: Create Alembic migration**

```python
# arm/migrations/versions/j4k5l6m7n8o9_job_add_folder_import.py
"""Add source_type and source_path columns for folder import support.

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa

revision = 'j4k5l6m7n8o9'
down_revision = 'i3j4k5l6m7n8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('job') as batch_op:
        batch_op.add_column(
            sa.Column('source_type', sa.String(16), nullable=False, server_default='disc')
        )
        batch_op.add_column(
            sa.Column('source_path', sa.String(1024), nullable=True)
        )
        batch_op.alter_column('devpath', existing_type=sa.String(15), nullable=True)


def downgrade():
    with op.batch_alter_table('job') as batch_op:
        batch_op.alter_column('devpath', existing_type=sa.String(15), nullable=False)
        batch_op.drop_column('source_path')
        batch_op.drop_column('source_type')
```

- [ ] **Step 5: Add INGRESS_PATH to setup/arm.yaml**

In `setup/arm.yaml`, after the `MUSIC_PATH` entry (around line 187), add:

```yaml
# ---- Folder Import ----
# Root path for folder imports. The UI file browser is scoped to this path.
# Point this at a directory containing BDMV/VIDEO_TS folders from disc backups.
INGRESS_PATH: ""
```

- [ ] **Step 6: Add ingress to file browser roots**

In `arm/services/file_browser.py`, modify the mapping dict at line 36 to add the ingress root:

```python
    mapping = {
        'raw': 'RAW_PATH',
        'completed': 'COMPLETED_PATH',
        'transcode': 'TRANSCODE_PATH',
        'music': 'MUSIC_PATH',
        'ingress': 'INGRESS_PATH',
    }
```

- [ ] **Step 7: Commit**

```bash
git add arm/models/job.py arm/migrations/versions/j4k5l6m7n8o9_job_add_folder_import.py setup/arm.yaml arm/services/file_browser.py
git commit -m "feat: add folder import fields to Job model with migration and config"
```

---

## Task 4: MakeMKV Source Refactor

**Files:**
- Modify: `arm/ripper/makemkv.py:741,1028,1082`

- [ ] **Step 1: Replace hardcoded dev: in rip_mainfeature**

In `arm/ripper/makemkv.py` at line 1028, change:
```python
        f"dev:{job.devpath}",
```
to:
```python
        job.makemkv_source,
```

- [ ] **Step 2: Replace hardcoded dev: in process_single_tracks**

In `arm/ripper/makemkv.py` at line 1082, change:
```python
                f"dev:{job.devpath}",
```
to:
```python
                job.makemkv_source,
```

- [ ] **Step 3: Replace hardcoded dev: in makemkv_mkv all-tracks path**

In `arm/ripper/makemkv.py` at line 741, change:
```python
            f"dev:{job.devpath}",
```
to:
```python
            job.makemkv_source,
```

- [ ] **Step 4: Replace hardcoded dev: in prescan_disc_info**

In `arm/ripper/makemkv.py` at line 918, change:
```python
           "info", "--cache=1", f"dev:{job.devpath}", "--minlength=0"]
```
to:
```python
           "info", "--cache=1", job.makemkv_source, "--minlength=0"]
```

- [ ] **Step 5: Guard prescan_resolve_mdisc for folder jobs**

In `arm/ripper/makemkv.py` at line 937-941, change:
```python
    # Resolve disc index for later rip phase (best-effort, non-critical)
    try:
        prescan_resolve_mdisc(job, timeout=60)
    except Exception as exc:
        logging.warning("mdisc resolution failed (non-fatal): %s", exc)
```
to:
```python
    # Resolve disc index for later rip phase (best-effort, non-critical)
    # Skip for folder imports — no physical drive to resolve
    if not getattr(job, 'is_folder_import', False):
        try:
            prescan_resolve_mdisc(job, timeout=60)
        except Exception as exc:
            logging.warning("mdisc resolution failed (non-fatal): %s", exc)
```

- [ ] **Step 6: Verify no hardcoded dev: remains**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && grep -n 'dev:{job.devpath}' arm/ripper/makemkv.py`
Expected: No matches found.

- [ ] **Step 7: Commit**

```bash
git add arm/ripper/makemkv.py
git commit -m "refactor: use job.makemkv_source instead of hardcoded dev: prefix"
```

---

## Task 5: Folder Ripper Module

**Files:**
- Create: `arm/ripper/folder_ripper.py`
- Create: `tests/test_folder_ripper.py`

- [ ] **Step 1: Write failing tests for folder ripper**

```python
# tests/test_folder_ripper.py
"""Tests for folder import pipeline orchestration."""
import os
import pytest
from unittest.mock import patch, MagicMock, call


class TestRipFolder:
    """Test the rip_folder pipeline function."""

    @patch("arm.ripper.utils.transcoder_notify")
    @patch("arm.ripper.makemkv._reconcile_filenames")
    @patch("arm.ripper.makemkv.process_single_tracks")
    @patch("arm.ripper.makemkv.prescan_track_info")
    @patch("arm.ripper.makemkv.prep_mkv")
    @patch("arm.ripper.makemkv.setup_rawpath")
    @patch("arm.ripper.folder_ripper.db")
    def test_rip_folder_success_calls_pipeline(
        self, mock_db, mock_setup, mock_prep, mock_prescan,
        mock_process, mock_reconcile, mock_notify, tmp_path, bdmv_folder
    ):
        from arm.ripper.folder_ripper import rip_folder

        mock_job = MagicMock()
        mock_job.source_path = str(bdmv_folder)
        mock_job.source_type = "folder"
        mock_job.config.RAW_PATH = str(tmp_path / "raw")
        mock_job.config.RIPMETHOD = "mkv"
        mock_job.config.MAINFEATURE = False
        mock_job.config.TRANSCODER_URL = ""
        mock_job.build_raw_path.return_value = str(tmp_path / "raw" / "Test Movie")
        mock_setup.return_value = str(tmp_path / "raw" / "Test Movie")

        rip_folder(mock_job)

        mock_prep.assert_called_once()
        mock_setup.assert_called_once()
        mock_prescan.assert_called_once_with(mock_job)
        mock_process.assert_called_once()

    @patch("arm.ripper.folder_ripper.db")
    def test_rip_folder_missing_source_fails(self, mock_db):
        from arm.ripper.folder_ripper import rip_folder

        mock_job = MagicMock()
        mock_job.source_path = "/nonexistent/folder"
        mock_job.source_type = "folder"

        with pytest.raises(FileNotFoundError):
            rip_folder(mock_job)

    @patch("arm.ripper.folder_ripper.db")
    def test_rip_folder_invalid_structure_fails(self, mock_db, tmp_ingress):
        from arm.ripper.folder_ripper import rip_folder

        empty = tmp_ingress / "empty"
        empty.mkdir()

        mock_job = MagicMock()
        mock_job.source_path = str(empty)
        mock_job.source_type = "folder"

        with pytest.raises(ValueError):
            rip_folder(mock_job)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest tests/test_folder_ripper.py -v 2>&1 | tail -10`
Expected: FAIL — `ModuleNotFoundError: No module named 'arm.ripper.folder_ripper'`

- [ ] **Step 3: Implement folder_ripper.py**

```python
# arm/ripper/folder_ripper.py
"""Folder import pipeline orchestration.

Parallel entry point to arm_ripper.rip_visual_media() for folder-based
jobs. Bypasses udev, drive readiness, disc resolution, and eject steps.
Uses MakeMKV's file: source prefix instead of dev:.
"""
import logging
import os

from arm.models import job as job_module
from arm.models.job import JobState
from arm.ripper import makemkv, utils
from arm.ripper.folder_scan import detect_disc_type
from arm.ripper.makemkv import (
    prep_mkv,
    setup_rawpath,
    prescan_track_info,
    process_single_tracks,
    rip_mainfeature,
    _reconcile_filenames,
)
from arm.database import db

logger = logging.getLogger(__name__)


def rip_folder(job):
    """Run the folder import pipeline for a folder-based job.

    Steps:
        1. Validate source folder
        2. Prep MakeMKV (license/keys)
        3. Setup raw output path
        4. Pre-scan for track info
        5. Rip tracks via MakeMKV (file: source)
        6. Reconcile filenames
        7. Notify transcoder
        8. Update job status

    Raises:
        FileNotFoundError: If source folder does not exist.
        ValueError: If source folder has no valid disc structure.
    """
    source = job.source_path

    # 1. Validate source
    if not os.path.isdir(source):
        job.status = JobState.FAILURE
        job.errors = f"Source folder not found: {source}"
        db.session.commit()
        raise FileNotFoundError(f"Source folder not found: {source}")

    disc_type = detect_disc_type(source)
    logger.info("Folder import: %s detected as %s", source, disc_type)

    try:
        # 2. Prep MakeMKV
        job.status = JobState.VIDEO_RIPPING
        job.stage = "Preparing MakeMKV"
        db.session.commit()
        prep_mkv()

        # 3. Setup raw output path
        rawpath = setup_rawpath(job, job.build_raw_path())
        job.raw_path = rawpath
        db.session.commit()
        logger.info("Raw output path: %s", rawpath)

        # 4. Pre-scan for track info
        job.stage = "Scanning tracks"
        db.session.commit()
        prescan_track_info(job)

        # 5. Rip tracks
        job.stage = "Ripping"
        db.session.commit()

        if job.config.MAINFEATURE and job.tracks.count() > 0:
            main_track = max(job.tracks, key=lambda t: int(t.length or 0))
            rip_mainfeature(job, main_track, rawpath)
        else:
            process_single_tracks(job, rawpath, "auto")

        # 6. Reconcile filenames
        _reconcile_filenames(job, rawpath)

        # 7. Notify transcoder
        job.stage = "Notifying transcoder"
        db.session.commit()
        transcoder_cfg = {
            k: job.config.__dict__.get(k, '') or getattr(job.config, k, '')
            for k in ('TRANSCODER_URL', 'TRANSCODER_WEBHOOK_SECRET',
                      'LOCAL_RAW_PATH', 'SHARED_RAW_PATH')
        }
        if transcoder_cfg.get('TRANSCODER_URL'):
            utils.transcoder_notify(
                transcoder_cfg,
                f"Folder import complete: {job.title or os.path.basename(source)}",
                "Rip complete",
                job=job,
            )

        # 8. Success
        job.status = JobState.TRANSCODE_WAITING
        job.stage = ""
        db.session.commit()
        logger.info("Folder import complete for job %s: %s", job.job_id, rawpath)

    except Exception as e:
        logger.error("Folder import failed for job %s: %s", job.job_id, e, exc_info=True)
        job.status = JobState.FAILURE
        job.errors = str(e)
        job.stage = ""
        db.session.commit()
        raise
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest tests/test_folder_ripper.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add arm/ripper/folder_ripper.py tests/test_folder_ripper.py
git commit -m "feat: add folder ripper module for folder import pipeline"
```

---

## Task 6: Folder API Router

**Files:**
- Create: `arm/api/v1/folder.py`
- Modify: `arm/app.py:32-42`
- Create: `tests/test_folder_api.py`

- [ ] **Step 1: Write failing tests for folder API**

```python
# tests/test_folder_api.py
"""Tests for folder import API endpoints."""
import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(mock_config):
    """Create a test client with mocked config."""
    with patch("arm.config.config.arm_config", mock_config):
        from arm.app import app
        client = TestClient(app)
        yield client


class TestFolderScan:
    """Test POST /api/v1/jobs/folder/scan endpoint."""

    @patch("arm.api.v1.folder.scan_folder")
    @patch("arm.config.config.arm_config", {"INGRESS_PATH": "/tmp/ingress"})
    def test_scan_valid_folder(self, mock_scan, app_client):
        mock_scan.return_value = {
            "disc_type": "bluray",
            "label": "TEST",
            "title_suggestion": "Test",
            "year_suggestion": "2024",
            "folder_size_bytes": 1000,
            "stream_count": 5,
        }
        resp = app_client.post("/api/v1/jobs/folder/scan", json={"path": "/tmp/ingress/test"})
        assert resp.status_code == 200
        assert resp.json()["disc_type"] == "bluray"

    @patch("arm.config.config.arm_config", {"INGRESS_PATH": ""})
    def test_scan_no_ingress_configured(self, app_client):
        resp = app_client.post("/api/v1/jobs/folder/scan", json={"path": "/some/path"})
        assert resp.status_code == 400

    @patch("arm.api.v1.folder.scan_folder")
    @patch("arm.config.config.arm_config", {"INGRESS_PATH": "/tmp/ingress"})
    def test_scan_invalid_folder(self, mock_scan, app_client):
        mock_scan.side_effect = ValueError("No disc structure")
        resp = app_client.post("/api/v1/jobs/folder/scan", json={"path": "/tmp/ingress/bad"})
        assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest tests/test_folder_api.py -v 2>&1 | tail -10`
Expected: FAIL — `ModuleNotFoundError: No module named 'arm.api.v1.folder'`

- [ ] **Step 3: Implement folder API router**

```python
# arm/api/v1/folder.py
"""API endpoints for folder-based job imports."""
import logging
import threading

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from arm.config import config as cfg
from arm.models.job import Job, JobState
from arm.ripper.folder_scan import scan_folder, validate_ingress_path
from arm.ripper.folder_ripper import rip_folder
from arm.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["folder"])


class FolderScanRequest(BaseModel):
    path: str


class FolderCreateRequest(BaseModel):
    source_path: str
    title: str
    year: str | None = None
    video_type: str = "movie"
    disctype: str = "bluray"
    imdb_id: str | None = None
    poster_url: str | None = None
    multi_title: bool = False


@router.post("/jobs/folder/scan")
def folder_scan(req: FolderScanRequest):
    """Scan a folder and detect disc type and metadata."""
    ingress = cfg.arm_config.get("INGRESS_PATH", "")
    if not ingress:
        raise HTTPException(400, "INGRESS_PATH is not configured")

    try:
        result = scan_folder(req.path, ingress)
    except FileNotFoundError as e:
        raise HTTPException(400, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))

    return result


@router.post("/jobs/folder", status_code=201)
def folder_create(req: FolderCreateRequest):
    """Create a folder import job and start the rip pipeline."""
    ingress = cfg.arm_config.get("INGRESS_PATH", "")
    if not ingress:
        raise HTTPException(400, "INGRESS_PATH is not configured")

    # Validate path
    try:
        validate_ingress_path(req.source_path, ingress)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(400, str(e))

    # Check for duplicate
    existing = (
        db.session.query(Job)
        .filter(
            Job.source_path == req.source_path,
            Job.status.notin_([JobState.SUCCESS, JobState.FAILURE]),
        )
        .first()
    )
    if existing:
        raise HTTPException(409, f"Active job already exists for this folder (job {existing.job_id})")

    # Create job
    job = Job.from_folder(req.source_path, req.disctype)
    job.title = req.title
    job.title_manual = req.title
    job.year = req.year
    job.year_manual = req.year
    job.video_type = req.video_type
    job.video_type_manual = req.video_type
    job.imdb_id = req.imdb_id
    job.imdb_id_manual = req.imdb_id
    job.poster_url = req.poster_url
    job.poster_url_manual = req.poster_url
    job.multi_title = req.multi_title
    job.status = JobState.VIDEO_RIPPING
    job.stage = "Starting"
    db.session.add(job)
    db.session.commit()

    logger.info("Created folder import job %s for %s", job.job_id, req.source_path)

    # Launch rip in background thread
    def _run_rip():
        try:
            rip_folder(job)
        except Exception:
            logger.error("Folder import job %s failed", job.job_id, exc_info=True)

    thread = threading.Thread(target=_run_rip, daemon=True, name=f"folder-rip-{job.job_id}")
    thread.start()

    return {
        "job_id": job.job_id,
        "status": job.status,
        "source_type": job.source_type,
        "source_path": job.source_path,
    }
```

- [ ] **Step 4: Register router in app.py**

In `arm/app.py`, after the existing imports (around line 32), add:
```python
from arm.api.v1 import folder
```

And after the existing `app.include_router()` calls (around line 42), add:
```python
app.include_router(folder.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest tests/test_folder_api.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add arm/api/v1/folder.py arm/app.py tests/test_folder_api.py
git commit -m "feat: add folder import API endpoints (scan and create)"
```

---

## Task 7: Frontend — API Client & Types

**Files:**
- Create: `frontend/src/lib/api/folder.ts`
- Modify: `frontend/src/lib/types/arm.ts`

Working directory: `/home/upb/src/automatic-ripping-machine-ui`

- [ ] **Step 1: Add FolderScanResult type and update Job interface**

In `frontend/src/lib/types/arm.ts`, add at the end of the file:

```typescript
export interface FolderScanResult {
	disc_type: string;
	label: string;
	title_suggestion: string;
	year_suggestion: string | null;
	folder_size_bytes: number;
	stream_count: number;
}

export interface FolderCreateRequest {
	source_path: string;
	title: string;
	year?: string | null;
	video_type: string;
	disctype: string;
	imdb_id?: string | null;
	poster_url?: string | null;
	multi_title?: boolean;
}

export interface FolderCreateResponse {
	job_id: number;
	status: string;
	source_type: string;
	source_path: string;
}
```

Also add `source_type` and `source_path` to the existing `Job` interface (after `is_iso` or similar field):

```typescript
	source_type?: string;
	source_path?: string;
```

- [ ] **Step 2: Create folder API client**

```typescript
// frontend/src/lib/api/folder.ts
import { apiFetch } from './client';
import type { FolderScanResult, FolderCreateRequest, FolderCreateResponse } from '../types/arm';
import type { DirectoryListing, FileRoot } from '../types/files';

export function scanFolder(path: string): Promise<FolderScanResult> {
	return apiFetch('/api/jobs/folder/scan', {
		method: 'POST',
		body: JSON.stringify({ path })
	});
}

export function createFolderJob(data: FolderCreateRequest): Promise<FolderCreateResponse> {
	return apiFetch('/api/jobs/folder', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export function fetchIngressDirectory(path: string): Promise<DirectoryListing> {
	return apiFetch(`/api/files/list?path=${encodeURIComponent(path)}`);
}

export function fetchIngressRoot(): Promise<FileRoot[]> {
	return apiFetch('/api/files/roots');
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-ui
git add frontend/src/lib/api/folder.ts frontend/src/lib/types/arm.ts
git commit -m "feat: add folder import API client and types"
```

---

## Task 8: Frontend — Folder Browser Component

**Files:**
- Create: `frontend/src/lib/components/FolderBrowser.svelte`

Working directory: `/home/upb/src/automatic-ripping-machine-ui`

- [ ] **Step 1: Create FolderBrowser component**

```svelte
<!-- frontend/src/lib/components/FolderBrowser.svelte -->
<script lang="ts">
	import { onMount } from 'svelte';
	import type { DirectoryListing, FileEntry, FileRoot } from '$lib/types/files';
	import { fetchIngressDirectory, fetchIngressRoot } from '$lib/api/folder';
	import FileIcon from './FileIcon.svelte';

	interface Props {
		onselect: (path: string) => void;
	}

	let { onselect }: Props = $props();

	let ingressRoot = $state('');
	let currentPath = $state('');
	let listing = $state<DirectoryListing | null>(null);
	let loading = $state(true);
	let error = $state('');
	let selectedPath = $state('');

	async function init() {
		try {
			loading = true;
			error = '';
			const roots = await fetchIngressRoot();
			const ingress = roots.find((r: FileRoot) => r.key === 'ingress');
			if (!ingress) {
				error = 'Ingress path is not configured. Set INGRESS_PATH in ARM settings.';
				return;
			}
			ingressRoot = ingress.path;
			currentPath = ingress.path;
			await loadDirectory(ingress.path);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load ingress root';
		} finally {
			loading = false;
		}
	}

	async function loadDirectory(path: string) {
		try {
			loading = true;
			error = '';
			listing = await fetchIngressDirectory(path);
			currentPath = path;
			selectedPath = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load directory';
		} finally {
			loading = false;
		}
	}

	function navigateUp() {
		if (listing?.parent && currentPath !== ingressRoot) {
			loadDirectory(listing.parent);
		}
	}

	function selectFolder(entry: FileEntry) {
		if (entry.type !== 'directory') return;
		const fullPath = `${currentPath}/${entry.name}`;
		selectedPath = fullPath;
		onselect(fullPath);
	}

	function openFolder(entry: FileEntry) {
		if (entry.type !== 'directory') return;
		loadDirectory(`${currentPath}/${entry.name}`);
	}

	function isDiscFolder(name: string): boolean {
		return name === 'BDMV' || name === 'VIDEO_TS';
	}

	function formatSize(bytes: number): string {
		if (bytes === 0) return '';
		const units = ['B', 'KB', 'MB', 'GB', 'TB'];
		const i = Math.floor(Math.log(bytes) / Math.log(1024));
		return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
	}

	onMount(() => { init(); });
</script>

<div class="folder-browser">
	{#if error}
		<div class="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
			{error}
		</div>
	{:else if loading && !listing}
		<div class="flex items-center justify-center py-8 text-gray-500 dark:text-gray-400">
			Loading...
		</div>
	{:else if listing}
		<!-- Breadcrumb -->
		<div class="mb-3 flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
			<button
				type="button"
				class="hover:text-primary disabled:opacity-50"
				disabled={currentPath === ingressRoot}
				onclick={navigateUp}
			>
				&larr; Back
			</button>
			<span class="truncate">{currentPath.replace(ingressRoot, '...') || '/'}</span>
		</div>

		<!-- Directory listing -->
		<div class="max-h-80 overflow-y-auto rounded-lg border border-primary/20 dark:border-primary/30">
			<table class="w-full text-sm">
				<tbody>
					{#each listing.entries.filter(e => e.type === 'directory') as entry}
						{@const fullPath = `${currentPath}/${entry.name}`}
						<tr
							class="cursor-pointer border-b border-primary/10 transition-colors last:border-0
								{selectedPath === fullPath ? 'bg-primary/15 dark:bg-primary/20' : 'hover:bg-primary/5 dark:hover:bg-primary/10'}"
							onclick={() => selectFolder(entry)}
							ondblclick={() => openFolder(entry)}
						>
							<td class="w-8 py-2 pl-3">
								<FileIcon type="directory" extension="" category="directory" />
							</td>
							<td class="py-2 pl-2 font-medium text-gray-900 dark:text-white">
								{entry.name}
								{#if isDiscFolder(entry.name)}
									<span class="ml-2 rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
										{entry.name === 'BDMV' ? 'Blu-ray' : 'DVD'}
									</span>
								{/if}
							</td>
							<td class="py-2 pr-3 text-right text-gray-500 dark:text-gray-400">
								{formatSize(entry.size)}
							</td>
						</tr>
					{/each}
					{#if listing.entries.filter(e => e.type === 'directory').length === 0}
						<tr>
							<td colspan="3" class="py-4 text-center text-gray-500 dark:text-gray-400">
								No folders found
							</td>
						</tr>
					{/if}
				</tbody>
			</table>
		</div>

		<p class="mt-2 text-xs text-gray-400 dark:text-gray-500">
			Click to select &middot; Double-click to open
		</p>
	{/if}
</div>
```

- [ ] **Step 2: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-ui
git add frontend/src/lib/components/FolderBrowser.svelte
git commit -m "feat: add FolderBrowser component for ingress directory picking"
```

---

## Task 9: Frontend — Import Wizard Component

**Files:**
- Create: `frontend/src/lib/components/FolderImportWizard.svelte`

Working directory: `/home/upb/src/automatic-ripping-machine-ui`

- [ ] **Step 1: Create the three-step wizard modal**

```svelte
<!-- frontend/src/lib/components/FolderImportWizard.svelte -->
<script lang="ts">
	import type { FolderScanResult } from '$lib/types/arm';
	import type { SearchResult, MediaDetail } from '$lib/types/arm';
	import { scanFolder, createFolderJob } from '$lib/api/folder';
	import { searchMetadata, fetchMediaDetail } from '$lib/api/jobs';
	import FolderBrowser from './FolderBrowser.svelte';

	interface Props {
		open: boolean;
		onclose: () => void;
		oncreated: () => void;
	}

	let { open, onclose, oncreated }: Props = $props();

	// Wizard state
	let step = $state(1);
	let error = $state('');
	let submitting = $state(false);

	// Step 1: folder selection
	let selectedPath = $state('');

	// Step 2: scan + metadata
	let scanResult = $state<FolderScanResult | null>(null);
	let scanning = $state(false);
	let searchResults = $state<SearchResult[]>([]);
	let searching = $state(false);
	let editTitle = $state('');
	let editYear = $state('');
	let editType = $state('movie');
	let editImdbId = $state('');
	let editPosterUrl = $state('');
	let editDiscType = $state('');

	// Step 3: confirm
	let creating = $state(false);

	const inputBase = 'rounded-lg border border-primary/25 bg-primary/5 px-3 py-1.5 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white';

	function reset() {
		step = 1;
		error = '';
		selectedPath = '';
		scanResult = null;
		searchResults = [];
		editTitle = '';
		editYear = '';
		editType = 'movie';
		editImdbId = '';
		editPosterUrl = '';
		editDiscType = '';
		submitting = false;
		scanning = false;
		searching = false;
		creating = false;
	}

	function handleClose() {
		reset();
		onclose();
	}

	function handleFolderSelect(path: string) {
		selectedPath = path;
		error = '';
	}

	async function handleScan() {
		if (!selectedPath) return;
		try {
			scanning = true;
			error = '';
			scanResult = await scanFolder(selectedPath);
			editTitle = scanResult.title_suggestion || '';
			editYear = scanResult.year_suggestion || '';
			editDiscType = scanResult.disc_type;
			editType = 'movie';
			step = 2;

			// Auto-search metadata
			if (editTitle) {
				await handleSearch();
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Scan failed';
		} finally {
			scanning = false;
		}
	}

	async function handleSearch() {
		if (!editTitle) return;
		try {
			searching = true;
			searchResults = await searchMetadata(editTitle, editYear || undefined);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Search failed';
		} finally {
			searching = false;
		}
	}

	async function handleSelectResult(result: SearchResult) {
		editTitle = result.title;
		editYear = result.year;
		editType = result.media_type || 'movie';
		editImdbId = result.imdb_id || '';
		editPosterUrl = result.poster_url || '';

		if (result.imdb_id) {
			try {
				const detail: MediaDetail = await fetchMediaDetail(result.imdb_id);
				if (detail.poster_url) editPosterUrl = detail.poster_url;
			} catch { /* keep what we have */ }
		}
	}

	async function handleCreate() {
		try {
			creating = true;
			error = '';
			await createFolderJob({
				source_path: selectedPath,
				title: editTitle,
				year: editYear || undefined,
				video_type: editType,
				disctype: editDiscType,
				imdb_id: editImdbId || undefined,
				poster_url: editPosterUrl || undefined,
			});
			handleClose();
			oncreated();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to create job';
		} finally {
			creating = false;
		}
	}

	function formatSize(bytes: number): string {
		if (!bytes) return '—';
		const units = ['B', 'KB', 'MB', 'GB', 'TB'];
		const i = Math.floor(Math.log(bytes) / Math.log(1024));
		return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
	}

	function discLabel(dt: string): string {
		const map: Record<string, string> = { bluray: 'Blu-ray', bluray4k: '4K UHD', dvd: 'DVD' };
		return map[dt] || dt;
	}
</script>

{#if open}
	<div class="fixed inset-0 z-50 flex items-center justify-center">
		<!-- Backdrop -->
		<button type="button" class="absolute inset-0 bg-black/50" onclick={handleClose} aria-label="Close"></button>

		<!-- Wizard -->
		<div class="relative z-10 w-full max-w-2xl rounded-lg bg-surface p-6 shadow-xl dark:bg-surface-dark">
			<!-- Header -->
			<div class="mb-4 flex items-center justify-between">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Import Folder</h2>
				<div class="flex gap-2">
					{#each [1, 2, 3] as s}
						<div class="h-2 w-8 rounded-full {s <= step ? 'bg-primary' : 'bg-gray-200 dark:bg-gray-700'}"></div>
					{/each}
				</div>
			</div>

			<!-- Error -->
			{#if error}
				<div class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
					{error}
				</div>
			{/if}

			<!-- Step 1: Pick Folder -->
			{#if step === 1}
				<p class="mb-3 text-sm text-gray-600 dark:text-gray-400">Select a Blu-ray or DVD folder to import.</p>
				<FolderBrowser onselect={handleFolderSelect} />
				<div class="mt-4 flex justify-end gap-3">
					<button type="button" onclick={handleClose}
						class="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700">
						Cancel
					</button>
					<button type="button" onclick={handleScan}
						disabled={!selectedPath || scanning}
						class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:bg-primary/90 disabled:opacity-50">
						{scanning ? 'Scanning...' : 'Next'}
					</button>
				</div>

			<!-- Step 2: Verify & Match -->
			{:else if step === 2}
				{#if scanResult}
					<div class="mb-4 flex items-start gap-4">
						<!-- Poster preview -->
						{#if editPosterUrl}
							<img src={editPosterUrl} alt="Poster" class="h-32 w-auto rounded shadow" />
						{:else}
							<div class="flex h-32 w-20 items-center justify-center rounded bg-gray-100 text-xs text-gray-400 dark:bg-gray-800">
								No poster
							</div>
						{/if}
						<div class="flex-1">
							<div class="mb-2 flex gap-2">
								<span class="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
									{discLabel(scanResult.disc_type)}
								</span>
								<span class="text-xs text-gray-500 dark:text-gray-400">
									{formatSize(scanResult.folder_size_bytes)} &middot; {scanResult.stream_count} streams
								</span>
							</div>
							<p class="text-xs text-gray-500 dark:text-gray-400">Disc label: {scanResult.label}</p>
						</div>
					</div>

					<!-- Editable fields -->
					<div class="grid grid-cols-2 gap-3">
						<div>
							<label class="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Title</label>
							<input type="text" bind:value={editTitle} class="w-full {inputBase}" />
						</div>
						<div>
							<label class="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Year</label>
							<input type="text" bind:value={editYear} class="w-full {inputBase}" />
						</div>
						<div>
							<label class="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Type</label>
							<select bind:value={editType} class="w-full {inputBase}">
								<option value="movie">Movie</option>
								<option value="series">Series</option>
							</select>
						</div>
						<div>
							<label class="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">IMDb ID</label>
							<input type="text" bind:value={editImdbId} placeholder="tt..." class="w-full {inputBase}" />
						</div>
					</div>

					<!-- Search -->
					<div class="mt-3 flex gap-2">
						<button type="button" onclick={handleSearch}
							disabled={searching || !editTitle}
							class="rounded-lg bg-primary/15 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-primary/25 disabled:opacity-50 dark:text-gray-300">
							{searching ? 'Searching...' : 'Search'}
						</button>
					</div>

					<!-- Results -->
					{#if searchResults.length > 0}
						<div class="mt-3 max-h-40 overflow-y-auto rounded-lg border border-primary/15 dark:border-primary/25">
							{#each searchResults as result}
								<button type="button"
									class="flex w-full items-center gap-3 border-b border-primary/10 px-3 py-2 text-left text-sm transition-colors last:border-0 hover:bg-primary/5 dark:hover:bg-primary/10"
									onclick={() => handleSelectResult(result)}>
									{#if result.poster_url}
										<img src={result.poster_url} alt="" class="h-10 w-auto rounded" />
									{/if}
									<div>
										<span class="font-medium text-gray-900 dark:text-white">{result.title}</span>
										<span class="ml-1 text-gray-500">({result.year})</span>
										<span class="ml-2 text-xs text-gray-400">{result.media_type}</span>
									</div>
								</button>
							{/each}
						</div>
					{/if}
				{/if}

				<div class="mt-4 flex justify-between">
					<button type="button" onclick={() => { step = 1; error = ''; }}
						class="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700">
						Back
					</button>
					<button type="button" onclick={() => { step = 3; error = ''; }}
						disabled={!editTitle}
						class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:bg-primary/90 disabled:opacity-50">
						Next
					</button>
				</div>

			<!-- Step 3: Confirm -->
			{:else if step === 3}
				<div class="space-y-3">
					<div class="flex items-start gap-4 rounded-lg border border-primary/20 p-4 dark:border-primary/30">
						{#if editPosterUrl}
							<img src={editPosterUrl} alt="Poster" class="h-24 w-auto rounded shadow" />
						{/if}
						<div class="flex-1">
							<h3 class="font-semibold text-gray-900 dark:text-white">
								{editTitle} {editYear ? `(${editYear})` : ''}
							</h3>
							<div class="mt-1 flex gap-2 text-sm text-gray-500 dark:text-gray-400">
								<span class="capitalize">{editType}</span>
								<span>&middot;</span>
								<span>{discLabel(editDiscType)}</span>
								{#if editImdbId}
									<span>&middot;</span>
									<span>{editImdbId}</span>
								{/if}
							</div>
							<p class="mt-2 text-xs text-gray-400 dark:text-gray-500 break-all">
								Source: {selectedPath}
							</p>
						</div>
					</div>
				</div>

				<div class="mt-4 flex justify-between">
					<button type="button" onclick={() => { step = 2; error = ''; }}
						class="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700">
						Back
					</button>
					<button type="button" onclick={handleCreate}
						disabled={creating}
						class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:bg-primary/90 disabled:opacity-50">
						{creating ? 'Importing...' : 'Import'}
					</button>
				</div>
			{/if}
		</div>
	</div>
{/if}
```

- [ ] **Step 2: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-ui
git add frontend/src/lib/components/FolderImportWizard.svelte
git commit -m "feat: add FolderImportWizard three-step modal component"
```

---

## Task 10: Frontend — Dashboard Integration

**Files:**
- Modify: `frontend/src/routes/+page.svelte`

Working directory: `/home/upb/src/automatic-ripping-machine-ui`

- [ ] **Step 1: Add Import Folder button and wizard to dashboard**

At the top of the `<script>` block in `+page.svelte`, add the import:

```typescript
import FolderImportWizard from '$lib/components/FolderImportWizard.svelte';
```

Add state for the wizard:

```typescript
let showImportWizard = $state(false);
```

In the template, find the first `<section>` or the area before the "Waiting for Review" section (around line 207). Add the import button before it:

```svelte
<!-- Import Folder button -->
<div class="mb-4 flex justify-end">
	<button
		type="button"
		onclick={() => showImportWizard = true}
		class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:bg-primary/90"
	>
		Import Folder
	</button>
</div>

<!-- Import wizard modal -->
<FolderImportWizard
	open={showImportWizard}
	onclose={() => showImportWizard = false}
	oncreated={() => { showImportWizard = false; refreshDashboard(); }}
/>
```

- [ ] **Step 2: Verify the dashboard renders without errors**

Run: `cd /home/upb/src/automatic-ripping-machine-ui/frontend && npm run build 2>&1 | tail -10`
Expected: Build succeeds with no errors

- [ ] **Step 3: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-ui
git add frontend/src/routes/+page.svelte
git commit -m "feat: add Import Folder button to dashboard with wizard integration"
```

---

## Task 11: End-to-End Verification

- [ ] **Step 1: Run all backend tests**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run frontend build**

Run: `cd /home/upb/src/automatic-ripping-machine-ui/frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Verify MakeMKV source refactor didn't break anything**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && grep -n 'dev:{job.devpath}' arm/ripper/makemkv.py`
Expected: Only line 918 (prescan_track_info — disc-only, intentionally untouched)

Run: `cd /home/upb/src/automatic-ripping-machine-neu && grep -n 'makemkv_source' arm/ripper/makemkv.py`
Expected: Lines 741, 1028, 1082 now use `job.makemkv_source`

- [ ] **Step 4: Verify migration chain is valid**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && grep -r "down_revision" arm/migrations/versions/j4k5l6m7n8o9*.py`
Expected: `down_revision = 'i3j4k5l6m7n8'` (chains from previous migration)

- [ ] **Step 5: Manual test with real BDMV folder (if available)**

Verify MakeMKV accepts `file:` prefix:
```bash
makemkvcon info --robot file:/path/to/bluray/folder --minlength=0
```
Expected: MakeMKV outputs track info (TCOUNT, TINFO lines) — confirms `file:` source works.
