# Log Naming & Transcoder ID Unification Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace fragile label-based log filenames with ID-based naming (`JOB_{id}_Rip.log` / `JOB_{id}_Transcode.log`) and unify the transcoder to use ARM job IDs as its primary key.

**Architecture:** Phase 1 refactors ARM-neu's logger to use a single `log_filename()` helper, removing all label/title-based naming. Phase 2 changes the transcoder to use the ARM job ID as its primary key (no auto-increment), updates log naming, and adds re-queue support with append-mode logging.

**Tech Stack:** Python, SQLAlchemy, SQLite, structlog, pytest

**Spec:** `docs/superpowers/specs/2026-03-23-log-naming-and-transcoder-id-unification-design.md`

**Deferred:** Spec section 1.4 (centralizing all ~11 `os.path.join(LOGPATH, job.logfile)` call sites) is not covered here. The existing pattern of reading `job.logfile` from DB and joining with config works correctly — cleanup can be done in a follow-up.

---

## Chunk 1: ARM-neu Log Naming Refactor

### File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `arm/ripper/logger.py` | Modify | Add `log_filename()`, simplify `setup_job_log()`, make `create_file_handler` public |
| `arm/ripper/folder_ripper.py` | Modify | Use `log_filename()` + `create_file_handler`, own log setup |
| `arm/api/v1/folder.py` | Modify | Remove `job.logfile` pre-assignment |
| `test/test_logger.py` | Modify | Update tests for new `log_filename()` and simplified `setup_job_log()` |
| `test/test_folder_ripper.py` | Modify | Add test for folder ripper log setup path |

---

### Task 1: Add `log_filename()` helper and make `create_file_handler` public

**Repo:** `/home/upb/src/automatic-ripping-machine-neu`
**Files:**
- Modify: `arm/ripper/logger.py:83-89` (`_create_file_handler` → `create_file_handler`)
- Modify: `arm/ripper/logger.py` (add `log_filename()` near line 83)
- Modify: `test/test_logger.py`

- [ ] **Step 1: Write test for `log_filename()`**

Add to `test/test_logger.py`:

```python
def test_log_filename_format():
    """log_filename() returns JOB_{id}_Rip.log"""
    from arm.ripper.logger import log_filename
    assert log_filename(42) == "JOB_42_Rip.log"
    assert log_filename(1) == "JOB_1_Rip.log"
    assert log_filename(9999) == "JOB_9999_Rip.log"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest test/test_logger.py::test_log_filename_format -v`
