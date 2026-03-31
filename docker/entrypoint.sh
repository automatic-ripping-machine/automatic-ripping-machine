#!/bin/bash
set -euo pipefail

ARM_HOME="/home/arm"
DEFAULT_UID=1000
DEFAULT_GID=1000

check_folder_ownership() {
    local check_dir folder_uid folder_gid
    check_dir="$1"
    folder_uid=$(stat -c "%u" "$check_dir")
    folder_gid=$(stat -c "%g" "$check_dir")
    if [ "$folder_uid" != "$ARM_UID" ] || [ "$folder_gid" != "$ARM_GID" ]; then
        echo "[ERROR]: ARM does not have permissions to $check_dir using $ARM_UID:$ARM_GID"
        echo "Folder permissions: $folder_uid:$folder_gid"
        exit 1
    fi
}

if [[ $ARM_UID -ne $DEFAULT_UID ]]; then
    usermod -u "$ARM_UID" arm
fi
if [[ $ARM_GID -ne $DEFAULT_GID ]]; then
    groupmod -og "$ARM_GID" arm
fi
# Match the render group GID to the actual device GID so arm can access the GPU
if [ -e /dev/dri/renderD128 ]; then
    RENDER_GID=$(stat -c "%g" /dev/dri/renderD128)
    if ! getent group "$RENDER_GID" >/dev/null 2>&1; then
        groupmod -g "$RENDER_GID" render
    fi
    usermod -a -G "$RENDER_GID" arm
fi
usermod -a -G render arm

chown -R arm:arm /opt/arm
check_folder_ownership "/home/arm"

for dir in media media/completed media/raw media/movies media/transcode logs logs/progress db music .MakeMKV; do
    thisDir="$ARM_HOME/$dir"
    if [[ ! -d "$thisDir" ]]; then
        mkdir -p "$thisDir"
        chown -R arm:arm "$thisDir"
    fi
done

[ -h /home/arm/Music ] && unlink /home/arm/Music

mkdir -p /etc/arm/config
for conf in arm.yaml apprise.yaml; do
    thisConf="/etc/arm/config/${conf}"
    if [[ ! -f "${thisConf}" ]]; then
        cp --no-clobber "/opt/arm/setup/${conf}" "${thisConf}"
    fi
done

[ -h /etc/arm/config/abcde.conf ] && unlink /etc/arm/config/abcde.conf
[ ! -f /etc/arm/config/abcde.conf ] && cp /opt/arm/setup/.abcde.conf /etc/arm/config/abcde.conf
[ ! -h /etc/abcde.conf ] && ln -sf /etc/arm/config/abcde.conf /etc/abcde.conf

ln -sf /usr/share/zoneinfo/"$TZ" /etc/localtime
DEBIAN_FRONTEND=noninteractive dpkg-reconfigure --frontend noninteractive tzdata 2>/dev/null || true

env > /etc/environment
chmod 0600 /etc/environment

exec runsvdir /etc/service
