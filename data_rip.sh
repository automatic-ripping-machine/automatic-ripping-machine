#!/bin/bash
# Rip Data using DD

# shellcheck disable=SC1090
# shellcheck disable=SC1091
# shellcheck source=config
source "$ARM_CONFIG"
source "$DISC_INFO"

{

        TIMESTAMP=$(date '+%Y%m%d_%H%M%S');
        DEST="/mnt/media/ARM/Media/Data/${TIMESTAMP}_${ID_FS_LABEL}"
        mkdir -p "$DEST"
	FILENAME=${ID_FS_LABEL}_disc.iso


	#dd if=/dev/sr0 of=$DEST/$FILENAME
	cat "$DEVNAME" > "$DEST/$FILENAME"

	eject "$DEVNAME"

	if [ "$SET_MEDIA_PERMISSIONS" = true ]; then

	chmod -R "$CHMOD_VALUE" "$DEST"

	fi

	if [ "$SET_MEDIA_OWNER" = true ]; then

	chown -R "$CHOWN_USER":"$CHOWN_GROUP" "$DEST"

	fi

} >> "$LOG"
