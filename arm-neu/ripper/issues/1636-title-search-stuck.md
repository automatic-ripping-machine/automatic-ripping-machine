# #1636 — DVDs not ripping after Title Search

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1636
**Priority:** High
**Verdict:** REAL BUG — we are affected (same `sleep_check_process` infinite wait)

## Problem

When a DVD is not found in OMDB and the user uses "Title Search" in the UI to assign correct metadata, the job stays in "waiting" status indefinitely. Other auto-identified discs proceed normally.

## Upstream Reports

- **Reporter:** ARM 2.21.0 with 4 drives, `max_concurrent_transcodes: 2`
- Job enters `sleep_check_process` for `makemkvcon` and never progresses
- On re-insertion (fresh job), the same disc works fine
- The stall only happens after manual Title Search correction

## Root Cause

Race condition in how Title Search interacts with the ripping pipeline, combined with process concurrency throttling:

1. User applies Title Search result via UI API — sets `title_manual`, `hasnicetitle=True`
2. Ripper breaks out of `check_for_wait()` and enters `makemkv()`
3. Inside `makemkv()`, `get_drives()` calls `makemkv_info()` which calls `sleep_check_process("makemkvcon", ...)`
4. If other drives are running MakeMKV (multi-drive setup), the process count stays at or above `max_processes`
5. `sleep_check_process` at `arm/ripper/utils.py:225` has **no timeout** — it loops forever:
   ```python
   while loop_count >= max_processes:
       ...
       time.sleep(random_time)
   ```
6. The penalty sleep in `makemkv_info()`'s `finally` block (lines 609-615) creates cascading delays where all jobs wait for each other

## Affected Code

- `arm/ripper/utils.py:209-239` — `sleep_check_process()` (infinite wait, no timeout)
- `arm/ripper/makemkv.py:548-617` — `makemkv_info()` penalty structure
- `arm/ripper/utils.py:763-805` — `check_for_wait()` (Title Search triggers break)

## Suggested Fix

1. **Add a timeout to `sleep_check_process()`** at `arm/ripper/utils.py:209`:
   ```python
   def sleep_check_process(process_str, max_processes, sleep=(20, 120, 10), timeout=3600):
       ...
       start = time.monotonic()
       while loop_count >= max_processes:
           if time.monotonic() - start > timeout:
               logging.warning(f"sleep_check_process timed out after {timeout}s waiting for {process_str}")
               break
           ...
   ```
2. **Reduce penalty sleep** in `makemkv_info()` at lines 609-615 — use a fixed, shorter penalty (e.g., 10s) instead of `MANUAL_WAIT_TIME`
