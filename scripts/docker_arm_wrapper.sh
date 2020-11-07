#!/bin/bash -x
#
#
set -euo pipefail

DOCKER_NAME=arm
DOCKER_IMAGE=arm:latest
DOCKER_VOLUME="/srv/docker/arm:/home/arm"
DOCKER_RESTART="on-failure:3"
ARM_UID="$(id -u plex)"
ARM_GID="$(id -g plex)"

# only run as root
if [[ "$(id -u)" -ne 0 ]] ; then
  echo "$(basename -- "$0") must be run as root" | logger -t ARM -s
  exit 2
fi

# fork to let udev keep running
if [[ "${1:-}" != "fork" ]] ; then
  #{ "$0" fork "$*" > /dev/null 2>&1 < /dev/null & } &
  { "$0" fork "$*" >> /tmp/arm.log 2>&1 < /dev/null & } &
  exit 0
else
  # get rid of "fork" arg
  shift
fi

# TODO handle "/dev/sr0" vs "sr0"
DEVNAME="$1"
if [[ -z "${DEVNAME}" || ! -b "${DEVNAME}" ]] ; then
  echo "Device '${DEVNAME}' not found" | logger -t ARM -s
  exit 1
fi

function findGenericDevice {
  if command -v lsscsi > /dev/null ; then
    SG_DEV="$(lsscsi -g | sed -ne '/\/dev\/sr[0-9]/ s#.*\(/dev/sg[0-9]*\) *#\1#p')"
    if [[ -n "${SG_DEV}" ]] ; then
      echo "Found generic device for ${DEVNAME}: ${SG_DEV}" | logger -t ARM
      echo "${SG_DEV}"
    fi
  fi
}

function runArmContainer {
  SG_DEV="$(findGenericDevice)"
  if [[ -n "${SG_DEV}" ]] ; then
    SG_DEV_ARG="--device=${SG_DEV}:/dev/sg0"
  fi
  echo "Starting on ${DEVNAME} ${SG_DEV}" | logger -t ARM
  # mounting a device in a container requires:
  #  capability: SYS_ADMIN
  #  security option: apparmor:unconfined
  docker run -d \
    --device="${DEVNAME}:/dev/sr0" ${SG_DEV_ARG} \
    -e UID="${ARM_UID}" -e GID="${ARM_GID}" \
    -v "${DOCKER_VOLUME}" \
    --cap-add SYS_ADMIN \
    --security-opt apparmor:unconfined \
    --restart "${DOCKER_RESTART}" \
    --name "${DOCKER_NAME}" \
    "${DOCKER_IMAGE}" \
    | logger -t ARM
}

function startArmContainer {
  echo "Starting stopped container ${DOCKER_NAME}" | logger -t ARM
  docker start "${DOCKER_NAME}" | logger -t ARM
}

function startArmRip {
  echo "Starting rip" | logger -t ARM
  docker exec \
    -u "${ARM_UID}" \
    -w /home/arm \
    "${DOCKER_NAME}" \
    python3 /opt/arm/arm/ripper/main.py -d sr0 \
    | logger -t ARM
}

# start ARM container, if not running, for WebUI
container_status="$(docker container ls -l -f name="${DOCKER_NAME}" --format '{{json .Status}}')"
case "${container_status//\"}" in
  Up*)
    echo "container '${DOCKER_NAME}' status: ${container_status}" | logger -t ARM
    ;;
  Exited*)
    startArmContainer
    ;;
  *)
    runArmContainer
    ;;  
esac

echo "Sleeping while disc spins up" | logger -t ARM
sleep 5 # allow the system enough time to load disc information such as title

startArmRip
