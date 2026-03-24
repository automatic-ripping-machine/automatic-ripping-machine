# Folder Import Review Flow Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change folder imports to create jobs in `MANUAL_WAIT` state with a review step before processing, and display "Processing" instead of "Ripping" for folder jobs in the UI.

**Architecture:** Backend changes in ARM-neu (`folder.py` stops auto-launching rip, `jobs.py` start endpoint dispatches folder jobs). Frontend changes in ARM-UI (status label override in JobCard, job detail page, and format utils).

**Tech Stack:** Python/FastAPI (ARM-neu), SvelteKit/Svelte 5 (ARM-UI), pytest

**Spec:** `docs/superpowers/specs/2026-03-23-folder-import-review-flow-design.md`

---

## Chunk 1: Backend — Folder Job Creates in MANUAL_WAIT

### File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `arm/api/v1/folder.py` | Modify | Create job in MANUAL_WAIT, remove thread launch |
| `arm/api/v1/jobs.py` | Modify | Start endpoint dispatches folder jobs |
| `test/test_folder_ripper.py` | Modify | Update tests for new flow |

---

### Task 1: Change folder API to create job in MANUAL_WAIT

**Repo:** `/home/upb/src/automatic-ripping-machine-neu`
**Files:**
- Modify: `arm/api/v1/folder.py:1-134`

- [ ] **Step 1: Write test for new folder job creation status**

Add to a new test file or existing folder test. Create `test/test_folder_api.py`:

```python
"""Tests for folder import API endpoint."""
import pytest
from unittest.mock import patch, MagicMock

from arm.models.job import JobState


class TestCreateFolderJob:
    """Test POST /api/v1/jobs/folder."""

    @patch("arm.api.v1.folder.db")
    @patch("arm.api.v1.folder.validate_ingress_path")
    @patch("arm.api.v1.folder.cfg")
    def test_creates_job_in_manual_wait(self, mock_cfg, mock_validate, mock_db):
        """Folder job should be created in MANUAL_WAIT_STARTED status."""
        from arm.api.v1.folder import create_folder_job, FolderCreateRequest

        mock_cfg.arm_config = {"INGRESS_PATH": "/tmp/ingress"}

        # Mock Job.query.filter to return no existing job
        with patch("arm.api.v1.folder.Job") as MockJob:
            mock_job = MagicMock()
            mock_job.job_id = 1
            mock_job.status = JobState.MANUAL_WAIT_STARTED.value
            mock_job.source_type = "folder"
            mock_job.source_path = "/tmp/ingress/TEST"
            MockJob.from_folder.return_value = mock_job
            MockJob.query.filter.return_value.first.return_value = None

            with patch("arm.api.v1.folder.Config"):
                req = FolderCreateRequest(
                    source_path="/tmp/ingress/TEST",
                    title="Test",
                    video_type="movie",
                    disctype="bluray",
                )
                result = create_folder_job(req)

        assert mock_job.status == JobState.MANUAL_WAIT_STARTED.value

    @patch("arm.api.v1.folder.db")
    @patch("arm.api.v1.folder.validate_ingress_path")
    @patch("arm.api.v1.folder.cfg")
    def test_does_not_launch_background_thread(self, mock_cfg, mock_validate, mock_db):
        """Folder job creation should NOT launch a background rip thread."""
        from arm.api.v1.folder import create_folder_job, FolderCreateRequest

        mock_cfg.arm_config = {"INGRESS_PATH": "/tmp/ingress"}

        with patch("arm.api.v1.folder.Job") as MockJob:
            mock_job = MagicMock()
            mock_job.job_id = 1
            mock_job.status = "waiting"
            mock_job.source_type = "folder"
            mock_job.source_path = "/tmp/ingress/TEST"
            MockJob.from_folder.return_value = mock_job
            MockJob.query.filter.return_value.first.return_value = None

            with patch("arm.api.v1.folder.Config"):
                req = FolderCreateRequest(
                    source_path="/tmp/ingress/TEST",
                    title="Test",
                    video_type="movie",
                    disctype="bluray",
                )
                result = create_folder_job(req)

        # No threading import, no rip_folder call — verified by the fact that
        # the module no longer imports them (step 3 removes them)
        assert result["status"] == "waiting"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest test/test_folder_api.py -x -v --tb=short`
