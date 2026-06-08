#!/bin/bash
# One-shot cleanup of orphaned jobs on container startup.
# Runs after arm_user_files_setup.sh, before start_udev.sh (alphabetical order).
# Must NOT block container startup — a failed cleanup is logged and skipped.

echo "[ARM] Cleaning up orphaned jobs from previous run..."

# Remove stale per-device lock files from previous container lifecycle.
# The wrapper script uses flock(2) on /home/arm/.arm_<dev>.lock — the lock
# auto-releases when the process exits, but the file persists on the
# bind-mounted volume. After a container restart (especially SIGKILL or
# power loss), no process holds the lock yet the file's existence can
# confuse flock if file descriptors leaked. Remove them so the next
# udev-triggered wrapper gets a clean lock.
for lockfile in /home/arm/.arm_*.lock; do
    [ -e "$lockfile" ] || continue
    echo "[ARM] Removing stale lock file: $lockfile"
    rm -f "$lockfile"
done

cd /opt/arm

# Run cleanup as the arm user with the same Python environment.
# Errors are caught so the container always boots even if the DB is missing.
if /sbin/setuser arm /bin/python3 -c "
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

import arm.config.config as cfg
from arm.database import db
db.init_engine('sqlite:///' + cfg.arm_config['DBFILE'])

from arm.services.job_cleanup import cleanup_orphaned_jobs
count = cleanup_orphaned_jobs()
if count:
    print(f'[ARM] Cleaned up {count} orphaned job(s)')
else:
    print('[ARM] No orphaned jobs found')
"; then
    echo "[ARM] Orphaned job cleanup complete"
else
    echo "[ARM] WARNING: Orphaned job cleanup failed — continuing startup"
fi
