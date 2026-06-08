# #1186 — Docker startup fails trying to chown NFS-mounted folders

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1186
**Priority:** Low
**Verdict:** REAL BUG + environmental — mitigated by our docker-compose setup
**Related:** #1622 (permission detection fails)

## Problem

Docker container startup fails when `/home/arm` or subdirectories are NFS-mounted volumes. The `chown` command fails on NFS (permission denied or no-op) and the ownership check then reports a mismatch.

## Upstream Reports

- **Reporter:** Docker with NFS volumes from Synology NAS, ARM_UID=1035, ARM_GID=100
- Error: "ARM does not have permissions to /home/arm using 1035:100 / Folder permissions--> 1035:1000"
- Worked in v2.6, broke in newer versions
- Upstream collaborator asked to test with local volumes to isolate NFS vs ARM issue
- User suggested an environment variable to skip the check

## Root Cause

Same script ordering bug as #1622, compounded by NFS:
1. `check_folder_ownership()` at `scripts/docker/runit/arm_user_files_setup.sh:17-36` uses `stat -c "%u"` / `stat -c "%g"`
2. NFS volumes may not support `chown` and report unexpected ownership via `stat`
3. The check runs before subdirectory fixes are applied

## Our Fork's Mitigations

- Named volumes via docker-compose.yml (not anonymous Docker volumes)
- `arm-db-init` init container handles DB volume ownership
- But `check_folder_ownership()` is still present and vulnerable for NFS users

## Affected Code

- `scripts/docker/runit/arm_user_files_setup.sh:17-36` — `check_folder_ownership()` function
- `scripts/docker/runit/arm_user_files_setup.sh:58-73` — chown/check ordering

## Suggested Fix

Same as #1622 plus NFS-specific handling:
1. Add `chown arm:arm /home/arm 2>/dev/null || true` before the ownership check (silently handle NFS failure)
2. Add `SKIP_OWNERSHIP_CHECK` env var escape hatch
3. Switch to `test -w "$check_dir"` (write access check) instead of numeric UID/GID comparison
