#!/bin/bash

DEVNAME=$1

echo "Entering docker wrapper" | logger -t ARM -s

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
    if [ "$CONFIG_PREVENT_99" != "false" ]; then
        numtracks=$(lsdvd /dev/"${DEVNAME}" 2> /dev/null | sed 's/,/ /' | cut -d ' ' -f 2 | grep -E '[0-9]+' | sort -r | head -n 1)
        if [ "$numtracks" == "99" ]; then
            echo "[ARM] ${DEVNAME} has 99 Track Protection. Bailing out and ejecting." | logger -t ARM -s
            eject "${DEVNAME}"
            exit
        fi
    fi
    echo "[ARM] Starting ARM for DVD on ${DEVNAME}" | logger -t ARM -s

elif [ "$ID_CDROM_MEDIA_BD" == "1" ]; then
	  echo "[ARM] Starting ARM for Bluray on ${DEVNAME}" | logger -t ARM -s

elif [ "$ID_CDROM_MEDIA_CD" == "1" ]; then
	  echo "[ARM] Starting ARM for CD on ${DEVNAME}" | logger -t ARM -s

elif [ "$ID_FS_TYPE" != "" ]; then
	  echo "[ARM] Starting ARM for Data Disk on ${DEVNAME} with File System ${ID_FS_TYPE}" | logger -t ARM -s

else
	  echo "[ARM] Not CD, Bluray, DVD or Data. Bailing out on ${DEVNAME}" | logger -t ARM -s
	  exit #bail out

fi

# Change this to docker.com image
DOCKER_IMAGE="shitwolfymakes/automatic-ripping-machine:latest"

CONTAINER_NAME="arm-rippers"
CONTAINER_VOLUME="-v /home/arm:/home/arm -v /etc/arm/config:/etc/arm/config -v /home/arm/Music:/home/arm/Music -v /home/arm/logs:/home/arm/logs -v /home/arm/media:/home/arm/media"
CONTAINER_RESTART="on-failure:3"
ARM_UID="$(id -u arm)"
ARM_GID="$(id -g arm)"

function findGenericDevice {
echo "xxx4" | logger -t ARM -s

    if command -v lsscsi > /dev/null ; then
        SG_DEV="$(lsscsi -g | sed -ne '/\/dev\/sr[0-9]/ s#.*\(/dev/sg[0-9]*\) *#\1#p')"
        echo "xxx5" | logger -t ARM -s

        if [[ -n "${SG_DEV}" ]] ; then
            echo "xxx6" | logger -t ARM -s
            echo "Found generic device for ${DEVNAME}: ${SG_DEV}" | logger -t ARM
            echo "${SG_DEV}"
        fi
    fi
}

function runArmContainer {
    SG_DEV="$(findGenericDevice)"
    if [[ -n "${SG_DEV}" ]] ; then
        echo "xxx7" | logger -t ARM -s
        SG_DEV_ARG="--device=${SG_DEV}:/dev/sg0"
    fi
    echo "Starting on ${DEVNAME} ${SG_DEV}" | logger -t ARM
    echo "yeet ${SG_DEV_ARG}" | logger -t ARM
    # mounting a device in a container requires:
    #    capability: SYS_ADMIN
    #    security option: apparmor:unconfined
    docker run -d \
        -e UID="${ARM_UID}" -e GID="${ARM_GID}" \
        -v "${CONTAINER_VOLUME}" \
        --privileged \
        --restart "${CONTAINER_RESTART}" \
        --name "${CONTAINER_NAME}" \
        "${DOCKER_IMAGE}" \
        | logger -t ARM
}

function startArmContainer {
    echo "Starting stopped container ${CONTAINER_NAME}" | logger -t ARM
    docker start "${CONTAINER_NAME}" | logger -t ARM
}

function startArmRip {
    # get info from udev to pass into the Docker container
    if [[ -z "${!ID_CDROM_MEDIA_*}" ]] ; then
        eval "$(udevadm info --query=env --export "${DEVNAME}")"
    fi
    local disctype="$(echo "${!ID_CDROM_MEDIA_*}" \
        | sed -nE '/.*(ID_CDROM_MEDIA_(BD|DVD|TRACK_COUNT_AUDIO)).*/ s//\1=1/p' )"
    local label_flag="${ID_FS_LABEL:+-l ID_FS_LABEL=${ID_FS_LABEL}}"
    if [[ -z "${disctype}" ]] ; then
        disctype="unknown=1"
    fi
    # This lets us get all of udev perams
    #echo "Starting udev in ${CONTAINER_NAME}" | logger -t ARM
    #docker exec -i -w /home/arm \
        #"${CONTAINER_NAME}" \
        #/bin/bash /etc/init.d/udev start | logger -t ARM
    echo "Starting rip" | logger -t ARM
    echo "trying - docker exec -it \
        -u ${ARM_UID} \
        ${CONTAINER_NAME} \
        python3 /opt/arm/arm/ripper/main.py -d ${DEVNAME}" | logger -t ARM

    sudo docker exec -it \
        -u "${ARM_UID}" \
        "${CONTAINER_NAME}" \
        python3 /opt/arm/arm/ripper/main.py -d "${DEVNAME}" | logger -t ARM
}

# start ARM container, if not running, for WebUI
echo "Checking container status"
container_status="$(docker container ls -l -f name="${CONTAINER_NAME}" --format '{{json .Status}}')"
echo "container '${CONTAINER_NAME}' status: ${container_status}" | logger -t ARM
case "${container_status//\"}" in
    Up*)
        ;;
    Exited*)
        startArmContainer
        ;;
    *)
        runArmContainer
        ;;
esac

# start the rip inside the same container

echo "xxx0" | logger -t ARM -s
startArmRip