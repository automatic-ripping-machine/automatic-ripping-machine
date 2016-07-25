#!/bin/bash
#
# Rip Data using DD


{

        TIMESTAMP=`date '+%Y%m%d_%H%M%S'`;
        mkdir /mnt/media/ARM/$TIMESTAMP
        DEST=/mnt/media/ARM/$TIMESTAMP
	FILENAME=${ID_FS_LABEL}_disc.iso


	#dd if=/dev/sr0 of=$DEST/$FILENAME 
	echo "Filename"
	echo $FILENAME
	cat /dev/sr0 > $DEST/$FILENAME

	eject


} >> /opt/arm/log
