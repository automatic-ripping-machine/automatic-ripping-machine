#!/bin/bash
#
# Rip video using MakeMKV then eject and call transcode script

{

        TIMESTAMP=`date '+%Y%m%d_%H%M%S'`;
        DEST=/mnt/media/ARM/raw/${TIMESTAMP}_${ID_FS_LABEL}
        mkdir $DEST


	makemkvcon mkv dev:/dev/sr0 all $DEST -r

	eject

	echo /opt/arm/video_transcode.sh $DEST $ID_FS_LABEL $TIMESTAMP | batch
	


} >> /opt/arm/log
