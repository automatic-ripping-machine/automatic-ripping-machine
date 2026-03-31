#!/bin/bash

# Poll all /dev/srN devices with cdrom_id every three seconds.
# Skip devices where makemkvcon is actively ripping (dev:/dev/srN in argv).
# The first time a disc is found to be inserted after either script startup
# or a no-disc status, start docker_arm_wrapper.sh in the background.

set -a && source /etc/environment && set +a

declare -A PRESENT

while true; do
    for dev in /dev/sr[0-9]*; do
        [ -b "$dev" ] || continue
        DEVNAME=${dev##*/}

        if pgrep -f "dev:$dev" >/dev/null 2>&1; then
            continue
        fi

        CDROM_INFO=$(/lib/udev/cdrom_id "$dev" 2>/dev/null)
        ID_CDROM_MEDIA=$(echo "$CDROM_INFO" | sed -n 's/^ID_CDROM_MEDIA=//p')

        if [ "$ID_CDROM_MEDIA" != "1" ]; then
            PRESENT[$DEVNAME]=
            continue
        fi

        [ -n "${PRESENT[$DEVNAME]}" ] && continue
        PRESENT[$DEVNAME]=1

        echo "$(date) [disc-monitor] Disc detected on $DEVNAME"
        (
            ID_CDROM_MEDIA_DVD=$(echo "$CDROM_INFO" | sed -n 's/^ID_CDROM_MEDIA_DVD=//p')
            ID_CDROM_MEDIA_BD=$(echo "$CDROM_INFO" | sed -n 's/^ID_CDROM_MEDIA_BD=//p')
            ID_CDROM_MEDIA_CD=$(echo "$CDROM_INFO" | sed -n 's/^ID_CDROM_MEDIA_CD=//p')
            ID_CDROM_MEDIA_CD_R=$(echo "$CDROM_INFO" | sed -n 's/^ID_CDROM_MEDIA_CD_R=//p')
            ID_CDROM_MEDIA_CD_RW=$(echo "$CDROM_INFO" | sed -n 's/^ID_CDROM_MEDIA_CD_RW=//p')
            ID_FS_TYPE=$(echo "$CDROM_INFO" | sed -n 's/^ID_FS_TYPE=//p')
            export ID_CDROM_MEDIA_DVD ID_CDROM_MEDIA_BD ID_CDROM_MEDIA_CD ID_CDROM_MEDIA_CD_R ID_CDROM_MEDIA_CD_RW ID_FS_TYPE
            gosu arm /opt/arm/scripts/docker/docker_arm_wrapper.sh "$DEVNAME"
        ) &
    done
    sleep 3
done
