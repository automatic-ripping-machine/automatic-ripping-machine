#!/bin/bash
set -e
function join_by {
  local d=${1-} f=${2-}
  if shift 2; then
    printf %s "$f" "${@/#/$d}"
  fi
}
cores_minus_one=`nproc --ignore=1`
cpu_array=`seq 1 1 $cores_minus_one`
cpu_cores=$(join_by , ${cpu_array})

docker run -d \
    -p "8080:8080" \
    -e TZ="`timedatectl show -p Timezone --value`" \
    -e ARM_UID="`id -u arm`" \
    -e ARM_GID="`id -g arm`" \
    -v "<path_to_arm_user_home_folder>:/home/arm" \
    -v "<path_to_music_folder>:/home/arm/music" \
    -v "<path_to_logs_folder>:/home/arm/logs" \
    -v "<path_to_media_folder>:/home/arm/media" \
    -v "<path_to_config_folder>:/etc/arm/config" \
    --device="/dev/sr0:/dev/sr0" \
    --device="/dev/sr1:/dev/sr1" \
    --device="/dev/sr2:/dev/sr2" \
    --device="/dev/sr3:/dev/sr3" \
    --privileged \
    --restart "always" \
    --name "automatic-ripping-machine" \
    --cpuset-cpus="$cpu_cores" \
    IMAGE_NAME