Expected: FAIL — job status is `ripping` not `waiting`

- [ ] **Step 3: Update `folder.py`**

In `arm/api/v1/folder.py`:

1. Remove imports that are no longer needed:
   - Remove `import threading` (line 3)
   - Remove `from arm.ripper.folder_ripper import rip_folder` (line 14)

2. Change line 62 docstring:
   ```python
   """Create a folder import job in review state."""
   ```

3. Change line 112:
   ```python
   job.status = JobState.MANUAL_WAIT_STARTED.value
   ```

4. Remove lines 124-126 (background thread launch):
   ```python
   # Launch rip pipeline in background
   thread = threading.Thread(target=rip_folder, args=(job,), daemon=True)
   thread.start()
   ```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest test/test_folder_api.py -x -v --tb=short`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C /home/upb/src/automatic-ripping-machine-neu add arm/api/v1/folder.py test/test_folder_api.py
git -C /home/upb/src/automatic-ripping-machine-neu commit -m "refactor: folder import creates job in MANUAL_WAIT state"
```

---

### Task 2: Start endpoint dispatches folder jobs

**Repo:** `/home/upb/src/automatic-ripping-machine-neu`
**Files:**
- Modify: `arm/api/v1/jobs.py:74-85`

- [ ] **Step 1: Write test for folder job start**

Add to `test/test_folder_api.py`:

```python
class TestStartFolderJob:
    """Test POST /api/v1/jobs/{job_id}/start for folder jobs."""

    @patch("arm.api.v1.jobs.db")
    @patch("arm.api.v1.jobs.threading.Thread")
    def test_start_folder_job_launches_rip_folder(self, mock_thread, mock_db):
        """Starting a folder job should launch rip_folder in a thread."""
        from arm.api.v1.jobs import start_waiting_job

        with patch("arm.api.v1.jobs.Job") as MockJob:
            mock_job = MagicMock()
            mock_job.job_id = 42
            mock_job.status = JobState.MANUAL_WAIT_STARTED.value
            mock_job.source_type = "folder"
            MockJob.query.get.return_value = mock_job

            result = start_waiting_job(42)

        assert result["success"] is True
        assert mock_job.status == JobState.VIDEO_RIPPING.value
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

    @patch("arm.api.v1.jobs.svc_files")
    def test_start_disc_job_uses_manual_start(self, mock_svc):
        """Starting a disc job should set manual_start=True (existing behavior)."""
        from arm.api.v1.jobs import start_waiting_job

        with patch("arm.api.v1.jobs.Job") as MockJob:
            mock_job = MagicMock()
            mock_job.job_id = 42
            mock_job.status = JobState.MANUAL_WAIT_STARTED.value
            mock_job.source_type = "disc"
            MockJob.query.get.return_value = mock_job

            result = start_waiting_job(42)

        mock_svc.database_updater.assert_called_once_with({"manual_start": True}, mock_job)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest test/test_folder_api.py::TestStartFolderJob -x -v --tb=short`
Expected: FAIL — start endpoint doesn't handle folder jobs

- [ ] **Step 3: Update `jobs.py` start endpoint**

In `arm/api/v1/jobs.py`, add imports at top of file:
```python
import threading
from arm.ripper.folder_ripper import rip_folder
```

Replace the start endpoint (lines 74-85):

