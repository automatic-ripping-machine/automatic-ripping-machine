# Folder Import Feature — Design Spec

**Date:** 2026-03-21
**Status:** Draft
**Scope:** ARM neu backend + ARM UI frontend

## Problem

ARM currently only processes physical optical discs via udev triggers. Users with existing Blu-ray (BDMV) and DVD (VIDEO_TS) folder backups on disk have no way to feed them through the ARM pipeline for MKV extraction, metadata lookup, and transcoding.

## Solution

Add folder-based job support to ARM. Users select a source folder from a configurable ingress path via a three-step UI wizard. ARM auto-detects the disc type, runs metadata lookup, extracts MKVs via MakeMKV (`file:` source), and hands off to the transcoder — the same pipeline as disc jobs, just with a different source.

## Design Decisions

- **Approach A chosen:** New "Folder Job" type integrated into the existing Job model, not a separate service. Folder jobs share the MakeMKV → metadata → transcode pipeline with disc jobs but skip udev/mount/eject steps.
- **Ingress path:** A new configurable root path (`INGRESS_PATH`) scoped for folder imports, separate from `RAW_PATH`.
- **Initial scope:** BDMV and VIDEO_TS folders. Architecture supports future ISO/archive expansion.
- **Auto-detection:** ARM reads disc metadata (`bdmt_eng.xml`, folder name) to pre-populate title/year before user confirmation.
- **Source cleanup:** Out of scope for initial implementation — user manages ingress folder contents.
- **MakeMKV `file:` prefix:** MakeMKV CLI supports `file:/path/to/folder` as a source for BDMV/VIDEO_TS folders. This is untested in this codebase — implementation must include an early manual verification with the deployed MakeMKV version before building the full pipeline.

---

## 1. Configuration

### arm.yaml (template: `setup/arm.yaml`)

```yaml
# Folder import ingress root — UI file browser is scoped to this path
INGRESS_PATH: "/home/arm/media/ingress/"
```

- Must be an absolute path accessible inside the ARM container
- Typically an NFS share or bind mount
- The UI folder browser will not navigate above this root (security boundary)
- Must be added to both `setup/arm.yaml` (template) and any dev config files so the config auto-migration picks it up
- Note: `get_allowed_roots()` in `arm/services/file_browser.py` only includes roots where `os.path.isdir()` is true. If `INGRESS_PATH` does not exist yet, the ingress root will silently be absent from the file browser. The implementation should create the directory on startup if it does not exist (matching the pattern used for `RAW_PATH`/`COMPLETED_PATH`), or the wizard should show a clear error if the ingress path is not configured/mounted.

---

## 2. Data Model

### Job Model Changes (`arm/models/job.py`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `source_type` | String(16) | `"disc"` | `"disc"` or `"folder"` — determines pipeline path |
| `source_path` | String(1024) | `None` | Absolute path to source BDMV/VIDEO_TS folder (folder jobs only) |

- `devpath` becomes nullable — folder jobs do not have a device path
- All existing fields (`disctype`, `title`, `year`, `video_type`, `status`, `raw_path`, `tracks`, `config`, etc.) are reused as-is
- `source_type` defaults to `"disc"` so all existing jobs are unaffected

### Job Constructor Adaptation

The current `Job.__init__` requires `devpath` and unconditionally calls `parse_udev()` and `get_pid()`, which depend on a physical device. To support folder jobs:

- Add a classmethod factory: `Job.from_folder(source_path, disctype)` that:
  - Creates a Job instance without calling `parse_udev()` or drive-related methods
  - Sets `source_type = "folder"`, `source_path = source_path`, `devpath = None`
  - Sets `disctype` from the scan result
  - Initializes all other fields to their defaults
- The existing `Job(devpath)` constructor remains unchanged for disc jobs

### Job Property Review

- `job.ripping_finished` checks `self.drive` — returns `True` when `drive is None`, which is correct for folder jobs but should be made explicit with a `source_type` check
- `job.eject()` checks `self.drive` — folder pipeline must explicitly skip eject rather than relying on the guard clause
- Add a property `job.makemkv_source` that returns `f"dev:{self.devpath}"` for disc jobs or `f"file:{self.source_path}"` for folder jobs — used by all MakeMKV command construction

