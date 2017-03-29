#!/bin/bash

# This is the primary entry point, so reset the logs
LOG_RESET="true"
export ARM_CONFIG=$1

echo "$ARM_CONFIG"

# shellcheck source=config
# shellcheck disable=SC1091
source "$ARM_CONFIG"

# Create log dir if needed
mkdir -p "$LOGPATH"

echo "${LOG} BEGIN identify.sh" | ts >> "$INFO_LOG"

#shellcheck disable=SC2094
{
# Print out the environment
set >> "$LOG"

# echo all config parameters to logfile
# excludes sensative parameters
# shellcheck disable=SC2129
echo "*** Start config parameters ****" >> "$LOG"
# shellcheck disable=SC2002
cat "$ARM_CONFIG"|sed '/^[#;].*$/d;/^$/d;/if/d;/^ /d;/^else/d;/^fi/d;/KEY=/d;/PASSWORD/d' >> "$LOG"
echo "*** End config parameters ****" >> "$LOG"

echo "Starting Identify Script..." >> "$LOG"

VIDEO_TITLE=""
HAS_NICE_TITLE=""

# Set Home to home folder of user that is setup to run MakeMKV
export HOME="/root/"

# Makemkvcon will determine the name of the disk (ID_FS_LABEL et al). FWiW, this takes a while (30-60s) but
# ID_FS_LABEL is populated almost immediately if checked from another proecess, the there is room for improvement here.
makemkvcon info dev:"${DEVNAME}" -r >> "$LOG"

# Output UDEV info
udevadm info -q env -n "$DEVNAME" >> "$LOG"

# Make sure there is a disk in the drive. If there isn't, do nothing. Note that calling blkid when the disk is ejected
# can cause the drive to uneject
if [ "$ID_CDROM_DVD" != "1" ]; then
    echo "Disc not inserted" >> "$LOG"
else
    # Run blkid to get the ID_FS_TYPE etc information
    eval "$(blkid -o udev -p /dev/sr0 | sed 's/^/export /g')"
fi

if [ "$ID_FS_TYPE" == "udf" ]; then
	echo "identified udf" >> "$LOG"
	echo "found ${ID_FS_LABEL} on ${DEVNAME}" >> "$LOG"

	if [ "$ARM_CHECK_UDF" == true ]; then
		# check to see if this is really a video
		mkdir -p /mnt/"$DEVNAME"
		mount "$DEVNAME" /mnt/"$DEVNAME"
		if [[ -d /mnt/${DEVNAME}/VIDEO_TS || -d /mnt/${DEVNAME}/BDMV ]]; then
			echo "identified udf as video" >> "$LOG"

			if [ "$GET_VIDEO_TITLE" == true ]; then

				GET_TITLE_OUTPUT=$(/opt/arm/getmovietitle.py -p /mnt"${DEVNAME}" 2>&1)
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
				VTYPE=$(/opt/arm/getvideotype.py -t "${VIDEO_TITLE}" 2>&1)

				#handle year mismath if found
				if [[ $VTYPE =~ .*#.* ]]; then
					VIDEO_TYPE=$(echo "$VTYPE" | cut -f1 -d#)
					NEW_YEAR=$(echo "$VTYPE" | cut -f2 -d#)
					echo "VIDEO_TYPE is $VIDEO_TYPE and NEW_YEAR is $NEW_YEAR"
					VIDEO_TITLE="$(echo "$VIDEO_TITLE" | cut -f1 -d\()($NEW_YEAR)" 
					echo "Year mismatch found.  New video title is $VIDEO_TITLE"
				else
					VIDEO_TYPE="$VTYPE"
				fi
			else
				VIDEO_TYPE="unknown"
			fi

			echo "got to here"
			echo "HAS_NICE_TITLE is ${HAS_NICE_TITLE}"
			echo "video title is now ${VIDEO_TITLE}"
			echo "video type is ${VIDEO_TYPE}"

			umount "/mnt/$DEVNAME"

			# Check to see if this file was already ripped. If it was, don't do it again. Fixes accidental infinite
			# ripping loops if a DVD gets reinserted
			LAST_VIDEO_TITLE=$(cat /opt/arm/.last_video_title)
			if [ "$LAST_VIDEO_TITLE" != "$VIDEO_TITLE" ]; then
			    # This is uniqe, so rip then eject
			    /opt/arm/video_rip.sh "$VIDEO_TITLE" "$HAS_NICE_TITLE" "$VIDEO_TYPE" "$LOG"
			    eject "$DEVNAME"
			else
			    # If it's a duplicate, don't eject
			    echo "Skipping duplicate $VIDEO_TITLE" >> "$LOG"
			fi
			# Leave breadcrumb for the next run
			echo "$VIDEO_TITLE" > /opt/arm/.last_video_title
		else
			umount "/mnt/$DEVNAME"
			echo "identified udf as data" >> "$LOG"
			/opt/arm/data_rip.sh
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
	echo "unable to identify" >> "$LOG"
	echo "ID_CDROM_MEDIA_TRACK_COUNT_AUDIO: $ID_CDROM_MEDIA_TRACK_COUNT_AUDIO" >> "$LOG"
	echo "ID_FS_TYPE: $ID_FS_TYPE" >> "$LOG"

    # Note: Don't eject if unable to identify. For DVDs, this runs multiple times
	echo "would have ejected $DEVNAME"
fi

echo "${LOG} END identify.sh" | ts >> "$INFO_LOG"


} >> "$LOG"
