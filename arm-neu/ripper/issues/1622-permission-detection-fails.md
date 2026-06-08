# #1622 — Permission detection fails on overlay/NFS filesystems

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1622
**Priority:** Medium
**Verdict:** REAL BUG (low severity for us) — script ordering bug, mitigated by our docker-compose setup

## Problem

The Docker startup script fails to detect permissions correctly. The ownership check reports wrong UID/GID, causing ARM to log warnings or refuse to start.

## Upstream Reports

- **Reporter:** Ubuntu 22.04 desktop, Docker, ARM_UID=1004, ARM_GID=1005
- `stat -c "%g"` correctly returns `1005` when run manually, but `check_folder_ownership()` reports GID as `1000`
- When GID changed to `1000` to bypass, the next check on `/etc/arm/config` also fails, reporting `0:0` despite directory being owned by `1004:1005`
- `.MakeMKV` inside `/home/arm` was owned by root, not arm
- Upstream collaborator (microtechno9000) suggested recursive `chown` but did not identify root cause

## Root Cause

**Script ordering bug** in `scripts/docker/runit/arm_user_files_setup.sh`:

1. Lines 39-53: `usermod -u $ARM_UID arm` and `groupmod -og $ARM_GID arm` change the arm user/group IDs
2. Line 58: `chown -R arm:arm /opt/arm` — uses new UID/GID
3. Line 61: **`check_folder_ownership "/home/arm"` — checks ownership BEFORE subdirectory fixes** (lines 64-73 handle subdirs AFTER the check)

The check runs before the fix. Additionally, `groupmod -og` uses the `-o` flag (non-unique GIDs), and Docker anonymous volumes retain ownership from creation time (root:root or 1000:1000 from the image layer).

The `stat` command itself works correctly — the issue is **when** the check runs relative to the chown operations.

## Our Fork's Mitigations

1. **Named volumes via docker-compose.yml** — we use named volumes and bind mounts with explicit paths, not anonymous Docker volumes
2. **arm-db-init init container** — runs `chown -R ${ARM_UID}:${ARM_GID} /data/db` before ARM starts (handles DB volume, but not `/home/arm`)

The `check_folder_ownership()` function is still vulnerable if someone uses our image directly (not via docker-compose).

## Affected Code

- `scripts/docker/runit/arm_user_files_setup.sh:17-36` — `check_folder_ownership()` function
- `scripts/docker/runit/arm_user_files_setup.sh:58-73` — chown/check ordering

## Suggested Fix

- Move `chown arm:arm /home/arm` BEFORE `check_folder_ownership "/home/arm"` (add after line 58)
- Or switch `check_folder_ownership()` to use `test -w "$check_dir"` (write access check) instead of numeric ownership comparison
- Add a `SKIP_OWNERSHIP_CHECK` env var escape hatch for NFS/CIFS users
