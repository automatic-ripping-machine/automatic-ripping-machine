# Folder Import Review Flow

**Date:** 2026-03-23
**Status:** Draft
**Repos:** automatic-ripping-machine-neu, automatic-ripping-machine-ui

## Problem

Folder imports currently skip the review step that disc rips go through. The wizard creates a job in `VIDEO_RIPPING` state and immediately launches `rip_folder()` in a background thread. This causes:

- **No review step** — user cannot verify metadata or match episodes before processing begins
- **Wrong status label** — UI shows "Ripping" for folder jobs, but nothing is being ripped from a disc
- **Series broken** — TV series folder imports have no opportunity for TVDB episode matching
- **No abort** — once created, the job starts immediately with no way to review first
- **Stuck jobs** — if the rip fails or hangs, the job stays in "ripping" state with no user recourse

## Design

### Core Change

Folder imports create a job in `MANUAL_WAIT_STARTED` ("waiting") state instead of `VIDEO_RIPPING`. The user reviews metadata on the job detail page and clicks "Start" to begin processing. This is the same flow disc rips use when manual wait is enabled.

### No New Job States

The backend uses `VIDEO_RIPPING` as the actual state when processing starts — no new `VIDEO_PROCESSING` state. The frontend displays **"Processing"** instead of **"Ripping"** when `job.source_type === 'folder'`. This avoids rippling a state change through the ripper, transcoder, webhooks, and job queries.

### Backend Changes (ARM-neu)

#### 1. `arm/api/v1/folder.py` — Create job in MANUAL_WAIT

Current (broken):
```python
job.status = JobState.VIDEO_RIPPING.value
# ... flush, commit ...
thread = threading.Thread(target=rip_folder, args=(job,), daemon=True)
thread.start()
```

New:
```python
job.status = JobState.MANUAL_WAIT_STARTED.value
# ... flush, commit ...
# No background thread — job waits for user to click Start
```

Remove the `threading` import and `rip_folder` import from `folder.py` since it no longer launches the rip directly.

#### 2. `arm/api/v1/jobs.py` — Start endpoint dispatches folder jobs

Current start endpoint only handles disc rips by setting `manual_start=True`:
```python
@router.post('/jobs/{job_id}/start')
def start_waiting_job(job_id: int):
    if job.status != JobState.MANUAL_WAIT_STARTED.value:
        return error
    svc_files.database_updater({"manual_start": True}, job)
```

New: Add folder job dispatch. When the job has `source_type == "folder"`, launch `rip_folder` in a background thread instead of setting the `manual_start` flag:

```python
@router.post('/jobs/{job_id}/start')
def start_waiting_job(job_id: int):
    if job.status != JobState.MANUAL_WAIT_STARTED.value:
        return error

    if job.source_type == "folder":
        job.status = JobState.VIDEO_RIPPING.value
        db.session.commit()
        thread = threading.Thread(target=rip_folder, args=(job,), daemon=True)
        thread.start()
        return {"success": True, "job_id": job.job_id, "status": job.status}
    else:
        # Disc rip — existing behavior
        svc_files.database_updater({"manual_start": True}, job)
        return {"success": True}
```

#### 3. `arm/ripper/folder_ripper.py` — No status changes

`rip_folder()` already sets `VIDEO_RIPPING` during processing and `TRANSCODE_WAITING` on success. No changes needed. The log setup changes from the ID-based naming work are already in place.

#### 4. Source path validation

Validation happens at job creation time only (in `folder.py`). If the folder disappears between creation and start, `rip_folder()` raises `FileNotFoundError` and the job moves to `FAILURE` — this is acceptable.

### Frontend Changes (ARM-UI)

#### 1. Status display — "Processing" for folder jobs

Two places display job status and both need the folder override:

**`JobCard.svelte` (line 56)** — already has a mapping but uses `'importing'`. Change to `'processing'`:
```svelte
<StatusBadge status={isFolderImport && job.status === 'ripping' ? 'processing' : job.status} />
```

