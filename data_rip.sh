#!/bin/bash
#
# Rip Data using DD


{



        TIMESTAMP=`date '+%Y%m%d_%H%M%S'`;
        DEST=/mnt/media/ARM/${TIMESTAMP}_${ID_FS_LABEL}
        mkdir $DEST
	FILENAME=${ID_FS_LABEL}_disc.iso


	#dd if=/dev/sr0 of=$DEST/$FILENAME 
	cat /dev/sr0 > $DEST/$FILENAME

	eject


} >> /opt/arm/log
