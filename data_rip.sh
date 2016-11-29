#!/bin/bash
# shellcheck source=config.sample
#
# Rip Data using DD
source "$ARM_CONFIG"

{



        TIMESTAMP=$(date '+%Y%m%d_%H%M%S');
        DEST="/mnt/media/ARM/${TIMESTAMP}_${ID_FS_LABEL}"
        mkdir "$DEST"
	FILENAME=${ID_FS_LABEL}_disc.iso


	#dd if=/dev/sr0 of=$DEST/$FILENAME 
	cat "$DEVNAME" > "$DEST/$FILENAME"

	eject


} >> "$LOG"