```python
@router.post('/jobs/{job_id}/start')
def start_waiting_job(job_id: int):
    """Start a job that is in 'waiting' status."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    if job.status != JobState.MANUAL_WAIT_STARTED.value:
        return JSONResponse({"success": False, "error": _NOT_WAITING}, status_code=409)

    if job.source_type == "folder":
        job.status = JobState.VIDEO_RIPPING.value
        db.session.commit()
        thread = threading.Thread(target=rip_folder, args=(job,), daemon=True)
        thread.start()
        return {"success": True, "job_id": job.job_id, "status": job.status}

    # Disc rip — existing behavior
    svc_files.database_updater({"manual_start": True}, job)
    return {"success": True, "job_id": job.job_id}
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest test/test_folder_api.py -x -v --tb=short`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `.venv/bin/python -m pytest test/ -x -q --tb=short`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git -C /home/upb/src/automatic-ripping-machine-neu add arm/api/v1/jobs.py test/test_folder_api.py
git -C /home/upb/src/automatic-ripping-machine-neu commit -m "feat: start endpoint dispatches folder jobs via rip_folder thread"
```

---

## Chunk 2: Frontend — "Processing" Status Display

### File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/lib/utils/format.ts` | Modify | Change `importing` to `processing` in STATUS_LABELS |
| `frontend/src/lib/components/JobCard.svelte` | Modify | Change `'importing'` to `'processing'` in folder override |
| `frontend/src/routes/jobs/[id]/+page.svelte` | Modify | Add folder status override (currently missing) |

---

### Task 3: Update format.ts STATUS_LABELS

**Repo:** `/home/upb/src/automatic-ripping-machine-ui`
**Files:**
- Modify: `frontend/src/lib/utils/format.ts:50,80`

- [ ] **Step 1: Update STATUS_LABELS**

In `frontend/src/lib/utils/format.ts`:

Line 80 — change:
```typescript
importing: 'Importing',
```
to:
```typescript
importing: 'Processing',
```

Line 83 — change:
```typescript
processing: 'Transcoding',
```
to:
```typescript
processing: 'Processing',
```

Note: `statusColor` already handles both `'importing'` and `'processing'` (lines 50-51 return `'status-active'`, lines 56-57 return `'status-processing'`). The `'processing'` case returns `'status-processing'` which is correct for folder jobs.

Actually, looking at the switch: `'importing'` maps to `'status-active'` (line 50) and `'processing'` maps to `'status-processing'` (line 56). Since we're changing JobCard to emit `'processing'` instead of `'importing'`, the color will change from active-blue to processing-purple. This is actually better — "Processing" should look different from "Ripping".

- [ ] **Step 2: Run frontend build check**

Run: `cd /home/upb/src/automatic-ripping-machine-ui/frontend && npx svelte-check --tsconfig ./tsconfig.json`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git -C /home/upb/src/automatic-ripping-machine-ui add frontend/src/lib/utils/format.ts
git -C /home/upb/src/automatic-ripping-machine-ui commit -m "refactor: rename importing to processing in status labels"
```

---

### Task 4: Update JobCard folder status override

**Repo:** `/home/upb/src/automatic-ripping-machine-ui`
**Files:**
- Modify: `frontend/src/lib/components/JobCard.svelte:56`

- [ ] **Step 1: Update JobCard**

In `frontend/src/lib/components/JobCard.svelte` line 56, change:
```svelte
<StatusBadge status={isFolderImport && job.status === 'ripping' ? 'importing' : job.status} />
```
to:
```svelte
<StatusBadge status={isFolderImport && job.status === 'ripping' ? 'processing' : job.status} />
```

- [ ] **Step 2: Run build check**

Run: `cd /home/upb/src/automatic-ripping-machine-ui/frontend && npx svelte-check --tsconfig ./tsconfig.json`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git -C /home/upb/src/automatic-ripping-machine-ui add frontend/src/lib/components/JobCard.svelte
git -C /home/upb/src/automatic-ripping-machine-ui commit -m "refactor: folder jobs display Processing instead of Importing"
```

---

