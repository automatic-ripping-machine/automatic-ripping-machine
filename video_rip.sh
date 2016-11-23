#!/bin/bash
#
# Rip video using MakeMKV then eject and call transcode script

source /opt/arm/config

{

	echo "Video Title is ${VIDEO_TITLE}"
        echo "Ripping video ${ID_FS_LABEL} from ${DEVNAME}" >> $LOG
	TIMESTAMP=`date '+%Y%m%d_%H%M%S'`;
        DEST=${RAWPATH}/${VIDEO_TITLE}
	RIPSTART=$(date +%s);

	echo "DEST is ${DEST}"

        mkdir $DEST

	if [ $RIPMETHOD = "backup" ] && [ $ID_CDROM_MEDIA_BD = "1" ]; then
		echo "Using backup method of ripping." >> $LOG
		DISC="${DEVNAME: -1}"
		echo "Sending command: "makemkvcon backup --decrypt -r disc:$DISC $DEST/""
		makemkvcon backup --decrypt -r disc:$DISC $DEST/
		eject $DEVNAME
	elif [ $MAINFEATURE = true ] && [ $ID_CDROM_MEDIA_DVD = "1" ] && [ -z $ID_CDROM_MEDIA_BD ]; then
		echo "Media is DVD and Main Feature parameter in config file is true.  Bypassing MakeMKV." >> $LOG

	else
		echo "Using mkv method of ripping." >> $LOG
		makemkvcon mkv dev:$DEVNAME all $DEST --minlength=$MINLENGTH -r
		eject $DEVNAME
	fi

	RIPEND=$(date +%s);
	RIPSEC=$(($RIPEND-$RIPSTART));
	RIPTIME="$(($RIPSEC / 3600)) hours, $((($RIPSEC / 60) % 60)) minutes and $(($RIPSEC % 60)) seconds."

	#eject $DEVNAME

	echo /opt/arm/notify.sh "\"Ripped: ${ID_FS_LABEL} completed from ${DEVNAME} in ${RIPTIME}\"" |at now

	echo "STAT: ${ID_FS_LABEL} ripped in ${RIPTIME}" >> $LOG


	if [ "$GET_TITLE_RESULT" = 0]; then
		echo "got video title from dvdid"
		echo /opt/arm/video_transcode.sh $DEST "${GET_TITLE_OUTPUT}" $TIMESTAMP | batch
	else
		echo "god video title from disc"
		echo /opt/arm/video_transcode.sh $DEST $VIDEO_TITLE $TIMESTAMP | batch
	fi		

	echo "${ID_FS_LABEL} sent to transcoding queue..." >> $LOG



} >> $LOG
