# #1711 — Drive readiness timeout too short

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1711
**Priority:** High
**Verdict:** REAL BUG — we are affected (identical code)
**Related:** #1667 (CDS_ERROR handling)

## Problem

The drive readiness loop in `main.py` waits only 10 seconds (10 iterations x 1s) for `drive.ready` to become `True`. Slow drives, USB optical drives, and discs that trigger kernel I/O recovery can exceed this timeout, causing a fatal error before ripping even starts.

## Upstream Reports

- **Reporter:** ARM 2.22.1 (commit 9850e69), Docker on Ubuntu 22.04.5 LTS (Dell OptiPlex 9020)
- Drive spins up but ARM fires fatal error and ejects before recognition completes
- Docker wrapper log shows **3 rapid invocations** in 30 seconds ("Starting ARM for unknown disc type on sr0" at 17:30:24, 17:30:41, 17:30:53)
- Two additional users confirmed — issue appeared immediately after upgrading to latest release (PR #1696 / commit 9850e69)
- The "unknown disc type" confirms udev environment variables (`ID_CDROM_MEDIA_DVD`, etc.) are not populated yet — the drive truly isn't ready

## Root Cause

Two distinct problems:

**1. 10-second timeout is too short.** `arm/ripper/main.py:181-189` — the retry loop is hardcoded to 10 iterations with 1-second sleep. Optical drives (especially USB-connected or in Docker where udev events are forwarded with delay) can take 15-30+ seconds to go from `CDS.TRAY_OPEN` / `CDS.DRIVE_NOT_READY` to `CDS.DISC_OK`. PR #1696 changed the failure mode from silent `sys.exit()` to `RipperException` that generates user-visible notifications, making the issue more noticeable.

**2. Multiple udev triggers.** The udev rule at `setup/51-docker-arm.rules` fires on `ACTION=="change"` for `sr[0-9]*`, which can trigger multiple times as the kernel re-probes the drive. Each invocation starts its own 10-second timer independently, and each fails, generating separate error notifications. There is no debounce mechanism.

## Affected Code

- `arm/ripper/main.py:181-189` — readiness loop (identical to upstream)
- `arm/models/system_drives.py` — `_tray_status()` (lines 34-87), `ready` property (line 205-207), `CDS` enum
- `setup/51-docker-arm.rules` — udev rule (no debounce)
- `scripts/docker/docker_arm_wrapper.sh` — wrapper invoked by udev (no duplicate guard)

## Suggested Fix

1. **Increase timeout** — make it configurable via arm.yaml (e.g., `DRIVE_READY_TIMEOUT`, default 60s) with exponential backoff or 2-3 second sleeps
2. **Differentiate transient from permanent states** — `CDS.TRAY_OPEN` and `CDS.DRIVE_NOT_READY` are transient (keep waiting); `CDS.NO_DISC` after full timeout means give up; `CDS.ERROR` means drive may be resetting
3. **Add duplicate-trigger guard** — PID lock file or debounce mechanism in `docker_arm_wrapper.sh` to prevent multiple simultaneous ARM invocations for the same device
4. Log the actual CDS state on each iteration for debugging
