#!/bin/bash
# Transcodes Video files using HandBrake and removes source files when done


#SRC=/mnt/media/ARM/raw/
SRC=$1
LABEL=$2
TIMESTAMP=$3
DEST_EXT=mkv
HANDBRAKE_CLI=HandBrakeCLI

echo "Start video transcoding script" >> /home/ben/log

	DEST=/mnt/media/ARM/${TIMESTAMP}_${LABEL}
	mkdir $DEST

        for FILE in `ls $SRC`
                do
                filename=$(basename $FILE)
                extension=${filename##*.}
                filename=${filename%.*}
	
		echo "Transcoding file $FILE" >> /opt/arm/log

                $HANDBRAKE_CLI -i $SRC/$FILE -o $DEST/$filename.$DEST_EXT --preset=Normal --subtitle scan -F -E fdk_haac >> /opt/arm/log
		#TIMESTAMP=`date '+%Y_%m_%d__%H_%M_%S'`;
		#mv $SRC/$FILE $SRC/done/$TIMESTAMP.$FILE
		#mv $DEST/$FILE $DEST/done/$FILE
		rm $SRC/$FILE

        	done

