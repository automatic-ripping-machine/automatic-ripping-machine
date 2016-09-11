#!/bin/bash
# Transcodes Video files using HandBrake and removes source files when done

source /opt/arm/config
#SRC=/mnt/media/ARM/raw/
SRC=$1
LABEL=$2
TIMESTAMP=$3
#LOG=$4
#DEST_EXT=mkv
#HANDBRAKE_CLI=HandBrakeCLI
#HB_PRESET="Normal"
#HB_PRESET="High Profile"

echo "Start video transcoding script" >> $LOG

	DEST=${ARMPATH}/${LABEL}_${TIMESTAMP}
	mkdir $DEST

        for FILE in `ls $SRC`
                do
                filename=$(basename $FILE)
                extension=${filename##*.}
                filename=${filename%.*}
	
		echo "Transcoding file $FILE" >> $LOG

                $HANDBRAKE_CLI -i $SRC/$FILE -o $DEST/$filename.$DEST_EXT --preset="$HB_PRESET" --subtitle scan -F 2> $LOG
		#TIMESTAMP=`date '+%Y_%m_%d__%H_%M_%S'`;
		#mv $SRC/$FILE $SRC/done/$TIMESTAMP.$FILE
		#mv $DEST/$FILE $DEST/done/$FILE
		rm $SRC/$FILE

       	done

rmdir $SRC

echo /opt/arm/notify.sh "\"Transcode: ${ID_FS_LABEl} complete.\"" |at now

