# #1298 — Success indicator for data rip that failed with read errors

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1298
**Priority:** High
**Verdict:** REAL BUG — we are affected (same status override in main.py)

## Problem

When a data disc rip fails (`dd` returns I/O error, exit code 1), ARM correctly logs the error but the job status is set to SUCCESS in the UI. The green tick is misleading — the rip actually failed.

## Upstream Reports

- **Reporter:** ARM v2.10.0, Docker — ripping a "dodgy data media" disc
- ARM log correctly shows `ERROR ARM: Data rip failed with code: 1`
- Raw files cleaned up appropriately
- But UI shows green tick (success) instead of red X (failure)

## Root Cause

The `__main__` block in `arm/ripper/main.py` has a `try/except/else` structure where the `else` clause unconditionally sets `job.status = SUCCESS`:

1. `rip_data()` at `arm/ripper/utils.py:363-417` sets `job.status = FAILURE` on `CalledProcessError` but **does not raise** — it returns `False`
2. In `main.py:144-150`, the `False` return triggers a `logging.critical()` but **no exception is raised**
3. The `else` block at `main.py:270-272` runs because no exception occurred:
   ```python
   else:
       if job:
           job.status = JobState.SUCCESS.value
   ```
4. This **overwrites** the `FAILURE` status that `rip_data()` had set

The same bug also affects the music rip path (`rip_music()` returns `False` on failure, no exception raised).

## Affected Code

- `arm/ripper/main.py:144-150` — data rip handling (no exception on failure)
- `arm/ripper/main.py:139-142` — music rip handling (same issue)
- `arm/ripper/main.py:270-272` — `else` clause overwrites status to SUCCESS
- `arm/ripper/utils.py:363-417` — `rip_data()` returns False on failure

## Suggested Fix

Raise `RipperException` on data/music rip failure so the `except` block handles it:

```python
# Data rip (lines 144-150):
elif job.disctype == "data":
    logging.info("Disc identified as data")
    if utils.rip_data(job):
        utils.notify(job, constants.NOTIFY_TITLE, f"Data disc: {job.label} copying complete. ")
    else:
        raise utils.RipperException("Data rip failed. See previous errors.")

# Music rip (lines 139-142) — same pattern:
else:
    raise utils.RipperException("Music rip failed. See previous errors.")
```
