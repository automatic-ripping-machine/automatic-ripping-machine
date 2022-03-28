#!/bin/bash
#
# set up a user and switch to that user

set -euo pipefail

UID="${UID:-1000}"
GID="${GID:-1000}"
export USER=arm
export HOME="/home/${USER}"

echo "creating group [${UID}] with id ${GID}"
groupadd -fo -g "${GID}" "${USER}"
if ! id -u "${USER}" ; then
    echo "creating user [${USER}] with id ${UID}"
    useradd --shell /bin/bash \
        -u "${UID}" -g "${GID}" -G video,cdrom \
        -o -c "" "${USER}"
    chown -R "${USER}:${USER}" "${HOME}"
fi

# setup needed/expected dirs if not found
SUBDIRS="media media/completed media/raw media/movies logs db Music .MakeMKV"
for dir in $SUBDIRS ; do
    thisDir="${HOME}/${dir}"
    if [[ ! -d "${thisDir}" ]] ; then
        echo "creating dir ${thisDir}"
        mkdir -p 0777 "${thisDir}"
        chown -R "${USER}:${USER}" "${thisDir}"
    fi
done

# setup config files if not found
mkdir -p /etc/config
CONFS="arm.yaml apprise.yaml .abcde.conf"
for conf in $CONFS; do
    thisConf="/etc/config/${conf}"
    if [[ ! -f "${thisConf}" ]] ; then
        echo "creating config file ${thisConf}"
        cp "/opt/arm/setup/${thisConf}" "/etc/config/${thisConf}"
    fi
done
chown -R "${USER}:${USER}" /etc/config/

[[ -h /dev/cdrom ]] || ln -sv /dev/sr0 /dev/cdrom 

if ! [[ -z $(service rsyslog status | grep "not running") ]] ; then
    echo "Starting rsyslog service..."
    service rsyslog start
fi

if [[ "${RUN_AS_USER:-true}" == "true" ]] ; then
    exec /usr/sbin/gosu arm "$@"
else
    exec "$@"
fi