### Alembic Migration

A new Alembic migration is required to add `source_type` and `source_path` columns to the `job` table. The migration must:
- Add `source_type` as `String(16)` with default `"disc"` (non-nullable, backfills existing rows)
- Add `source_path` as `String(1024)`, nullable
- Make `devpath` nullable (ALTER COLUMN)

### Job Status Flow (Folder Jobs)

```
IDENTIFYING → IDLE → VIDEO_RIPPING → TRANSCODE_WAITING → SUCCESS/FAIL
```

- `IDENTIFYING`: Scan phase — detect disc type, read metadata
- `IDLE`: Job created with metadata, ready to rip (the wizard confirm step triggers the transition out of IDLE)
- `VIDEO_RIPPING`: MakeMKV extracting MKVs from folder
- `TRANSCODE_WAITING` → `SUCCESS/FAIL`: Existing transcoder pipeline

Note: `IDLE` is included for consistency with disc jobs and the dashboard UI's state grouping.

---

## 3. Backend API

### New Endpoints

#### `POST /api/v1/jobs/folder/scan`

Scans a folder, detects disc type, extracts metadata. Does not create a job.

**Request:**
```json
{
  "path": "/home/arm/media/ingress/Roujin Z 1991 Blu-ray"
}
```

**Response (200):**
```json
{
  "disc_type": "bluray",
  "label": "ROUJINZ",
  "title_suggestion": "Roujin Z",
  "year_suggestion": "1991",
  "folder_size_bytes": 24900000000,
  "stream_count": 28
}
```

**Errors:**
- `400`: Path not under `INGRESS_PATH`, path does not exist
- `422`: No BDMV or VIDEO_TS structure detected

**Implementation:**
- Validate path is under `INGRESS_PATH` using `os.path.realpath()` to resolve symlinks before comparison (prevent path traversal via symlinks)
- Check for `BDMV/` → Blu-ray (`bluray` or `bluray4k`); `VIDEO_TS/` → DVD
- Blu-ray: check `CERTIFICATE/id.bdmv` for UHD → use `disctype: "bluray4k"` directly; read `BDMV/META/DL/bdmt_eng.xml` for title
- DVD: attempt label from folder name
- Count streams in `BDMV/STREAM/` or `VIDEO_TS/`
- Calculate total folder size
- Timeout: folder traversal for size calculation should be bounded (e.g., 30s) to handle very large folders gracefully

#### `POST /api/v1/jobs/folder`

Creates a folder job with user-confirmed metadata and starts the rip pipeline.

**Request:**
```json
{
  "source_path": "/home/arm/media/ingress/Roujin Z 1991 Blu-ray",
  "title": "Roujin Z",
  "year": "1991",
  "video_type": "movie",
  "disctype": "bluray",
  "imdb_id": "tt0104012",
  "poster_url": "https://...",
  "multi_title": false
}
```

**Response (201):**
```json
{
  "job_id": 42,
  "status": "ripping",
  "source_type": "folder",
  "source_path": "/home/arm/media/ingress/Roujin Z 1991 Blu-ray"
}
```

**Errors:**
- `400`: Path validation failure, missing required fields
- `409`: Job already exists for this source path (prevent double-import)
- `422`: Source folder no longer exists or is not a valid disc structure

**Implementation:**
- Validate `source_path` is under `INGRESS_PATH` and still exists
- Check no active job with same `source_path` (prevent duplicates)
- Create Job with `source_type="folder"`, `source_path` set, `devpath=None`
- Apply user-provided metadata (title, year, video_type, imdb_id, poster_url)
- Launch rip pipeline in background thread (same pattern as disc jobs)

---

## 4. Processing Pipeline

### New Module: `arm/ripper/folder_ripper.py`

