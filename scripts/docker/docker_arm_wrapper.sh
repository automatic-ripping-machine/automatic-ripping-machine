#!/bin/bash
#
# ARM Docker Wrapper — called by udev via 51-docker-arm.rules
#
# Responsibilities:
#   1. Per-device flock to prevent concurrent ARM runs on the same drive
#   2. Source environment variables (PATH etc. not available from udev)
#   3. Log the detected disc type
#   4. Launch ARM's main.py for the device
#
# The flock also prevents post-eject retriggering: the rip process still
# holds the lock when the eject fires another udev event.

DEVNAME=$1
ARMLOG="/home/arm/logs/arm.log"
LOCKFILE="/home/arm/.arm_${DEVNAME}.lock"

# --- Per-device flock (non-blocking) ---
# Opens the lock file on fd 9 and attempts a non-blocking exclusive lock.
# If another ARM process already holds the lock for this device, exit cleanly.
exec 9>"$LOCKFILE"
if ! flock -n 9; then
    echo "$(date) [ARM] Lock held for ${DEVNAME}, another ARM process is running. Skipping." >> "$ARMLOG"
    exit 0
fi
# Lock acquired — will auto-release when this process exits.

echo "[ARM] Entering docker wrapper" | logger -t ARM -s
echo "$(date) [ARM] Entering docker wrapper for ${DEVNAME}" >> "$ARMLOG"

# --- Source environment (udev doesn't provide PATH) ---
if [[ -f /etc/environment ]]; then
    set -a && source /etc/environment && set +a
fi

#######################################################################################
# Log Discovered Type and Start Rip
#######################################################################################

# ID_CDROM_MEDIA_BD = Blu-ray
# ID_CDROM_MEDIA_CD = CD
# ID_CDROM_MEDIA_DVD = DVD
if [[ "$ID_CDROM_MEDIA_DVD" == "1" ]]; then
    echo "$(date) [ARM] Starting ARM for DVD on ${DEVNAME}" >> "$ARMLOG"
    echo "[ARM] Starting ARM for DVD on ${DEVNAME}" | logger -t ARM -s
elif [[ "$ID_CDROM_MEDIA_BD" == "1" ]]; then
    echo "$(date) [ARM] Starting ARM for Blu-ray on ${DEVNAME}" >> "$ARMLOG"
    echo "[ARM] Starting ARM for Blu-ray on ${DEVNAME}" | logger -t ARM -s
elif [[ "$ID_CDROM_MEDIA_CD" == "1" ]] || [[ "$ID_CDROM_MEDIA_CD_R" == "1" ]] || [[ "$ID_CDROM_MEDIA_CD_RW" == "1" ]]; then
    echo "$(date) [ARM] Starting ARM for CD on ${DEVNAME}" >> "$ARMLOG"
    echo "[ARM] Starting ARM for CD on ${DEVNAME}" | logger -t ARM -s
elif [[ "$ID_FS_TYPE" != "" ]]; then
    echo "$(date) [ARM] Starting ARM for Data Disk on ${DEVNAME} with FS ${ID_FS_TYPE}" >> "$ARMLOG"
    echo "[ARM] Starting ARM for Data Disk on ${DEVNAME} with FS ${ID_FS_TYPE}" | logger -t ARM -s
else
    echo "$(date) [ARM] No recognized disc type on ${DEVNAME}, skipping." >> "$ARMLOG"
    echo "[ARM] No recognized disc type on ${DEVNAME}, skipping." | logger -t ARM -s
    exit 0
fi

cd /home/arm || exit 1
python3 /opt/arm/arm/ripper/main.py -d "${DEVNAME}" | logger -t ARM -s
