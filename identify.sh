#!/bin/bash
#
{
echo "Starting Identify Script..." >> /opt/arm/log

# Set Home to home folder of user that is setup to run MakeMKV
export HOME="/root/"


if [ $ID_FS_TYPE == "udf" ]; then
	echo "identified video" >> /opt/arm/log
	echo "ripping video" >> /opt/arm/log
	/opt/arm/video_rip.sh


elif [ $ID_FS_TYPE == "iso9660" ]; then
	echo "identified data" >> /opt/arm/log
	/opt/arm/data_rip.sh
	eject
elif (($ID_CDROM_MEDIA_TRACK_COUNT_AUDIO > 0 )); then
	echo "identified audio" >> /opt/arm/log
	abcde
else
	echo "unable to identify" >> /opt/arm/log
	echo $ID_CDROM_MEDIA_TRACK_COUNT_AUDIO >> /opt/arm/log
	echo $ID_FS_TYPE >> /opt/arm/log
	eject
fi


} >> /opt/arm/log