Orchestrates the folder import pipeline. This is a parallel entry point to `arm_ripper.rip_visual_media()` — it does NOT call into `arm_ripper.py` because that module is deeply coupled to disc/drive concepts (drive readiness polling, `_resolve_mdisc`, eject). Instead, `folder_ripper.py` replicates the relevant orchestration steps:

1. **Validate source** — confirm folder exists and contains BDMV or VIDEO_TS
2. **Setup raw path** — create output directory under `RAW_PATH` using existing `setup_rawpath()` logic
3. **Prep MakeMKV** — call existing `prep_mkv()` for license/key updates
4. **Invoke MakeMKV** — call `makemkvcon mkv file:{source_path} all {raw_path} --minlength={MINLENGTH}` (or per-track if `multi_title`)
5. **Reconcile filenames** — reuse existing `_reconcile_filenames()`
6. **Persist raw_path** — save to job record
7. **Notify transcoder** — reuse existing `transcoder_notify()`
8. **Update job status** — `TRANSCODE_WAITING` on success, `FAIL` on error
9. **No eject** — explicitly skipped for folder jobs

### MakeMKV Adaptation (`arm/ripper/makemkv.py`)

The existing `process_single_tracks()` and `rip_mainfeature()` hardcode `f"dev:{job.devpath}"` as the MakeMKV source. To support folder jobs:

- Add a `makemkv_source` property to the Job model that returns `f"dev:{self.devpath}"` for disc jobs or `f"file:{self.source_path}"` for folder jobs
- Refactor `process_single_tracks()` and `rip_mainfeature()` to use `job.makemkv_source` instead of the hardcoded `f"dev:{job.devpath}"`
- There are four `dev:{job.devpath}` occurrences in `makemkv.py` (lines 741, 918, 1028, 1082). Only lines 741, 1028, and 1082 (`rip_mainfeature`, `process_single_tracks`, and the backup function) need the `makemkv_source` refactor. Line 918 (`_info_scan`/`prescan_track_info`) is a disc-only pre-scan function not called by the folder pipeline — intentionally left untouched.
- This is a single-line change in each in-scope function — no duplication needed
- The existing `run()` generator, output parsing (`parse_line`), and progress tracking are source-agnostic and need no changes
- `folder_ripper.py` calls these refactored functions directly, bypassing the `makemkv()` entry point (which handles drive resolution and eject)

### Identify Adaptation (`arm/ripper/identify.py`)

- New function `identify_folder(path)` that:
  - Detects disc type from folder structure (BDMV → `bluray`/`bluray4k`, VIDEO_TS → `dvd`)
  - Reads `bdmt_eng.xml` for Blu-ray title/year
  - Checks `CERTIFICATE/id.bdmv` for UHD detection (returns `bluray4k` disctype)
  - Returns structured scan result (used by the scan endpoint)
- Does NOT mount/unmount, does NOT use ioctl drive checks
- Reuses existing `_label_from_bluray_xml()` helper where possible

---

## 5. UI — Three-Step Import Wizard

### Entry Point

"Import Folder" button on the dashboard (`+page.svelte`), top of page. Opens a full-screen modal wizard.

### Step 1: Pick Folder

- File browser component scoped to `INGRESS_PATH`
- Reuses the existing file browser service (`arm/services/file_browser.py`): add `'ingress': 'INGRESS_PATH'` to `get_allowed_roots()` mapping so `GET /api/v1/files/list?root=ingress` works out of the box
- Reuses existing `FileRow.svelte` and `FileIcon.svelte` UI components where applicable
- Shows directories with folder size
- Visual indicators for detected BDMV/VIDEO_TS folders
- "Next" button calls `POST /api/v1/jobs/folder/scan` and advances to step 2

### Step 2: Verify & Match

- Displays scan results: disc type badge, detected label, suggested title/year
- Auto-triggers metadata search with suggested title
- Shows search results with poster thumbnails (reuse `TitleSearch` pattern)
- Editable fields: title, year, video type (movie/series), IMDb ID
- "Search" button for manual re-search
- "Next" advances to step 3

### Step 3: Confirm & Queue

