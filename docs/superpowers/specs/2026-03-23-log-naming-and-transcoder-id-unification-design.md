# Log Naming & Transcoder ID Unification

**Date:** 2026-03-23
**Status:** Draft
**Repos:** automatic-ripping-machine-neu, automatic-ripping-machine-transcoder, automatic-ripping-machine-ui

## Problem

Log filenames are derived from disc labels and titles, which leads to:
- **Collisions**: Two discs with the same label overwrite each other's logs (fragile `_{stage}` fallback)
- **Fragile sanitization**: Different code paths sanitize names differently (disc rips vs folder imports)
- **Scattered path construction**: ~11 call sites independently join `LOGPATH + job.logfile`
- **No single point of truth**: Log filename format is defined implicitly in multiple places

The transcoder compounds this by maintaining its own auto-increment ID separate from the ARM job ID, creating dual-identity confusion. Its logs use `job-{transcoder_id}.log`, disconnected from the ARM job they belong to.

## Design

### Log Filename Convention

```
Ripper log:     JOB_{arm_job_id}_Rip.log
Transcoder log: JOB_{arm_job_id}_Transcode.log
```

- **Job ID guarantees uniqueness** — no collision logic needed
- **Human-readable metadata** (title, year, etc.) stays in the database, not the filename
- **Both logs for the same job** sort together in the filesystem

### Phase 1: ARM-neu Log Naming Refactor

**Goal:** Single source of truth for log filenames, set once from job ID.

#### 1.1 New `log_filename()` helper

Add to `arm/ripper/logger.py`:

```python
def log_filename(job_id: int) -> str:
    """Canonical log filename for a rip job. Single source of truth."""
    return f"JOB_{job_id}_Rip.log"
```

This is the **only** place the filename format is defined.

#### 1.2 Refactor `setup_job_log(job)`

Current behavior:
- Derives filename from `job.label` (sanitized, with MusicBrainz lookup for music)
- Checks for collision, appends `_{stage}` if file exists
- Sets `job.logfile = filename`
- Returns full path

New behavior:
- Calls `log_filename(job.job_id)` to get the filename
- Sets `job.logfile = filename`
- Returns full path (`os.path.join(LOGPATH, filename)`)
- Remove: label sanitization, collision detection, `identify_audio_cd()` call for filename purposes

#### 1.3 Folder ripper alignment

Current: `folder.py` API sets `job.logfile = f"{safe_title}.log"` before `rip_folder()` is called. Then `folder_ripper.py` reads `job.logfile` to create a file handler.

New:
- `folder.py` **stops setting** `job.logfile` — leave it `None`
- `folder_ripper.py` calls `log_filename(job.job_id)` to set `job.logfile` and create the file handler
- Same pattern as disc rips: the rip function owns log setup

#### 1.4 Centralize log path construction

Current: ~11 sites do `os.path.join(cfg.arm_config['LOGPATH'], job.logfile)`.

New rules:
- `job.logfile` stores the **filename only** (unchanged)
- Functions that need the full path receive it as a parameter from their caller, OR construct it from config + `job.logfile`
- `_create_file_handler(filename)` continues to join internally (it already does this correctly)
- No function should construct the filename — only read it from `job.logfile` or call `log_filename()`

#### 1.5 Progress logs

Current: `arm/ripper/makemkv.py` creates progress logs at `{LOGPATH}/progress/{job_id}.log`.

This already uses job ID. **No change needed.**

#### 1.6 Files affected (ARM-neu)

| File | Change |
|------|--------|
| `arm/ripper/logger.py` | Add `log_filename()`, simplify `setup_job_log()`, rename `_create_file_handler` to `create_file_handler` (public API) |
| `arm/ripper/folder_ripper.py` | Set up log from `log_filename()` instead of reading pre-set `job.logfile`; update import from `_create_file_handler` to `create_file_handler` |
| `arm/api/v1/folder.py` | Remove `job.logfile` assignment (lines 115-116) |
| `arm/ripper/main.py` | Verify `setup_job_log()` calls still work (should be transparent) |
| `arm/services/jobs.py` | No change to path construction pattern (still reads `job.logfile` from DB) |
| `arm/services/files.py` | No change (still reads `job.logfile` from DB) |
| `arm/services/maintenance.py` | `get_orphan_logs()` — no change (scans for `.log` files, matches against DB) |
| `arm/ripper/utils.py` | `rip_music` and `rip_data` — verify they read `job.logfile` (set by `setup_job_log`) |

### Phase 2: Transcoder ID Unification

**Goal:** Transcoder uses ARM job ID as its primary identity. No auto-increment.

#### 2.1 Schema change

Current:
```python
id = Column(Integer, primary_key=True, autoincrement=True)
arm_job_id = Column(String(50), nullable=True)
```

New:
```python
id = Column(Integer, primary_key=True, autoincrement=False)
# arm_job_id column removed — id IS the ARM job ID
```

The webhook provides the ARM job ID; the transcoder uses it directly as its primary key.

#### 2.2 Log filename

```python
def log_filename(job_id: int) -> str:
    return f"JOB_{job_id}_Transcode.log"
```

Replaces current `f"job-{job.id}.log"`.

#### 2.3 Job creation from webhook

Current: Webhook receives `payload.job_id` (ARM ID), stores as `arm_job_id`, auto-generates its own `id`.