Expected: FAIL with `ImportError` (log_filename doesn't exist yet)

- [ ] **Step 3: Implement `log_filename()` and rename `_create_file_handler`**

In `arm/ripper/logger.py`, add before `_create_file_handler` (around line 83):

```python
def log_filename(job_id: int) -> str:
    """Canonical log filename for a rip job. Single source of truth."""
    return f"JOB_{job_id}_Rip.log"
```

Then rename `_create_file_handler` to `create_file_handler` (drop the underscore). Update its two call sites within the same file:
- Line 125 in `setup_job_log`: `logger.addHandler(create_file_handler(log_file))`
- Line 191 in `create_early_logger`: `handler = create_file_handler("arm.log")`

- [ ] **Step 4: Update `folder_ripper.py` import**

In `arm/ripper/folder_ripper.py` line 17, change:
```python
from arm.ripper.logger import _create_file_handler
```
to:
```python
from arm.ripper.logger import create_file_handler
```

And line 46:
```python
file_handler = create_file_handler(job.logfile)
```

- [ ] **Step 5: Update existing tests that reference `_create_file_handler`**

In `test/test_logger.py`, update any imports or references from `_create_file_handler` to `create_file_handler`. The `test_json_file_output` test (around line 34) likely imports it directly.

- [ ] **Step 6: Run all logger tests**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest test/test_logger.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-neu
git add arm/ripper/logger.py arm/ripper/folder_ripper.py test/test_logger.py
git commit -m "refactor: add log_filename() helper and make create_file_handler public"
```

---

### Task 2: Simplify `setup_job_log()` to use `log_filename()`

**Repo:** `/home/upb/src/automatic-ripping-machine-neu`
**Files:**
- Modify: `arm/ripper/logger.py:92-142` (`setup_job_log`)
- Modify: `test/test_logger.py`

- [ ] **Step 1: Update test for `setup_job_log()` to expect ID-based filename**

In `test/test_logger.py`, find `test_setup_job_log_swaps_handler` (around line 80). Update the assertion that checks `job.logfile` to expect the new format:

```python
def test_setup_job_log_sets_id_based_filename(mock_job, tmp_path, monkeypatch):
    """setup_job_log() uses log_filename() to set job.logfile = JOB_{id}_Rip.log"""
    monkeypatch.setitem(cfg.arm_config, "LOGPATH", str(tmp_path))
    monkeypatch.setitem(cfg.arm_config, "LOGLEVEL", "DEBUG")
    mock_job.job_id = 42
    mock_job.label = "SOME_DISC"
    mock_job.devpath = "/dev/sr0"

    result = setup_job_log(mock_job)

    assert mock_job.logfile == "JOB_42_Rip.log"
    assert result == str(tmp_path / "JOB_42_Rip.log")
```

- [ ] **Step 2: Run test to verify it fails (still using old label-based naming)**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest test/test_logger.py::test_setup_job_log_sets_id_based_filename -v`
Expected: FAIL — `job.logfile` is `"SOME_DISC.log"` not `"JOB_42_Rip.log"`

- [ ] **Step 3: Simplify `setup_job_log()`**

Replace the body of `setup_job_log()` in `arm/ripper/logger.py` (lines 92-142):

```python
def setup_job_log(job):
    """
    Setup logging and return the path to the logfile for redirection of external calls.

    Sets job.logfile to the canonical ID-based filename. Returns the full path.
    Binds job context (job_id, label, devpath) into structlog contextvars so every
    subsequent log call automatically includes these fields.
    """
    log_file = log_filename(job.job_id)
    log_full = os.path.join(cfg.arm_config['LOGPATH'], log_file)

    job.logfile = log_file

    # Swap the file handler to the per-job log file.
    # Operate on root logger so all logging.info() calls are captured.
    logger = logging.getLogger()
    logger.setLevel(cfg.arm_config["LOGLEVEL"])
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)

    logger.addHandler(create_file_handler(log_file))

    # Bind job context into structlog contextvars — all subsequent log calls
    # from any module will include these fields automatically
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        job_id=job.job_id,
        label=job.label,
        devpath=job.devpath,
    )

    # These stop apprise and others spitting our secret keys if users post log online
    logging.getLogger("apprise").setLevel(logging.WARN)
    logging.getLogger("requests").setLevel(logging.WARN)
    logging.getLogger("urllib3").setLevel(logging.WARN)

    # Return the full logfile location to the logs
    return log_full
```

Key changes:
- Removed label sanitization, `identify_audio_cd()` call, collision detection
- Uses `log_filename(job.job_id)` instead

- [ ] **Step 4: Run logger tests**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest test/test_logger.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run ripper main tests (they mock `setup_job_log`)**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest test/test_ripper_main.py -v`
Expected: ALL PASS (these mock `setup_job_log` so the internal change is transparent)

- [ ] **Step 6: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-neu
git add arm/ripper/logger.py test/test_logger.py
git commit -m "refactor: simplify setup_job_log() to use ID-based log_filename()"
```

---

### Task 3: Folder ripper owns its own log setup

**Repo:** `/home/upb/src/automatic-ripping-machine-neu`
**Files:**
- Modify: `arm/ripper/folder_ripper.py:17,40-53`
- Modify: `arm/api/v1/folder.py:114-116`
- Modify: `test/test_folder_ripper.py`

- [ ] **Step 1: Write test for folder ripper log setup**

Add to `test/test_folder_ripper.py`:

```python
def test_rip_folder_sets_id_based_logfile(mock_job, tmp_path, monkeypatch):
    """rip_folder() sets job.logfile = JOB_{id}_Rip.log via log_filename()"""
    monkeypatch.setitem(cfg.arm_config, "LOGPATH", str(tmp_path))
    monkeypatch.setitem(cfg.arm_config, "LOGLEVEL", "DEBUG")
    mock_job.job_id = 99
    mock_job.logfile = None  # folder.py no longer pre-sets this
    mock_job.source_path = "/nonexistent"  # will fail at validation, that's fine

    with pytest.raises(FileNotFoundError):
        rip_folder(mock_job)

    # Even though it failed, log setup should have happened first
    assert mock_job.logfile == "JOB_99_Rip.log"
    assert (tmp_path / "JOB_99_Rip.log").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest test/test_folder_ripper.py::test_rip_folder_sets_id_based_logfile -v`
Expected: FAIL — folder ripper still reads pre-set `job.logfile`

- [ ] **Step 3: Update `folder_ripper.py` to own log setup**

In `arm/ripper/folder_ripper.py`, update imports (line 17):
```python
from arm.ripper.logger import create_file_handler, log_filename
```

Replace the log setup block (lines 40-53) with:

```python
    file_handler = None
    try:
        # 0. Set up per-job log file so the UI can display rip progress
        log_file = log_filename(job.job_id)
        job.logfile = log_file

        root_logger = logging.getLogger()
        file_handler = create_file_handler(log_file)
        root_logger.addHandler(file_handler)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            job_id=job.job_id,
            source_type="folder",
            source_path=job.source_path,
        )
```

And add `structlog.contextvars.clear_contextvars()` to the `finally` block:

```python
    finally:
        # Clean up the per-job file handler and structlog context
        if file_handler:
            logging.getLogger().removeHandler(file_handler)
            file_handler.close()
        structlog.contextvars.clear_contextvars()
```

- [ ] **Step 4: Remove `job.logfile` assignment from `folder.py`**

In `arm/api/v1/folder.py`, remove lines 113-116 (the comment, safe_title construction, and logfile assignment):
```python
    # Set logfile name (used by job list endpoint and log viewer)
    safe_title = re.sub(r'[^\w\-.]', '_', req.title or 'folder_import')
    job.logfile = f"{safe_title}.log"
```

Also remove the `import re` at line 2 if it's no longer used elsewhere in the file.

- [ ] **Step 5: Run folder ripper tests**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest test/test_folder_ripper.py -v`
Expected: ALL PASS

- [ ] **Step 6: Run folder API tests if they exist**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest test/ -k folder -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-neu
git add arm/ripper/folder_ripper.py arm/api/v1/folder.py test/test_folder_ripper.py
git commit -m "refactor: folder ripper owns log setup via log_filename()"
```

---

### Task 4: Full test suite pass for ARM-neu

**Repo:** `/home/upb/src/automatic-ripping-machine-neu`

- [ ] **Step 1: Run the full test suite**

Run: `cd /home/upb/src/automatic-ripping-machine-neu && python -m pytest test/ -v --tb=short`
Expected: ALL PASS

- [ ] **Step 2: Fix any failures**

If any tests fail due to the rename (`_create_file_handler` → `create_file_handler`) or the logfile format change, update them to match the new convention.

- [ ] **Step 3: Commit any test fixes**

```bash
cd /home/upb/src/automatic-ripping-machine-neu
git add -A
git commit -m "test: fix tests for ID-based log naming refactor"
```

---

## Chunk 2: Transcoder ID Unification & Log Naming

### File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/models.py` | Modify | Remove `arm_job_id` column, change PK to non-autoincrement, update webhook payload |
| `src/transcoder.py` | Modify | Add `log_filename()`, update `queue_job()`, `_setup_job_logging()`, `_notify_arm_callback()` |
| `src/main.py` | Modify | Update webhook handler, `/jobs` endpoint, remove `arm_job_id` from responses |
| `src/database.py` | Modify | Schema migration for PK change and column removal |
| `tests/test_models.py` | Modify | Update webhook payload and model tests |
| `tests/test_transcoder.py` | Modify | Update queue_job and job processing tests |
| `tests/test_database.py` | Modify | Update schema tests |

---

### Task 5: Add `log_filename()` helper to transcoder

**Repo:** `/home/upb/src/automatic-ripping-machine-transcoder`
**Files:**
- Modify: `src/transcoder.py`
- Modify: `tests/test_transcoder.py`

- [ ] **Step 1: Write test for transcoder `log_filename()`**

Add to `tests/test_transcoder.py`:

```python
def test_log_filename_format():
    """log_filename() returns JOB_{id}_Transcode.log"""
    from src.transcoder import log_filename
    assert log_filename(42) == "JOB_42_Transcode.log"
    assert log_filename(1) == "JOB_1_Transcode.log"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/upb/src/automatic-ripping-machine-transcoder && python -m pytest tests/test_transcoder.py::test_log_filename_format -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement `log_filename()`**

Add to `src/transcoder.py` near the top-level helpers:

```python
def log_filename(job_id: int) -> str:
    """Canonical log filename for a transcode job. Single source of truth."""
    return f"JOB_{job_id}_Transcode.log"
```

- [ ] **Step 4: Update log naming in `_process_job()`**

In `src/transcoder.py` around line 576, change:
```python
logfile_name = f"job-{job.id}.log"
```
to:
```python
logfile_name = log_filename(job.id)
```

- [ ] **Step 5: Verify `_setup_job_logging()` uses append mode**

In `src/transcoder.py` around line 367, verify the FileHandler already uses append mode (Python's `FileHandler` defaults to `mode='a'`). If it explicitly sets `mode='w'`, change to `mode='a'`. If no mode is specified, it's already correct — add an explicit `mode='a'` for clarity:
```python
handler = logging.FileHandler(str(log_dir / logfile_name), mode='a')
```

- [ ] **Step 6: Run tests**

Run: `cd /home/upb/src/automatic-ripping-machine-transcoder && python -m pytest tests/test_transcoder.py -v --tb=short`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-transcoder
git add src/transcoder.py tests/test_transcoder.py
git commit -m "refactor: add log_filename() helper with ID-based naming"
```

---

### Task 6: Update transcoder model — remove `arm_job_id`, change PK

**Repo:** `/home/upb/src/automatic-ripping-machine-transcoder`
**Files:**
- Modify: `src/models.py:41-71` (TranscodeJobDB)
- Modify: `src/models.py:73-154` (WebhookPayload)
- Modify: `tests/test_models.py`

- [ ] **Step 1: Write tests for new model**

Update `tests/test_models.py`:

```python
def test_transcode_job_db_no_autoincrement():
    """TranscodeJobDB.id is not auto-incrementing — it's the ARM job ID."""
    col = TranscodeJobDB.__table__.columns["id"]
    assert col.primary_key
    assert col.autoincrement == False  # noqa: E712

def test_transcode_job_db_no_arm_job_id_column():
    """arm_job_id column has been removed."""
    assert "arm_job_id" not in TranscodeJobDB.__table__.columns

def test_webhook_payload_job_id_coerced_to_int():
    """Webhook payload.job_id is coerced to int."""
    payload = WebhookPayload(title="Test", path="/tmp/test", job_id="42")
    assert payload.job_id == 42
    assert isinstance(payload.job_id, int)

def test_webhook_payload_job_id_required():
    """Webhook payload requires job_id."""
    with pytest.raises(ValidationError):
        WebhookPayload(title="Test", path="/tmp/test")  # no job_id

def test_webhook_payload_rejects_non_numeric_job_id():
    """Webhook payload rejects non-numeric job_id."""
    with pytest.raises(ValidationError):
        WebhookPayload(title="Test", path="/tmp/test", job_id="abc")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/upb/src/automatic-ripping-machine-transcoder && python -m pytest tests/test_models.py -v --tb=short`
Expected: FAIL — model still has `arm_job_id` and autoincrement

- [ ] **Step 3: Update `TranscodeJobDB` model**

In `src/models.py`, modify the TranscodeJobDB class:

```python
class TranscodeJobDB(Base):
    """Database model for transcode jobs."""
    __tablename__ = "transcode_jobs"

    id = Column(Integer, primary_key=True, autoincrement=False)
    title = Column(String(500), nullable=False)
    source_path = Column(String(1000), nullable=False)
    output_path = Column(String(1000), nullable=True)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
    progress = Column(Float, default=0.0)
    # arm_job_id REMOVED — id IS the ARM job ID
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    # ... rest unchanged
```

- [ ] **Step 4: Update `WebhookPayload` — `job_id` is required int**

In `src/models.py`, update the WebhookPayload class:

Change `job_id` field from:
```python
job_id: Optional[str] = Field(None, max_length=MAX_JOB_ID_LENGTH)
```
to:
```python
job_id: int
```

Replace the `coerce_job_id` validator with:
```python
@field_validator("job_id", mode="before")
@classmethod
def coerce_job_id(cls, v):
    """Coerce job_id to int. ARM always sends integer job IDs."""
    try:
        return int(v)
    except (TypeError, ValueError):
        raise ValueError("job_id must be a valid integer")
```

- [ ] **Step 5: Run model tests**

Run: `cd /home/upb/src/automatic-ripping-machine-transcoder && python -m pytest tests/test_models.py -v --tb=short`
Expected: ALL PASS (new tests pass, update any old tests that reference `arm_job_id`)

- [ ] **Step 6: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-transcoder
git add src/models.py tests/test_models.py
git commit -m "refactor: remove arm_job_id, use ARM job ID as primary key"
```

---

### Task 7: Remove all `arm_job_id` references from transcoder (atomic)

> **Important:** This task combines queue_job, callback, structlog, webhook, and /jobs changes into one atomic task. Committing these separately would leave the code broken between commits.

**Repo:** `/home/upb/src/automatic-ripping-machine-transcoder`
**Files:**
- Modify: `src/transcoder.py` (queue_job, _notify_arm_callback, _process_job, _restore_pending_jobs, structlog bindings)
- Modify: `src/main.py` (webhook handler, /jobs endpoint)
- Modify: `tests/test_transcoder.py`

- [ ] **Step 1: Write tests for new queue_job behavior**

Add to `tests/test_transcoder.py`:

```python
async def test_queue_job_uses_arm_job_id_as_pk(worker, tmp_path):
    """queue_job() creates a job with the ARM job ID as primary key."""
    job_id, created = await worker.queue_job(
        job_id=42,
        title="Test Movie",
        source_path=str(tmp_path),
    )
    assert job_id == 42
    assert created is True

async def test_queue_job_idempotent_for_active_job(worker, tmp_path):
    """Re-queueing an active job returns existing job."""
    job_id1, created1 = await worker.queue_job(job_id=42, title="Test", source_path=str(tmp_path))
    job_id2, created2 = await worker.queue_job(job_id=42, title="Test", source_path=str(tmp_path))
    assert job_id1 == job_id2 == 42
    assert created1 is True
    assert created2 is False

async def test_queue_job_requeues_terminal_job(worker, tmp_path):
    """Re-queueing a completed/failed job resets it to PENDING."""
    job_id, _ = await worker.queue_job(job_id=42, title="Test", source_path=str(tmp_path))
    # Manually set to COMPLETED
    async with get_db() as db:
        from sqlalchemy import update
        await db.execute(update(TranscodeJobDB).where(TranscodeJobDB.id == 42).values(status=JobStatus.COMPLETED))
        await db.commit()

    job_id2, created2 = await worker.queue_job(job_id=42, title="Test", source_path=str(tmp_path))
    assert job_id2 == 42
    assert created2 is True  # re-queued
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/upb/src/automatic-ripping-machine-transcoder && python -m pytest tests/test_transcoder.py::test_queue_job_uses_arm_job_id_as_pk -v`
Expected: FAIL

- [ ] **Step 3: Update `queue_job()` method**

In `src/transcoder.py`, update `queue_job()` signature — replace `arm_job_id` param with `job_id: int` as first positional param:

```python
async def queue_job(
    self,
    job_id: int,  # ARM job ID — used as primary key
    title: str,
    source_path: str,
    video_type: str | None = None,
    year: str | None = None,
    disctype: str | None = None,
    poster_url: str | None = None,
    config_overrides: dict | None = None,
    multi_title: bool = False,
    tracks: list[dict] | None = None,
    folder_name: str | None = None,
    title_name: str | None = None,
) -> tuple[int, bool]:
```

Replace the dedup and creation logic:

```python
    async with get_db() as db:
        # Check for existing job by primary key
        existing = await db.get(TranscodeJobDB, job_id)
        if existing:
            if existing.status in (JobStatus.PENDING, JobStatus.PROCESSING):
                # Active job — return idempotently
                return existing.id, False
            else:
                # Terminal job (COMPLETED/FAILED) — reset for re-queue
                existing.status = JobStatus.PENDING
                existing.progress = 0.0
                existing.error = None
                existing.started_at = None
                existing.completed_at = None
                existing.retry_count = (existing.retry_count or 0) + 1
                await db.commit()
                return existing.id, True

        # Create new job with ARM job ID as PK
        job_db = TranscodeJobDB(
            id=job_id,
            title=title,
            source_path=source_path,
            # ... all other fields same as before, minus arm_job_id
        )
        db.add(job_db)
        await db.commit()
        return job_db.id, True
```

- [ ] **Step 4: Update `TranscodeJob` in-memory dataclass**

> **Critical:** There is a `TranscodeJob` dataclass (separate from `TranscodeJobDB`) used as the in-memory representation during processing. Find it in `src/transcoder.py` or `src/models.py`. Remove the `arm_job_id` field from it. Update every place that constructs a `TranscodeJob` instance (typically in `_process_job()` and `_restore_pending_jobs()`) to stop passing `arm_job_id`.

- [ ] **Step 5: Update `_notify_arm_callback()`**

In `src/transcoder.py`, replace all `job.arm_job_id` references:

```python
# Old guard:
if not settings.arm_callback_url or not job.arm_job_id:
# New:
if not settings.arm_callback_url:

# Old URL:
url = f"{settings.arm_callback_url.rstrip('/')}/api/v1/jobs/{job.arm_job_id}/transcode-callback"
# New:
url = f"{settings.arm_callback_url.rstrip('/')}/api/v1/jobs/{job.id}/transcode-callback"

# Old log:
logger.info(f"ARM callback sent ({resp.status_code}): {status} for ARM job {job.arm_job_id}")
# New:
logger.info(f"ARM callback sent ({resp.status_code}): {status} for job {job.id}")
```

- [ ] **Step 6: Grep for ALL remaining `arm_job_id` references in `src/transcoder.py`**

Run: `grep -n "arm_job_id" src/transcoder.py`

Every hit must be updated. Common locations:
- ~line 357: structlog context binding
- ~line 572: another context binding
- ~line 942: log message

Replace all with `job.id` or remove.

- [ ] **Step 7: Update webhook handler in `main.py`**

In `src/main.py`, the webhook handler around line 435 currently passes:
```python
arm_job_id=payload.job_id,
```
Change to:
```python
job_id=payload.job_id,
```

- [ ] **Step 8: Update `/jobs` endpoint in `main.py`**

Rename parameter from `arm_job_id` to `job_id`:
```python
job_id: int | None = Query(None),
```

Update filter:
```python
if job_id is not None:
    query = query.where(TranscodeJobDB.id == job_id)
```

Remove `arm_job_id` from response serialization dict.

- [ ] **Step 9: Grep for ALL remaining `arm_job_id` references in `src/main.py`**

Run: `grep -n "arm_job_id" src/main.py`

Every hit must be updated or removed.

- [ ] **Step 10: Run all tests**

Run: `cd /home/upb/src/automatic-ripping-machine-transcoder && python -m pytest tests/ -v --tb=short`
Expected: ALL PASS

- [ ] **Step 11: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-transcoder
git add src/transcoder.py src/main.py tests/test_transcoder.py
git commit -m "refactor: remove arm_job_id, use unified job ID across transcoder"
```

---

### Task 8: Update database schema migration

**Repo:** `/home/upb/src/automatic-ripping-machine-transcoder`
**Files:**
- Modify: `src/database.py:39-60` (`_add_missing_columns`)

- [ ] **Step 1: Update `_add_missing_columns()`**

Since historical data doesn't matter, the simplest approach is to drop and recreate the table if the old schema is detected. In `src/database.py`, update the migration logic:

The existing `_add_missing_columns()` runs inside a `conn.run_sync()` block — it uses synchronous `conn.execute()`. Add a check for the old `arm_job_id` column. If found, drop and recreate the table:

```python
# Check if we need to migrate from old schema (arm_job_id present)
result = conn.execute(text("PRAGMA table_info(transcode_jobs)"))
columns = {row[1] for row in result.fetchall()}
if "arm_job_id" in columns:
    # Old schema — drop and recreate (historical data not important)
    conn.execute(text("DROP TABLE transcode_jobs"))
    Base.metadata.create_all(conn)
    return
```

- [ ] **Step 2: Update schema tests**

In `tests/test_database.py`, update any tests that check for the `arm_job_id` column to verify it does NOT exist.

- [ ] **Step 3: Run database tests**

Run: `cd /home/upb/src/automatic-ripping-machine-transcoder && python -m pytest tests/test_database.py -v --tb=short`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-transcoder
git add src/database.py tests/test_database.py
git commit -m "refactor: schema migration drops old arm_job_id table, recreates with unified PK"
```

---

### Task 9: Full transcoder test suite pass

**Repo:** `/home/upb/src/automatic-ripping-machine-transcoder`

- [ ] **Step 1: Run the full test suite**

Run: `cd /home/upb/src/automatic-ripping-machine-transcoder && python -m pytest tests/ -v --tb=short`
Expected: ALL PASS

- [ ] **Step 2: Fix any remaining test failures**

Common things to look for:
- Tests that create `TranscodeJobDB` objects without passing `id` (now required since no autoincrement)
- Tests that reference `job.arm_job_id` or `arm_job_id` in assertions
- Tests that check API response JSON for `arm_job_id` field
- Webhook test payloads missing `job_id` (now required)

- [ ] **Step 3: Commit any test fixes**

```bash
cd /home/upb/src/automatic-ripping-machine-transcoder
git add -A
git commit -m "test: fix tests for unified ID and log naming refactor"
```

---

## Chunk 3: Integration Verification

### Task 10: Cross-repo integration check

This task verifies the changes work together across repos.

- [ ] **Step 1: Verify ARM-neu log naming end-to-end**

In `/home/upb/src/automatic-ripping-machine-neu`, run:
```bash
python -m pytest test/ -v --tb=short
```
Expected: ALL PASS

- [ ] **Step 2: Verify transcoder end-to-end**

In `/home/upb/src/automatic-ripping-machine-transcoder`, run:
```bash
python -m pytest tests/ -v --tb=short
```
Expected: ALL PASS

- [ ] **Step 3: Verify UI still reads logs correctly**

No code changes in the UI, but verify the log reader works with the new naming:
```bash
cd /home/upb/src/automatic-ripping-machine-ui
python -m pytest tests/ -v --tb=short -k log
```

- [ ] **Step 4: Manual smoke test with docker compose**

Build and start the stack:
```bash
cd /home/upb/src/automatic-ripping-machine-neu
docker compose down && docker compose up --build -d
```

Verify:
1. Start a job (disc or folder import)
2. Check that log file is created as `JOB_{id}_Rip.log` in the logs directory
3. Check that the UI can display the log via the job detail page
4. If transcoder is configured, verify `JOB_{id}_Transcode.log` is created

- [ ] **Step 5: Commit any final fixes**

```bash
git add -A && git commit -m "fix: integration adjustments for log naming unification"
```
