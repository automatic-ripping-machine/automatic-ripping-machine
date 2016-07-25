#!/bin/bash
#
# Rip video using MakeMKV then call transcode script
# eject media when transcode script completes

{
	makemkvcon mkv dev:/dev/sr0 all /mnt/media/ARM/raw -r

	/opt/arm/video_transcode.sh
	
	eject


} >> /opt/arm/log
