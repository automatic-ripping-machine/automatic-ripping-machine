#!/bin/bash
# Transcodes Video files using HandBrake and removes source files when done
# shellcheck source=./config.sample

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
		rmdir -rf "$SRC"
	elif [ "$RIPMETHOD" = "backup" ] && [ "$MAINFEATURE" = false ] && [ "$ID_CDROM_MEDIA_BD" = "1" ]; then
		echo "Transcoding BluRay all titles above minlength." >> "$LOG"
		$HANDBRAKE_CLI -i "$SRC" -o "$DEST/$LABEL.$DEST_EXT" --min-duration "$MINLENGTH" --preset="$HB_PRESET" --subtitle scan -F 2>> "$LOG"
		rmdir -rf "$SRC"
	elif [ "$MAINFEATURE" = true ] && [ "$ID_CDROM_MEDIA_DVD" = "1" ]; then
		echo "Transcoding DVD main feature only." >> "$LOG"
		# echo "$HANDBRAKE_CLI -i $DEVNAME -o \"${DEST}/${LABEL}.${DEST_EXT}\" --main-feature --preset="${HB_PRESET}" --subtitle scan -F 2" >> $LOG
        $HANDBRAKE_CLI -i "$DEVNAME" -o "${DEST}/${LABEL}.${DEST_EXT}" --main-feature --preset="${HB_PRESET}" --subtitle scan -F 2>> "$LOG"
		# $HANDBRAKE_CLI -i $DEVNAME -o "${DEST}/${LABEL}.${DEST_EXT}" --main-feature --preset="${HB_PRESET}">> $LOG
		eject "$DEVNAME"
	else
		echo "Transcoding all files." >> "$LOG"
	        for FILE in "$SRC"
                	do
                	filename=$(basename "$FILE")

                	#extension=${filename##*.}
                	filename=${filename%.*}

			echo "Transcoding file $FILE" >> "$LOG"
                	$HANDBRAKE_CLI -i "$FILE" -o "$DEST/$filename.$DEST_EXT" --preset="$HB_PRESET" --subtitle scan -F 2>> "$LOG"
			rm "$FILE"
       		done
		rmdir "$SRC"
	fi

	if [ "$VIDEO_TYPE" = "movie" ] && [ "$MAINFEATURE" = true ] && [ "$HAS_NICE_TITLE" = true ]; then
        echo "checing for existing file" >> "$LOG"
		if [ ! -f "$MEDIA_DIR/$LABEL.$DEST_EXT" ]; then
			echo "No file found.  Moving \"$DEST/$LABEL.$DEST_EXT to $MEDIA_DIR/$LABEL.$DEST_EXT\"" >> "$LOG"
			mv -n "$DEST/$LABEL.$DEST_EXT" "$MEDIA_DIR/$LABEL.$DEST_EXT"
		else	
			echo "Warning: $MEDIA_DIR/$LABEL.$DEST_EXT File exists! File moving aborted" >> "$LOG"
        fi
    else
        echo "Nothing here..." >> "$LOG"
	fi

rmdir -rf "$SRC" 

TRANSEND=$(date +%s);
TRANSSEC=$((TRANSEND-TRANSSTART));
TRANSTIME="$((TRANSSEC / 3600)) hours, $(((TRANSSEC / 60) % 60)) minutes and $((TRANSSEC % 60)) seconds."

echo "STAT: ${ID_FS_LABEL} transcoded in ${TRANSTIME}" >> "$LOG"

#echo /opt/arm/rename.sh $DEST

echo /opt/arm/notify.sh "\"Transcode: ${ID_FS_LABEL} completed in ${TRANSTIME}\"" |at now