New:
- Webhook's `payload.job_id` becomes the primary key `id`
- `queue_job()` sets `id=arm_job_id` explicitly
- Dedup: check for existing job by `id` (primary key lookup), not source_path scan
- If a job with that ID already exists and is PENDING/PROCESSING, return it (idempotent)
- If a job with that ID exists and is COMPLETED/FAILED, reset to PENDING and re-queue (re-processing allowed)

#### 2.4 Collision handling

Collisions are **ARM's responsibility**. The transcoder trusts the ARM job ID is unique. If ARM sends the same job ID twice:
- If job is active (PENDING/PROCESSING): return existing job (idempotent)
- If job is terminal (COMPLETED/FAILED): reset status to PENDING and re-queue

#### 2.4.1 Log append on re-queue

When a job is re-queued, the log file (`JOB_{id}_Transcode.log`) is opened in **append mode**. This preserves the full history of every attempt in a single file, which is better for debugging than creating separate files per attempt. The `_setup_job_logging()` handler should use `FileHandler(..., mode='a')`.

#### 2.5 Code paths requiring `arm_job_id` → `id` migration

Several transcoder code paths currently reference `arm_job_id` and must be updated:

- **`_notify_arm_callback()`** (`transcoder.py`): Builds callback URL as `/api/v1/jobs/{job.arm_job_id}/transcode-callback` — change to `job.id`
- **`/jobs` API endpoint** (`main.py`): Filters by `arm_job_id` column in query params — change to filter by `id`
- **`queue_job()` dedup** (`transcoder.py`): Currently deduplicates by `source_path`; change to primary key lookup by `id`. Keep source_path as a secondary safety check (log warning if source_path differs for same ID)
- **Structlog context bindings** (`transcoder.py`): References to `arm_job_id` in context vars → use `job_id` bound from `job.id`
- **API response serialization** (`main.py`): Remove `arm_job_id` from JSON responses; `id` is now the ARM job ID
- **Webhook payload model** (`models.py`): `job_id` field validated as `String(50)` with regex — change to `int` coercion since ARM job IDs are integers

#### 2.6 Migration

SQLite considerations:
- SQLite < 3.35.0 cannot `ALTER TABLE DROP COLUMN` natively — use Alembic batch mode (recreate table) for portability
- `arm_job_id` is currently `String(50)` — backfill into `Integer` PK requires validation that all values are numeric
- No foreign keys reference `transcode_jobs.id` (verified), so table recreation is safe
- Historical data is not important — fresh DB on upgrade is acceptable. No backfill migration needed.

#### 2.7 Files affected (transcoder)

| File | Change |
|------|--------|
| `src/models.py` | Remove `arm_job_id` column; change `id` to `Integer, primary_key=True, autoincrement=False`; update webhook payload `job_id` to coerce to `int` |
| `src/transcoder.py` | `queue_job()` accepts `job_id: int` as required param, sets as PK; add `log_filename()` helper; update `_setup_job_logging()`; update `_notify_arm_callback()` to use `job.id`; update structlog context bindings; update dedup to PK lookup |
| `src/main.py` | Webhook handler passes `int(payload.job_id)` as PK; update `/jobs` query filter; remove `arm_job_id` from API responses |
| `src/database.py` | Migration using batch mode for `arm_job_id` removal and PK change |
| `src/config.py` | No change |
| `src/log_reader.py` | No change (reads filenames from disk) |

### Phase 3: UI Alignment

The ARM UI already reads `job.logfile` from the database and passes it to log viewer components. The only change is that filenames will look different (`JOB_42_Rip.log` instead of `BLADE_RUNNER_2049.log`).

**No code changes required in the UI.** The existing flow works:
1. Job fetched via API includes `logfile` field
2. `InlineLogFeed` receives filename as prop
3. Backend `log_reader` resolves filename to path in log directory

The UI can optionally be enhanced later to construct log filenames from job ID (since the format is predictable), but this is not required for the initial release.

## Migration & Rollout

### Data migration
- **ARM-neu**: No schema change. New jobs get ID-based filenames. Old jobs keep their existing `logfile` values. Old log files on disk remain readable.
- **Transcoder**: Schema migration required. Fresh deployments get the new schema. Existing deployments need a migration script.

### Backward compatibility
- Old log files remain on disk and are still viewable
- The orphan log detection (`get_orphan_logs()`) continues to work — it matches filenames against DB values regardless of naming convention
- No API contract changes

## Testing

### ARM-neu
- `setup_job_log()` produces `JOB_{id}_Rip.log` for disc rips
- `folder_ripper` produces `JOB_{id}_Rip.log` for folder imports
- File handler writes to correct path
- Cleanup removes handler on exit
- Progress logs unchanged

### Transcoder
- Webhook with ARM job ID creates job with that ID as PK
- Log file created as `JOB_{id}_Transcode.log`
- Duplicate webhook (same ID, active job) returns existing job
- API responses use single `id` field (no `arm_job_id`)
- ARM callback uses `job.id` (which is the ARM job ID)

## Decisions

1. **Re-queue policy**: Allowed. Terminal jobs (COMPLETED/FAILED) are reset to PENDING. Logs append to existing file.
2. **Historical data**: Not important. Fresh DB on upgrade — no backfill migration.
