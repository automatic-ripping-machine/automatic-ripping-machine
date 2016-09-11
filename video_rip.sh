#!/bin/bash
#
# Rip video using MakeMKV then eject and call transcode script

source /opt/arm/config

{

        echo "Ripping video ${ID_FS_LABEL} from ${DEVNAME}" >> $LOG
	TIMESTAMP=`date '+%Y%m%d_%H%M%S'`;
        DEST=${RAWPATH}/${ID_FS_LABEL}_${TIMESTAMP}
        mkdir $DEST


	makemkvcon mkv dev:$DEVNAME all $DEST --minlength=$MINLENGTH -r

	eject $DEVNAME

	echo /opt/arm/notify.sh "\"Ripped: ${ID_FS_LABEL} completed from ${DEVNAME}\"" |at now

	echo /opt/arm/video_transcode.sh $DEST $ID_FS_LABEL $TIMESTAMP | batch


} >> $LOG
