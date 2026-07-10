#!/bin/bash -i

set -eo pipefail

DEVNAME=$1
USER="arm"

#######################################################################################
# Log Discovered Type and Start Rip
# ID_CDROM_MEDIA_BD = Blu-ray
# ID_CDROM_MEDIA_CD = CD
# ID_CDROM_MEDIA_DVD = DVD
#######################################################################################

if [ "$ID_CDROM_MEDIA_DVD" == "1" ]; then
	echo "[ARM] Starting ARM for DVD on ${DEVNAME}" | logger -t ARM -s

elif [ "$ID_CDROM_MEDIA_BD" == "1" ]; then
	echo "[ARM] Starting ARM for Blu-ray on ${DEVNAME}" | logger -t ARM -s

elif [ "$ID_CDROM_MEDIA_CD" == "1" ]; then
	echo "[ARM] Starting ARM for CD on ${DEVNAME}" | logger -t ARM -s

elif [ "$ID_FS_TYPE" != "" ]; then
	echo "[ARM] Starting ARM for Data Disk on ${DEVNAME} with File System ${ID_FS_TYPE}" | logger -t ARM -s

else
	echo "[ARM] Starting ARM for unknown disc type on ${DEVNAME}" | logger -t ARM -s

fi

/bin/su -l -c "echo /usr/bin/python3 /opt/arm/arm/ripper/main.py -d ${DEVNAME} | at now" -s /bin/bash ${USER}

#######################################################################################
# Check to see if the admin page is running, if not, start it
#######################################################################################

if ! pgrep -f "runui.py" > /dev/null; then
	echo "[ARM] ARM Webgui not running; starting it " | logger -t ARM -s
	/bin/su -l -c "/usr/bin/python3 /opt/arm/arm/runui.py  " -s /bin/bash ${USER}
fi
