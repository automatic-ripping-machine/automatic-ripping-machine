#!/bin/bash
#
#
set -euo pipefail
# Change this to docker.com image
DOCKER_IMAGE="arm-combined:latest"

CONTAINER_NAME="arm-rippers"
CONTAINER_VOLUME="-v /home/arm:/home/arm -v /home/arm/config:/home/arm/config -v /home/arm/Music:/home/arm/Music -v /home/arm/logs:/home/arm/logs -v /home/arm/media:/home/arm/media"
CONTAINER_RESTART="on-failure:3"
ARM_UID="$(id -u arm)"
ARM_GID="$(id -g arm)"

sleep 5 # allow the system enough time to load disc information such as title

echo "Entering docker wrapper" | logger -t ARM -s

# exit if udev ID_CDROM_MEDIA properties not available yet
# avoid running too early
if [[ -z "${!ID_CDROM_MEDIA_*}" ]] ; then
  echo "No ID_s" | logger -t ARM -s
  # echo "$(date) disk not ready/identified yet" >> /tmp/docker_arm_wrapper.log
echo "xxx" | logger -t ARM -s

  exit 0
fi

# fork to let udev keep running
if [[ "${1:-}" != "fork" ]] ; then
  #{ "$0" fork "$*" > /dev/null 2>&1 < /dev/null & } &
  echo "$0 xxx1 $@" | logger -t ARM -s
  #echo "$0 fork $@" | at -M now # systemd udev hates children
  #exit 0
else
  # get rid of "fork" arg
  shift
fi

DEVNAME="$1"
if [[ -z "${DEVNAME}" ]] ; then
echo "xxx2" | logger -t ARM -s

  echo "Usage: $(basename -- "$0") <device>" | logger -t ARM -s
  echo "devname messed up" | logger -t ARM -s
  exit 1
fi
if [[ ! -b "${DEVNAME}" && -b "/dev/${DEVNAME}" ]] ; then
echo "xxx3" | logger -t ARM -s

  echo "fixing devname" | logger -t ARM -s
  DEVNAME="/dev/${DEVNAME}"
fi

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
  #  capability: SYS_ADMIN
  #  security option: apparmor:unconfined
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
  local disctype="$(echo ${!ID_CDROM_MEDIA_*} \
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
  echo "trying - docker exec -i -u ${ARM_UID} \
    -w /home/arm \
    ${CONTAINER_NAME} \
    python3 /opt/arm/arm/ripper/main.py \
      -d ${DEVNAME} -t ${disctype} ${label_flag} " | logger -t ARM
  docker exec -i \
    -u "${ARM_UID}" \
    -w /home/arm \
    "${CONTAINER_NAME}" \
    python3 /opt/arm/arm/ripper/main.py \
      -d ${DEVNAME} -t ${disctype} ${label_flag} \
    | logger -t ARM
}

# start ARM container, if not running, for WebUI
container_status="$(docker container ls -l -f name="${CONTAINER_NAME}" --format '{{json .Status}}')"
case "${container_status//\"}" in
  Up*)
    echo "container '${CONTAINER_NAME}' status: ${container_status}" | logger -t ARM
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

