#!/bin/bash
#
source /opt/arm/config

# Create log dir if needed
mkdir -p "$LOGPATH"

{
echo "Starting Identify Script..." >> "$LOG"

VIDEO_TITLE=""
HAS_NICE_TITLE=""


#Clean up old log files
FILESFOUND=( $(find "$LOGPATH" -mtime +"$LOGLIFE" -type f))
echo "Deleting ${#FILESFOUND[@]} old log files: ${FILESFOUND[*]}" >> "$LOG"
find "$LOGPATH" -mtime +"$LOGLIFE" -type f -delete

# Set Home to home folder of user that is setup to run MakeMKV
export HOME="/root/"

# Output UDEV info
udevadm info -q env -n "$DEVNAME" >> "$LOG"

if [ "$ID_FS_TYPE" == "udf" ]; then
	echo "identified udf" >> "$LOG"
	echo "found ${ID_FS_LABEL} on ${DEVNAME}" >> "$LOG"

	if [ "$ARM_CHECK_UDF" == true ]; then
		# check to see if this is really a video
		mkdir -p "/mnt/$DEVNAME"
		mount "$DEVNAME" "/mnt/DEVNAME"
		if [[ -d /mnt/${DEVNAME}/VIDEO_TS || -d /mnt/${DEVNAME}/BDMV ]]; then
			echo "identified udf as video" >> "$LOG"

			if [ "$GET_VIDEO_TITLE" == true ]; then

				GET_TITLE_OUTPUT=$(/opt/arm/getmovietitle.py -p "/mnt${DEVNAME}" 2>&1)
				GET_TITLE_RESULT=$?

				if [ $GET_TITLE_RESULT = 0 ]; then
					echo "Obtained Title $GET_TITLE_OUTPUT"
					HAS_NICE_TITLE=true
					VIDEO_TITLE=${GET_TITLE_OUTPUT}
				else
					echo "failed to get title $GET_TITLE_OUTPUT"
					HAS_NICE_TITLE=false
					VIDEO_TITLE=${ID_FS_LABEL} 
				fi

			else
				HAS_NICE_TITLE=false
				VIDEO_TITLE=${ID_FS_LABEL} 
			fi

			if [ $HAS_NICE_TITLE == true ]; then
				VIDEO_TYPE=$(/opt/arm/getvideotype.py -t "${VIDEO_TITLE}" 2>&1)
			else
				VIDEO_TYPE="unknown"
			fi

			echo "got to here"
			echo "HAS_NICE_TITLE is ${HAS_NICE_TITLE}"
			echo "video title is now ${VIDEO_TITLE}"
			echo "video type is ${VIDEO_TYPE}"

			umount "/mnt/$DEVNAME"
			/opt/arm/video_rip.sh "$VIDEO_TITLE" "$HAS_NICE_TITLE" "$VIDEO_TYPE" "$LOG"
		else
			umount "/mnt/$DEVNAME"
			echo "identified udf as data" >> "$LOG"
			/opt/arm/data_rip.sh "$LOG"
			eject "$DEVNAME"

		fi
	else
		echo "ARM_CHECK_UDF is false, assuming udf is video" >> "$LOG"
		/opt/arm/video_rip.sh "$LOG"
	fi	


elif (("$ID_CDROM_MEDIA_TRACK_COUNT_AUDIO" > 0 )); then
	echo "identified audio" >> "$LOG"
	abcde -d "$DEVNAME"

elif [ "$ID_FS_TYPE" == "iso9660" ]; then
	echo "identified data" >> "$LOG"
	/opt/arm/data_rip.sh "$LOG"
	eject "$DEVNAME"
else
	echo "unable to identify"
	echo "$ID_CDROM_MEDIA_TRACK_COUNT_AUDIO" >> "$LOG"
	echo "$ID_FS_TYPE" >> "$LOG"
	eject "$DEVNAME"
fi


} >> "identify-$LOG"
