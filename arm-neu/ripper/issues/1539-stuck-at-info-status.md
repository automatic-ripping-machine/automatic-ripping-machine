# #1539 — Job stuck at "info" status

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1539
**Priority:** High
**Verdict:** REAL BUG — we are affected (identical code, confirmed across multiple ARM versions)
**Related:** #1545 (MakeMKV does not start)

## Problem

Jobs get permanently stuck at `VIDEO_INFO` status. The UI shows "info" and the job never progresses. The last log entry is typically "Job running in auto mode" with no further output.

## Upstream Reports

- **Original reporter:** ARM 2.18.3 on Ubuntu 24.02 — disc identified but process never starts
- **Confirming user (capymachi):** Detailed logs showing disc mounting, pydvdid errors, successful identification, then "Failed to open disc" from MakeMKV followed by silence
- **Confirming user (Tarcontar):** ARM 2.20.5 with DEBUG logs showing successful Blu-ray identification but truncated before MakeMKV progress
- **One anonymous user:** Confirmed on latest version (2025-08-28)
- Upstream maintainer (1337-server) asked for DEBUG logs but no further action taken

This affects multiple users across different ARM versions (2.18.3, 2.20.5, latest), indicating a long-standing structural issue rather than a regression.

## Root Cause

`arm/ripper/makemkv.py` — the `run()` function spawns `makemkvcon` via `subprocess.Popen` with **no timeout**:

```python
with subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True) as proc:
    for line in proc.stdout:  # blocks forever if makemkvcon hangs
        ...
```

The chain: `makemkv_mkv()` -> `get_track_info()` -> `TrackInfoProcessor.process_messages()` -> `makemkv_info()` -> `run()`. A hang at any point leaves the job stuck at `VIDEO_INFO`.

The `sleep_check_process()` function only gates _entry_ into `run()` (concurrency limiting) — it does not monitor _duration_. Once `makemkvcon` is running, it can hang indefinitely.

## Affected Code

- `arm/ripper/makemkv.py:1259-1303` — `run()` function (subprocess management, no timeout)
- `arm/ripper/makemkv.py:598-617` — `makemkv_info()` generator (sets VIDEO_INFO status)
- `arm/ripper/makemkv.py:537-575` — `sleep_check_process()` (only limits concurrency, not duration)

## Suggested Fix

1. **Add a timeout to `run()`** — use a watchdog timer (separate thread that calls `proc.kill()` after a configurable timeout). Reasonable defaults: 10-15 minutes for `makemkvcon info`, much longer (hours) for `makemkvcon mkv`/`backup`
2. **Add `MAKEMKV_INFO_TIMEOUT` config setting** in arm.yaml so users can tune it
3. **Set job status to `FAILURE` on timeout** with a descriptive error message rather than leaving it stuck at "info"
4. **Consider a heartbeat/progress check** — if `makemkvcon` has not produced stdout for N minutes (e.g., 5 min for info, 15 min for rip), assume it is hung and kill it. This is more robust than a hard timeout because long rips legitimately take hours but should always produce progress output
