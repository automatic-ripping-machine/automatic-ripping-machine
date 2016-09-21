#!/bin/bash
#
# Rip video using MakeMKV then eject and call transcode script

source /opt/arm/config

{

        echo "Ripping video ${ID_FS_LABEL} from ${DEVNAME}" >> $LOG
	TIMESTAMP=`date '+%Y%m%d_%H%M%S'`;
        DEST=${RAWPATH}/${ID_FS_LABEL}_${TIMESTAMP}
	RIPSTART=$(date +%s);
        mkdir $DEST


	makemkvcon mkv dev:$DEVNAME all $DEST --minlength=$MINLENGTH -r

	RIPEND=$(date +%s);
	RIPSEC=$(($RIPEND-$RIPSTART));
	RIPTIME="$(($RIPSEC / 3600)) hours, $((($RIPSEC / 60) % 60)) minutes and $(($RIPSEC % 60)) seconds."

	eject $DEVNAME

	echo /opt/arm/notify.sh "\"Ripped: ${ID_FS_LABEL} completed from ${DEVNAME} in ${RIPTIME}\"" |at now

	echo "STAT: ${ID_FS_LABEL} ripped in ${RIPTIME}" >> $LOG
	echo /opt/arm/video_transcode.sh $DEST $ID_FS_LABEL $TIMESTAMP | batch

	echo "${ID_FS_LABEL} sent to transcoding queue..." >> $LOG



} >> $LOG