- Summary card: source path, disc type, title (year), video type, poster
- Destination preview (rendered folder/file name from naming patterns)
- "Import" button → `POST /api/v1/jobs/folder` → close wizard
- Job appears on dashboard immediately

### New UI Files

| File | Purpose |
|------|---------|
| `lib/components/FolderImportWizard.svelte` | Three-step modal wizard orchestrator |
| `lib/components/FolderBrowser.svelte` | Directory picker scoped to ingress path (wraps existing FileRow/FileIcon components) |
| `lib/api/folder.ts` | API client for scan and create endpoints |

---

## 6. Error Handling & Logging

### Error Categories

| Stage | Error | Handling |
|-------|-------|----------|
| **Scan** | Folder not found | 400 response, UI shows inline error |
| **Scan** | Path traversal attempt (outside INGRESS_PATH, including via symlinks) | 400 response, logged as warning. Uses `os.path.realpath()` to resolve symlinks before boundary check |
| **Scan** | No disc structure detected | 422 response, UI shows "not a valid disc folder" |
| **Scan** | Unreadable metadata XML | Log warning, return scan result without title suggestion |
| **Create** | Duplicate job for same source path | 409 response, UI shows "already importing" |
| **Create** | Source folder disappeared between scan and create | 422 response |
| **Rip** | MakeMKV binary not found | Job fails, logged as error |
| **Rip** | MakeMKV extraction failure | Job fails with error details, logged |
| **Rip** | No titles extracted | Job fails, "no titles found" logged |
| **Rip** | Insufficient disk space | Job fails, logged as error |
| **Transcode** | Transcoder unreachable | Job stays in TRANSCODE_WAITING, logged as warning |
| **Transcode** | Webhook rejected | Logged as error, job status updated |

### Logging

- All operations logged via `logging.getLogger(__name__)` with job ID context
- Folder jobs get per-job log files (same pattern as disc jobs)
- MakeMKV stdout/stderr captured to job log
- API validation errors logged at WARNING level
- Pipeline failures logged at ERROR level

---

## 7. Testing

### Backend Unit Tests

| Test File | Coverage |
|-----------|----------|
| `tests/test_folder_scan.py` | Disc type detection from folder structure (BDMV, VIDEO_TS, nested, invalid). Metadata XML parsing. UHD detection. Path validation (traversal prevention). |
| `tests/test_folder_job.py` | Job creation with `source_type="folder"`, nullable devpath. Duplicate prevention. Status transitions. |
| `tests/test_folder_ripper.py` | MakeMKV command construction with `file:` prefix. Error handling (missing binary, rip failure, no titles). Path validation. |
| `tests/test_folder_api.py` | API endpoint tests: scan (valid/invalid paths), create (success/duplicate/missing), auth. |

### Integration Tests

- End-to-end with mock BDMV folder structure (directory tree + metadata XML, no m2ts files)
- MakeMKV invocation with mocked subprocess (verify correct `file:` command)
- Job lifecycle: create → rip → transcode webhook → complete

### UI Tests

- Wizard flow: open → browse → select → scan → match → confirm
- Error states: invalid folder, scan failure, API unreachable
- Edge cases: empty ingress path, deeply nested folders

---

## 8. Future Expansion

The architecture supports these additions without structural changes:

- **ISO files**: Add `"iso"` to supported `source_type` values. Mount ISO to temp path, then process as folder. Or use MakeMKV's `iso:` prefix directly.
- **Archive files**: Detect `.iso`, `.img` extensions in folder browser. Extract/mount before scanning.
- **Batch import**: Scan entire `INGRESS_PATH` for all valid folders, present list for multi-select import.
- **Auto-import**: Optional watched folder mode — scan `INGRESS_PATH` periodically and auto-queue new folders.
- **Source cleanup**: Post-completion option to delete or move source folder from ingress.

---

## Affected Repositories

| Repository | Changes |
|------------|---------|
| `automatic-ripping-machine-neu` | Job model, config, API endpoints, folder_ripper module, identify adaptation, makemkv adaptation, tests |
| `automatic-ripping-machine-ui` | FolderImportWizard, FolderBrowser, folder API client, dashboard button |