**`/jobs/[id]/+page.svelte` (line 251)** — passes `job.status` directly with NO folder override. This is why hifi shows "Ripping" for folder jobs. Add the same override:
```svelte
<StatusBadge status={job.source_type === 'folder' && job.status === 'ripping' ? 'processing' : job.status} />
```

**`format.ts`** — update STATUS_LABELS: change `importing: 'Importing'` to `processing: 'Processing'`. Update `statusColor` to handle `'processing'` (can reuse the same color as `'ripping'`).

This is a display-only change. The actual status value remains `ripping` (`VIDEO_RIPPING`).

#### 2. Job detail page — Start button

The job detail page already shows a "Start" button for jobs in `MANUAL_WAIT_STARTED` state. No changes needed — folder jobs in `waiting` state will automatically get the Start button.

#### 3. Folder import wizard — redirect after creation

The wizard already collects title, year, video_type, imdb_id, poster_url, and multi_title. It calls `POST /api/jobs/folder` which will now create the job in `waiting` state. After creation, the wizard should redirect to the job detail page so the user can review and start.

### What This Enables

Once folder jobs go through the review state:
- **Episode matching works** — the job detail page already has TVDB matching UI for jobs in `waiting` state
- **Metadata review** — user can verify title, year, type before starting
- **Cancel before start** — user can cancel a folder import job before processing begins
- **Consistent UX** — folder imports and disc rips follow the same review → start flow

## Files Affected

### ARM-neu
| File | Change |
|------|--------|
| `arm/api/v1/folder.py` | Set `MANUAL_WAIT_STARTED` status, remove background thread launch, remove threading/rip_folder imports, update docstring |
| `arm/api/v1/jobs.py` | Add folder job dispatch in start endpoint (launch `rip_folder` thread) |
| `test/test_folder_ripper.py` | Update tests (job no longer auto-starts) |

### ARM-UI
| File | Change |
|------|--------|
| `frontend/src/lib/components/JobCard.svelte` | Change `'importing'` to `'processing'` in folder status override |
| `frontend/src/routes/jobs/[id]/+page.svelte` | Add folder status override (currently missing — shows "Ripping" for folder jobs) |
| `frontend/src/lib/utils/format.ts` | Change `importing: 'Importing'` to `processing: 'Processing'` in STATUS_LABELS; update `statusColor` for `'processing'` |

## Testing

### Backend
- Folder import API creates job in `waiting` status (not `ripping`)
- No background thread launched on creation
- Start endpoint with `source_type=folder` launches `rip_folder` thread
- Start endpoint with `source_type=folder` sets status to `ripping`
- Start endpoint rejects non-waiting jobs (existing behavior)
- Disc rip start endpoint unchanged (sets `manual_start=True`)

### Frontend
- JobCard shows "Processing" when `source_type=folder` and status is `ripping`
- JobCard shows "Ripping" when `source_type=disc` and status is `ripping`
- Start button appears for folder jobs in `waiting` state
- Wizard redirects to job detail page after creation

### Integration
- Full flow: wizard → create job → review page → click start → processing → transcode waiting
- Series flow: wizard (video_type=series) → create job → episode matching on review page → start → processing

## Decisions

1. **No new job states** — `VIDEO_PROCESSING` was considered but rejected to avoid rippling changes through backend/transcoder. Frontend handles display.
2. **Validate at creation only** — source folder checked when job is created, not again at start time.
3. **Movies also get review** — all folder imports go through `MANUAL_WAIT`, not just series. Consistent and lets users double-check metadata.
4. **`manual_start` flag not used for folder jobs** — disc rips use `manual_start=True` to signal an already-running ripper thread to proceed. Folder jobs have no running thread in `MANUAL_WAIT` — the start endpoint launches `rip_folder` directly. The `manual_start` flag is irrelevant for folder jobs.
5. **"Processing" not "Importing"** — the UI previously mapped folder ripping to "Importing" in JobCard but this wasn't applied on the job detail page. Changing to "Processing" which better describes what MakeMKV does (extracting/remuxing from disc structure).
