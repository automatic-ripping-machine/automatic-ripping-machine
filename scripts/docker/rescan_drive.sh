#!/usr/bin/env bash
# Rescan a single optical drive inside the ARM container.
#
# Called via: docker exec arm-rippers /opt/arm/scripts/docker/rescan_drive.sh sr0
#
# 1. Cleans up stale sibling device nodes from USB re-enumeration
# 2. Creates the device node if missing
# 3. Checks if a disc is actually present (ioctl)
# 4. Checks if ARM is already processing this drive (flock)
# 5. Launches the ARM wrapper directly (no container udev rules needed)

set -euo pipefail

DEVNAME="${1:-}"
ARMLOG="/home/arm/logs/arm.log"

log() {
    local msg="[rescan_drive] $*"
    echo "$(date '+%Y-%m-%d %H:%M:%S') $msg" >> "$ARMLOG"
    logger -t arm-rescan "$*" 2>/dev/null || true
}

# --- Validate argument ---
if [[ -z "$DEVNAME" ]]; then
    echo "Usage: rescan_drive.sh <device>  (e.g. sr0)" >&2
    exit 1
fi

if [[ ! "$DEVNAME" =~ ^sr[0-9]+$ ]]; then
    echo "ERROR: Device must match sr[0-9]+ (e.g. sr0, sr1), got: $DEVNAME" >&2
    exit 1
fi

log "Rescanning /dev/$DEVNAME"

# --- Clean up stale sibling sr* device nodes ---
# After USB re-enumeration the drive may appear under a different name
# (e.g. sr1 → sr0). Remove device nodes whose kernel backing (/sys/block)
# has disappeared so ARM doesn't see phantom drives.
for stale in /dev/sr[0-9]*; do
    [[ -e "$stale" ]] || continue
    stale_name="${stale#/dev/}"
    [[ "$stale_name" == "$DEVNAME" ]] && continue
    if [[ ! -d "/sys/block/$stale_name" ]]; then
        rm -f "$stale"
        log "Removed stale device node $stale (no /sys/block/$stale_name)"
    fi
done

# --- Create device node if missing ---
if [[ ! -e "/dev/$DEVNAME" ]]; then
    if [[ ! -f "/sys/block/$DEVNAME/dev" ]]; then
        # Not an error — during USB re-enumeration the old device name fires
        # an add event before the kernel settles on the new name. Exit 0 so
        # the host-side watcher does NOT fall back to a container restart.
        log "Device /dev/$DEVNAME not in /sys/block — drive not present (yet), skipping"
        exit 0
    fi

    majmin=$(cat "/sys/block/$DEVNAME/dev")
    major=$(echo "$majmin" | cut -d: -f1)
    minor=$(echo "$majmin" | cut -d: -f2)

    mknod -m 0660 "/dev/$DEVNAME" b "$major" "$minor"
    chown root:cdrom "/dev/$DEVNAME"
    log "Created missing device node /dev/$DEVNAME ($major:$minor)"
fi

# --- Check if a disc is present (ioctl) ---
# CDROM_DRIVE_STATUS (0x5326): 1=NO_DISC, 2=TRAY_OPEN, 3=NOT_READY, 4=DISC_OK
DISC_STATUS=$(python3 -c "
import os, fcntl
try:
    fd = os.open('/dev/$DEVNAME', os.O_RDONLY | os.O_NONBLOCK)
    try:
        print(fcntl.ioctl(fd, 0x5326, 0))
    finally:
        os.close(fd)
except:
    print(-1)
" 2>/dev/null || echo "-1")

if [[ "$DISC_STATUS" == "1" || "$DISC_STATUS" == "2" ]]; then
    log "No disc in /dev/$DEVNAME (status=$DISC_STATUS), skipping"
    exit 0
fi

if [[ "$DISC_STATUS" == "-1" ]]; then
    log "Cannot query /dev/$DEVNAME (status=$DISC_STATUS), skipping"
    exit 0
fi

# --- Check if ARM is already processing this drive ---
LOCKFILE="/home/arm/.arm_${DEVNAME}.lock"
if ! flock -n "$LOCKFILE" true 2>/dev/null; then
    log "ARM already running for $DEVNAME (lock held), skipping"
    exit 0
fi

# --- Launch ARM wrapper directly ---
# The wrapper has its own flock, so even if there's a race between our
# check above and the exec below, double-runs are prevented.
log "Disc present (status=$DISC_STATUS), launching ARM wrapper for $DEVNAME"
exec /opt/arm/scripts/docker/docker_arm_wrapper.sh "$DEVNAME"
