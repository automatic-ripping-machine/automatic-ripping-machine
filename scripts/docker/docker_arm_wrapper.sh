#!/bin/bash

DEVNAME=$1
ARMLOG="/home/arm/logs/arm.log"
echo "[ARM] Entering docker wrapper" | logger -t ARM -s
echo "$(date) Entering docker wrapper" >> $ARMLOG

#######################################################################################
# YAML Parser to read Config
#
# From: https://stackoverflow.com/questions/5014632/how-can-i-parse-a-yaml-file-from-a-linux-shell-script
#######################################################################################

function parse_yaml {
   local prefix=$2
   local s='[[:space:]]*' w='[a-zA-Z0-9_]*' fs=$(echo @|tr @ '\034')
   sed -ne "s|^\($s\):|\1|" \
        -e "s|^\($s\)\($w\)$s:$s[\"']\(.*\)[\"']$s\$|\1$fs\2$fs\3|p" \
        -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p"  $1 |
   awk -F$fs '{
      indent = length($1)/2;
      vname[indent] = $2;
      for (i in vname) {if (i > indent) {delete vname[i]}}
      if (length($3) > 0) {
         vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
         printf("%s%s%s=\"%s\"\n", "'$prefix'",vn, $2, $3);
      }
   }'
}
eval $(parse_yaml /etc/arm/config/arm.yaml "CONFIG_")

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
      if [ "$CONFIG_UNIDENTIFIED_EJECT" != "false" ]; then
	    eject "${DEVNAME}"
      fi
	  exit #bail out
fi
cd /home/arm
/usr/bin/python3 /opt/arm/arm/ripper/main.py -d "${DEVNAME}" | logger -t ARM -s