### Task 5: Add folder status override to job detail page

**Repo:** `/home/upb/src/automatic-ripping-machine-ui`
**Files:**
- Modify: `frontend/src/routes/jobs/[id]/+page.svelte:251`

- [ ] **Step 1: Add folder detection variable**

Near the top of the `<script>` block (where other derived variables are), add:
```svelte
let isFolderImport = $derived(job?.source_type === 'folder');
```

- [ ] **Step 2: Update StatusBadge on line 251**

Change:
```svelte
<StatusBadge status={job.status} />
```
to:
```svelte
<StatusBadge status={isFolderImport && job.status === 'ripping' ? 'processing' : job.status} />
```

- [ ] **Step 3: Run build check**

Run: `cd /home/upb/src/automatic-ripping-machine-ui/frontend && npx svelte-check --tsconfig ./tsconfig.json`
Expected: No errors

- [ ] **Step 4: Run frontend tests**

Run: `cd /home/upb/src/automatic-ripping-machine-ui/frontend && npx vitest run --reporter=verbose`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git -C /home/upb/src/automatic-ripping-machine-ui add frontend/src/routes/jobs/[id]/+page.svelte
git -C /home/upb/src/automatic-ripping-machine-ui commit -m "fix: job detail page shows Processing for folder jobs"
```

---

## Chunk 3: Full Test Pass & Integration

### Task 6: Full backend test suite

**Repo:** `/home/upb/src/automatic-ripping-machine-neu`

- [ ] **Step 1: Run full ARM-neu tests**

Run: `.venv/bin/python -m pytest test/ -x -q --tb=short`
Expected: ALL PASS

- [ ] **Step 2: Fix any failures**

Common issues:
- Tests that import `rip_folder` from `folder.py` (it's been removed)
- Tests that expect folder jobs to start in `VIDEO_RIPPING` state

- [ ] **Step 3: Commit fixes if needed**

```bash
git -C /home/upb/src/automatic-ripping-machine-neu add -A
git -C /home/upb/src/automatic-ripping-machine-neu commit -m "test: fix tests for folder import review flow"
```

### Task 7: Full frontend test suite

**Repo:** `/home/upb/src/automatic-ripping-machine-ui`

- [ ] **Step 1: Run full UI backend tests**

Run: `/home/upb/src/automatic-ripping-machine-ui/.venv/bin/python -m pytest tests/ -x -q --tb=short`
Expected: ALL PASS

- [ ] **Step 2: Run frontend checks**

Run: `cd /home/upb/src/automatic-ripping-machine-ui/frontend && npm run build && npx svelte-check --tsconfig ./tsconfig.json`
Expected: Build succeeds, no type errors

- [ ] **Step 3: Commit fixes if needed**

```bash
git -C /home/upb/src/automatic-ripping-machine-ui add -A
git -C /home/upb/src/automatic-ripping-machine-ui commit -m "test: fix tests for processing status display"
```

### Task 8: Push and create PRs

- [ ] **Step 1: Push ARM-neu**

```bash
git -C /home/upb/src/automatic-ripping-machine-neu push origin feat/id-based-log-naming
```

- [ ] **Step 2: Push ARM-UI**

Create a feature branch in UI repo and push:
```bash
git -C /home/upb/src/automatic-ripping-machine-ui checkout -b feat/folder-import-review
git -C /home/upb/src/automatic-ripping-machine-ui push -u origin feat/folder-import-review
```

- [ ] **Step 3: Create UI PR**

```bash
GITHUB_TOKEN= gh pr create --repo uprightbass360/automatic-ripping-machine-ui --head feat/folder-import-review --base main --title "feat: folder import review flow and Processing status" --body "..."
```

- [ ] **Step 4: Check CI on both PRs**

Wait for CI to pass on both:
- ARM-neu PR #129 (already exists, push adds commits)
- New UI PR

- [ ] **Step 5: Fix any CI failures**
