#!/usr/bin/env bash
# ARM Drive Watcher — host-side script triggered by udev on USB drive ADD events.
#
# USB optical drives (e.g. Pioneer BDR-S12JX) fire continuous ADD events
# due to bus resets during spin-up.  This script rate-limits and only
# triggers a rescan inside the ARM container when a disc is actually present
# and ARM isn't already processing it.
#
# Install:
#   sudo cp scripts/host/arm-drive-watcher.sh /usr/local/bin/
#   sudo chmod +x /usr/local/bin/arm-drive-watcher.sh
#   sudo cp setup/99-arm-drive-watcher.rules /etc/udev/rules.d/
#   sudo udevadm control --reload-rules

set -euo pipefail

DEVNAME="${1:-sr0}"
CONTAINER="${2:-arm-rippers}"
COOLDOWN=120  # seconds between rescan attempts per device

log() {
    logger -t arm-drive-watcher "$*" 2>/dev/null || true
}

# --- Rate limit per device ---
STATE_FILE="/run/arm-drive-watcher-${DEVNAME}.state"
NOW=$(date +%s)
if [[ -f "$STATE_FILE" ]]; then
    LAST=$(cat "$STATE_FILE" 2>/dev/null || echo 0)
    ELAPSED=$((NOW - LAST))
    if (( ELAPSED < COOLDOWN )); then
        exit 0  # silent — don't spam journal during USB bus resets
    fi
fi
echo "$NOW" > "$STATE_FILE"

# --- Check container is running ---
if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -q true; then
    log "Container $CONTAINER not running, skipping"
    exit 0
fi

# --- Check if ARM is already processing this device ---
if ! docker exec "$CONTAINER" flock -n "/home/arm/.arm_${DEVNAME}.lock" true 2>/dev/null; then
    log "ARM already processing $DEVNAME, skipping"
    exit 0
fi

# --- Check if a disc is present (ioctl inside container) ---
# CDROM_DRIVE_STATUS: 1=NO_DISC, 2=TRAY_OPEN, 3=NOT_READY, 4=DISC_OK
DISC_STATUS=$(docker exec "$CONTAINER" python3 -c "
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

if [[ "$DISC_STATUS" != "3" && "$DISC_STATUS" != "4" ]]; then
    log "No disc in $DEVNAME (status=$DISC_STATUS), skipping"
    exit 0
fi

# --- Trigger rescan inside container ---
log "Disc present in $DEVNAME (status=$DISC_STATUS), triggering rescan"
docker exec -d "$CONTAINER" /opt/arm/scripts/docker/rescan_drive.sh "$DEVNAME"
