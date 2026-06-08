# #1667 — CDS_ERROR prevents rip after kernel recovery

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1667
**Priority:** High
**Verdict:** ENVIRONMENTAL + REAL BUG — we are affected (identical code)
**Related:** #1711 (drive readiness timeout)

## Problem

When the kernel has trouble reading a disc (USB disconnects, I/O errors), the ioctl returns an error state. ARM's `_tray_status()` returns `None` on `OSError`, which maps to `CDS.ERROR`. The readiness loop treats this as "not ready" and times out, even though the kernel may eventually recover and mount the disc. The drive enters a persistent error state from ARM's perspective — the ONLY fix is restarting the Docker container.

## Upstream Reports

- **Reporter:** ARM 2.21.0, Docker on Ubuntu 24.04, ASUS BW-16D1HT via USB
- dmesg shows USB drive repeatedly disconnecting and reconnecting (4 cycles in 10 seconds) with I/O errors
- Kernel eventually recovers and UDF-fs mounts successfully — disc is playable in VLC and rippable manually
- ARM reports `CDS.ERROR` and refuses to process; only a container restart fixes it
- If disc mounts cleanly on first try, ARM works fine
- Zero responses from upstream maintainers

## Root Cause

**Environmental component:** USB drive instability (disconnecting/reconnecting) is a hardware/kernel issue ARM cannot prevent.

**Real bug component — device node re-enumeration:** When the kernel destroys `/dev/sr1` and recreates the drive as `/dev/sr0` during USB reconnect, the `SystemDrives` database row still has `mount='/dev/sr1'`. The ioctl on the old device node returns `None` (CDS.ERROR) forever because the node no longer exists. Only a container restart re-runs `drives_search()` / `drives_update()` which refreshes mount paths.

The critical chain:
1. `_tray_status()` at `arm/models/system_drives.py:82`: `fcntl.ioctl(disk_check, 0x5326, 0)` on stale device node
2. `OSError` caught at line 83-84, returns `None`
3. `tray.setter` at line 197 converts `None` to `CDS.ERROR`
4. `drive.ready` returns `False` (CDS.ERROR != CDS.DISC_OK)
5. Readiness loop exhausts, raises `RipperException`

Additionally, `main.py` line 177 does `SystemDrives.query.filter_by(mount=devpath).one()` — if the device node changed, this throws `NoResultFound` and ARM crashes during setup.

## Affected Code

- `arm/models/system_drives.py` — `CDS` enum (line 31), `_tray_status()` (lines 34-87), `ready` property
- `arm/ripper/main.py:177` — drive lookup by mount path
- `arm/ripper/main.py:181-189` — readiness loop

## Suggested Fix

1. **Drive re-enumeration handling** — when `_tray_status()` gets `FileNotFoundError` or "No such device" for a known mount point, trigger `drives_update()` to refresh all mount paths instead of returning `None`
2. **Fallback in `main.py` setup** — if `SystemDrives.query.filter_by(mount=devpath).one()` raises `NoResultFound`, attempt to re-scan drives before failing
3. **Apply the drive readiness timeout fix from #1711** — a longer timeout also helps since the drive may become ready once the kernel finishes re-probing
