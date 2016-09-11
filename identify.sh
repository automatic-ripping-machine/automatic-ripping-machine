#!/bin/bash
#
source /opt/arm/config

{
echo "Starting Identify Script..." >> $LOG

#Clean up old log files
FILESFOUND=( $(find $LOGPATH -mtime +$LOGLIFE -type f))
echo "Deleting ${#FILESFOUND[@]} old log files:"${FILESFOUND[@]} >> $LOG
find $LOGPATH -mtime +$LOGLIFE -type f -delete

# Set Home to home folder of user that is setup to run MakeMKV
export HOME="/root/"


if [ $ID_FS_TYPE == "udf" ]; then
	echo "identified video" >> $LOG
	echo "found ${ID_FS_LABEL} on ${DEVNAME}" >> $LOG
	#echo "ripping video" >> $LOG
	/opt/arm/video_rip.sh $LOG

elif (($ID_CDROM_MEDIA_TRACK_COUNT_AUDIO > 0 )); then
	echo "identified audio" >> $LOG
	abcde

elif [ $ID_FS_TYPE == "iso9660" ]; then
	echo "identified data" >> $LOG
	/opt/arm/data_rip.sh $LOG
	eject $DEVNAME
else
	echo "unable to identify" >> $LOG
	echo $ID_CDROM_MEDIA_TRACK_COUNT_AUDIO >> $LOG
	echo $ID_FS_TYPE >> $LOG
	eject $DEVNAME
fi


} >> $LOG
