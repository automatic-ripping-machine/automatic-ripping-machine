# #1559 — Debian Trixie upgrade breaks drive recognition

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1559
**Priority:** Medium
**Verdict:** ENVIRONMENTAL — partially mitigated in our fork (we have `/dev/sr*` regex fallback upstream lacks)

## Problem

Upgrading the host OS to Debian Trixie (13) causes optical drives to no longer be recognized by ARM. Drives show as "not available" in the UI and udev events don't trigger ripping.

## Upstream Reports

- **Reporter:** ARM v2.18.4 on Debian Trixie (13/testing)
- Drives found in DB from prior run but marked "not available" — pyudev cannot see properties inside container
- Logs: `Drive 'ASUS_BW-16D1HT_KLCO82B5029' on '' is not available.`
- **martinnj:** Identified root cause as "incomplete udev population inside the container" — proposed mounting `/run/udev:/run/udev:ro` and `/dev/disk:/dev/disk:ro`
- **OrioleNix:** Workaround did NOT fix the issue
- **dylexrocks:** Confirmed on Debian 13, udev workaround enabled detection but caused 100% CPU for 15 minutes during startup
- Upstream merged PR #1592 (allow drives with unpopulated ID tags)

## Root Cause

Docker containers rely on the host's udev database to populate device properties inside the container. Debian Trixie changed something in udev (likely systemd-udevd version bump or cgroup v2 enforcement) that prevents the host's udev database from being accessible inside the container.

When `pyudev.Context().list_devices(subsystem="block")` runs inside the container, it can see block devices (nodes exist) but cannot read their udev properties (`ID_TYPE`, `ID_CDROM`, etc.).

## Our Fork's Mitigations

Our fork has **better resilience** than upstream due to three factors:

1. **`drives_search()` fallback** — our `is_optical` check includes `re.match(r"^/dev/sr\d+$", devnode)` as a third condition. If the device node matches `/dev/sr*`, it's detected as optical even without udev properties. Upstream did not have this.

2. **`start_udev.sh` device node creation** — actively creates missing device nodes by reading `/proc/sys/dev/cdrom/info` and using `mknod`. Handles cases where the container's devtmpfs lacks the device node.

3. **Startup retry logic** — our `drives.py` retries drive detection up to 3 times at startup with increasing delays (5s, 10s, 15s), giving udev time to settle.

4. **`privileged: true`** in our docker-compose.yml gives the container full `/dev` access, avoiding many device passthrough issues.

**Remaining exposure:** The `docker_arm_wrapper.sh` still relies on udev environment variables (`$ID_CDROM_MEDIA_DVD`, etc.) which may be empty on Trixie — but this only affects logging labels (lines 19-34), not actual ripping functionality, since the wrapper unconditionally calls `python3 /opt/arm/arm/ripper/main.py -d "${DEVNAME}"`.

## Affected Code

- `scripts/docker/runit/start_udev.sh` — udev initialization + device node creation
- `arm/services/drives.py` — `drives_search()` with `/dev/sr*` fallback
- `scripts/docker/docker_arm_wrapper.sh` — wrapper invoked by udev

## Suggested Fix

No immediate code change required. Our fork already handles the main failure mode. Consider:
- Adding `/run/udev:/run/udev:ro` to docker-compose volumes as optional for Trixie hosts
- Documenting minimum host OS requirements
- Monitoring upstream Trixie discussion for definitive fix
