#!/bin/bash
# Transcodes Video files using HandBrake and removes source files when done


SRC=/mnt/media/ARM/raw/
DEST_EXT=mkv
HANDBRAKE_CLI=HandBrakeCLI

echo "Start video transcoding script" >> /home/ben/log

	TIMESTAMP=`date '+%Y%m%d_%H%M%S'`;
	mkdir /mnt/media/ARM/$TIMESTAMP
	DEST=/mnt/media/ARM/$TIMESTAMP

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

