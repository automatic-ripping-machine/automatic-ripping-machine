#!/bin/bash
#
# Rip Data using DD
source /opt/arm/config

{



        TIMESTAMP=$(date '+%Y%m%d_%H%M%S');
        DEST="/mnt/media/ARM/${TIMESTAMP}_${ID_FS_LABEL}"
        mkdir "$DEST"
	FILENAME=${ID_FS_LABEL}_disc.iso


	#dd if=/dev/sr0 of=$DEST/$FILENAME 
	cat "$DEVNAME" > "$DEST/$FILENAME"

	eject


} >> "$LOG"
