#!/bin/bash

DEVNAME=$1
ARMLOG="/home/arm/logs/arm.log"
echo "[ARM] Entering docker wrapper" | logger -t ARM -s
echo "$(date) Entering docker wrapper" >> $ARMLOG

#######################################################################################
# Log Discovered Type and Start Rip
#######################################################################################

# ID_CDROM_MEDIA_BD = Bluray
# ID_CDROM_MEDIA_CD = CD
# ID_CDROM_MEDIA_DVD = DVD
if [ "$ID_CDROM_MEDIA_DVD" == "1" ]; then
    echo "$(date) [ARM] Starting ARM for DVD on ${DEVNAME}" >> $ARMLOG
    echo "[ARM] Starting ARM for DVD on ${DEVNAME}" | logger -t ARM -s
elif [ "$ID_CDROM_MEDIA_BD" == "1" ]; then
	  echo "[ARM] Starting ARM for Bluray on ${DEVNAME}" >> $ARMLOG
	  echo "$(date) [[ARM] Starting ARM for Bluray on ${DEVNAME}" | logger -t ARM -s
elif [ "$ID_CDROM_MEDIA_CD" == "1" ] || [ "$ID_CDROM_MEDIA_CD_R" == "1" ] || [ "$ID_CDROM_MEDIA_CD_RW" == "1" ]; then
	  echo "[ARM] Starting ARM for CD on ${DEVNAME}" | logger -t ARM -s
	  echo "$(date) [[ARM] Starting ARM for CD on ${DEVNAME}" >> $ARMLOG
elif [ "$ID_FS_TYPE" != "" ]; then
	  echo "[ARM] Starting ARM for Data Disk on ${DEVNAME} with File System ${ID_FS_TYPE}" | logger -t ARM -s
	  echo "$(date) [[ARM] Starting ARM for Data Disk on ${DEVNAME} with File System ${ID_FS_TYPE}" >> $ARMLOG
else
	  echo "[ARM] Not CD, Blu-ray, DVD or Data. Bailing out on ${DEVNAME}" | logger -t ARM -s
	  echo "$(date) [ARM] Not CD, Blu-ray, DVD or Data. Bailing out on ${DEVNAME}" >> $ARMLOG
	  exit #bail out
fi
cd /home/arm
/usr/bin/python3 /opt/arm/arm/ripper/main.py -d "${DEVNAME}" | logger -t ARM -s
