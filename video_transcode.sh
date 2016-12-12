#!/bin/bash
# Transcodes Video files using HandBrake and removes source files when done

# shellcheck source=config
# shellcheck disable=SC1091
source "$ARM_CONFIG"

SRC=$1
LABEL=$2
HAS_NICE_TITLE=$3
VIDEO_TYPE=$4
TIMESTAMP=$5


	TRANSSTART=$(date +%s);
	echo "Start video transcoding script" >> "$LOG"

	if [ "$HAS_NICE_TITLE" = true ]; then
		echo "transcoding with a nice title" >> "$LOG"
		DEST="${ARMPATH}/${LABEL}"
		echo "dest ${DEST} variable created"
		if [ -d "$DEST" ]; then
			echo "directory already exists... adding timestamp" >> "$LOG"
			DEST="${ARMPATH}/${LABEL}_${TIMESTAMP}"
		fi
	else
		echo "transcoding without a nice title" >> "$LOG"
		DEST="${ARMPATH}/${LABEL}_${TIMESTAMP}"
	fi	

	# DEST="${ARMPATH}/${LABEL}_${TIMESTAMP}"
	mkdir "$DEST"
	if [ "$RIPMETHOD" = "backup" ] && [ "$MAINFEATURE" = true ] && [ "$ID_CDROM_MEDIA_BD" = "1" ]; then
		echo "Transcoding BluRay main feature only." >> "$LOG"
		$HANDBRAKE_CLI -i "$SRC" -o "$DEST/$LABEL.$DEST_EXT" --main-feature --preset="$HB_PRESET" --subtitle scan -F 2>> "$LOG"
		rmdir "$SRC"	
	elif [ "$RIPMETHOD" = "backup" ] && [ "$MAINFEATURE" = false ] && [ "$ID_CDROM_MEDIA_BD" = "1" ]; then		
		echo "Transcoding BluRay all titles above minlength." >> "$LOG"
		# This fails, need to figure out how to iterate through all fetures on a backup source
		$HANDBRAKE_CLI -i "$SRC" -o "$DEST/$LABEL.$DEST_EXT" --min-duration "$MINLENGTH" --preset="$HB_PRESET" --subtitle scan -F 2>> "$LOG"		
		rmdir "$SRC"
	elif [ "$MAINFEATURE" = true ] && [ "$ID_CDROM_MEDIA_DVD" = "1" ]; then
		echo "Transcoding DVD main feature only." >> "$LOG"
		# echo "$HANDBRAKE_CLI -i $DEVNAME -o \"${DEST}/${LABEL}.${DEST_EXT}\" --main-feature --preset="${HB_PRESET}" --subtitle scan -F 2" >> $LOG
        $HANDBRAKE_CLI -i "$DEVNAME" -o "${DEST}/${LABEL}.${DEST_EXT}" --main-feature --preset="${HB_PRESET}" --subtitle scan -F 2>> "$LOG"
		# $HANDBRAKE_CLI -i $DEVNAME -o "${DEST}/${LABEL}.${DEST_EXT}" --main-feature --preset="${HB_PRESET}">> $LOG
		eject "$DEVNAME"
	else
		echo "Transcoding all files." >> "$LOG"
		# shellcheck disable=SC2045
	        for FILE in $(ls "$SRC")
                	do
                	filename=$(basename "$FILE")

                	#extension=${filename##*.}
                	filename=${filename%.*}

			echo "Transcoding file $FILE" >> "$LOG"
                	$HANDBRAKE_CLI -i "$SRC/$FILE" -o "$DEST/$filename.$DEST_EXT" --preset="$HB_PRESET" --subtitle scan -F 2>> "$LOG"
			rm "$SRC/$FILE"
       		done
		rmdir "$SRC"
	fi

	if [ "$VIDEO_TYPE" = "movie" ] && [ "$MAINFEATURE" = true ] && [ "$HAS_NICE_TITLE" = true ]; then
	# move the file to the final media directory
        echo "Checing for existing file..." >> "$LOG"
		if [ ! -f "$MEDIA_DIR/$LABEL.$DEST_EXT" ]; then
			echo "No file found.  Moving \"$DEST/$LABEL.$DEST_EXT to $MEDIA_DIR/$LABEL.$DEST_EXT\"" >> "$LOG"
			mv -n "$DEST/$LABEL.$DEST_EXT" "$MEDIA_DIR/$LABEL.$DEST_EXT"

			if [ "$EMBY_REFRESH" = true ]; then
				# signal emby to scan library
				ApiKey="$(curl -s -H "Authorization: MediaBrowser Client=\"$EMBY_CLIENT\", Device=\"$EMBY_DEVICE\", DeviceId=\"$EMBY_DEVICEID\", Version=1.0.0.0, UserId=\"$EMBY_USERID\"" -d "username=$EMBY_USERNAME" -d "password=$EMBY_PASSWORD" "http://$EMBY_SERVER:$EMBY_PORT/users/authenticatebyname?format=json" | python -m json.tool | grep 'AccessToken' | sed 's/\"//g; s/AccessToken://g; s/\,//g; s/ //g')"

				RESPONSE=$(curl -d 'Library' "http://$EMBY_SERVER:$EMBY_PORT/Library/Refresh?api_key=$ApiKey")

				if [ ${#RESPONSE} = 0 ]; then
					# scan was successful
					echo "Emby refresh command sent successfully" >> "$LOG"
				else
					# scan failed
					echo "Emby refresh command failed for some reason.  Probably authentication issues" >> "$LOG"
				fi
			else
				echo "Emby Refresh False.  Skipping library scan" >> "$LOG"
			fi
		else	
			echo "Warning: $MEDIA_DIR/$LABEL.$DEST_EXT File exists! File moving aborted" >> "$LOG"
        fi
    else
        echo "Nothing here..." >> "$LOG"
	fi

rmdir "$SRC" 

TRANSEND=$(date +%s);
TRANSSEC=$((TRANSEND-TRANSSTART));
TRANSTIME="$((TRANSSEC / 3600)) hours, $(((TRANSSEC / 60) % 60)) minutes and $((TRANSSEC % 60)) seconds."

echo "STAT: ${ID_FS_LABEL} transcoded in ${TRANSTIME}" >> "$LOG"

#echo /opt/arm/rename.sh $DEST

echo /opt/arm/notify.sh "\"Transcode: ${ID_FS_LABEL} completed in ${TRANSTIME}\"" |at now
