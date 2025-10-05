#!/bin/bash -i

set -eo pipefail

DEVNAME=$1
PROTECTION=""
USER="arm"

#######################################################################################
# YAML Parser to read Config
#
# From: https://stackoverflow.com/questions/5014632/how-can-i-parse-a-yaml-file-from-a-linux-shell-script
#######################################################################################

function parse_yaml {
   local prefix=$2
   local s='[[:space:]]*'
   local w='[a-zA-Z0-9_]*'
   local fs
   fs=$(echo @ | tr @ '\034')
   sed -ne "s|^\($s\):|\1|" \
        -e "s|^\($s\)\($w\)$s:${s}[\"']\(.*\)[\"']$s\$|\1$fs\2$fs\3|p" \
        -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p"  "$1" |
   awk -F"$fs" '{
      indent = length($1)/2;
      vname[indent] = $2;
      for (i in vname) {if (i > indent) {delete vname[i]}}
      if (length($3) > 0) {
         vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
         printf("%s%s%s=\"%s\"\n", "'"$prefix"'",vn, $2, $3);
      }
   }'
}

eval "$(parse_yaml /etc/arm/config/arm.yaml "CONFIG_")"

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
	echo "[ARM] Not CD, Bluray, DVD or Data. Bailing out on ${DEVNAME}" | logger -t ARM -s
	exit #bail out

fi

/bin/su -l -c "echo /opt/arm/venv/bin/python3 /opt/arm/arm/ripper/main.py -d ${DEVNAME} | at now" -s /bin/bash ${USER}

#######################################################################################
# Check to see if the admin page is running, if not, start it
#######################################################################################

if ! pgrep -f "runui.py" > /dev/null; then
	echo "[ARM] ARM Webgui not running; starting it " | logger -t ARM -s
	/bin/su -l -c "/opt/arm/venv/bin/python3 /opt/arm/arm/runui.py  " -s /bin/bash ${USER}
fi
