#!/usr/bin/env bash
# Rescan a single optical drive inside the ARM container.
#
# Called via: docker exec arm-rippers /opt/arm/scripts/docker/rescan_drive.sh sr0
#
# Creates the device node if missing (USB drive re-enumeration),
# then triggers udev for that device only. The existing udev rule
# (51-docker-arm.rules) fires the wrapper script if a disc is present.
#
# This avoids restarting the entire container, which would kill
# in-progress rips on other drives.

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

# --- Create device node if missing ---
if [[ ! -e "/dev/$DEVNAME" ]]; then
    if [[ ! -f "/sys/block/$DEVNAME/dev" ]]; then
        log "ERROR: /sys/block/$DEVNAME/dev not found — kernel does not see this drive"
        exit 1
    fi

    majmin=$(cat "/sys/block/$DEVNAME/dev")
    major=$(echo "$majmin" | cut -d: -f1)
    minor=$(echo "$majmin" | cut -d: -f2)

    mknod -m 0660 "/dev/$DEVNAME" b "$major" "$minor"
    chown root:cdrom "/dev/$DEVNAME"
    log "Created missing device node /dev/$DEVNAME ($major:$minor)"
fi

# --- Trigger udev for this device only ---
# ACTION=change matches the disc-detection rule (51-docker-arm.rules).
# If a disc is present, the rule fires docker_arm_wrapper.sh → main.py.
# If no disc is loaded, udev simply does nothing.
udevadm trigger --action=change --name-match="/dev/$DEVNAME"
udevadm settle --timeout=5

log "Rescan complete for /dev/$DEVNAME"
