#!/bin/bash
# Transcodes Video files using HandBrake and removes source files when done

source /opt/arm/config

SRC=$1
LABEL=$2
TIMESTAMP=$3
TRANSSTART=$(date +%s);

echo "Start video transcoding script" >> $LOG

	DEST=${ARMPATH}/${LABEL}_${TIMESTAMP}
	mkdir $DEST

        for FILE in `ls $SRC`
                do
                filename=$(basename $FILE)
                extension=${filename##*.}
                filename=${filename%.*}
	
		echo "Transcoding file $FILE" >> $LOG

                $HANDBRAKE_CLI -i $SRC/$FILE -o $DEST/$filename.$DEST_EXT --preset="$HB_PRESET" --subtitle scan -F 2>> $LOG
		#TIMESTAMP=`date '+%Y_%m_%d__%H_%M_%S'`;
		#mv $SRC/$FILE $SRC/done/$TIMESTAMP.$FILE
		#mv $DEST/$FILE $DEST/done/$FILE
		rm $SRC/$FILE

       	done

rmdir $SRC

TRANSEND=$(date +%s);
TRANSSEC=$(($TRANSEND-$TRANSSTART));
TRANSTIME="$(($TRANSSEC / 3600)) hours, $((($TRANSSEC / 60) % 60)) minutes and $(($TRANSSEC % 60)) seconds."

echo "STAT: ${ID_FS_LABEL} transcoded in ${TRANSTIME}" >> $LOG

echo /opt/arm/notify.sh "\"Transcode: ${ID_FS_LABEL} completed in ${TRANSTIME}\"" |at now

