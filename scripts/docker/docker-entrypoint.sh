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
    chown "${USER}.${USER}" "${HOME}"
fi

# setup needed/expected dirs if not found
SUBDIRS="config media media/completed media/raw media/movies logs db Music .MakeMKV"
for dir in $SUBDIRS ; do
    thisDir="${HOME}/${dir}"
    if [[ ! -d "${thisDir}" ]] ; then
        echo "creating dir ${thisDir}"
        mkdir -p -m 0777 "${thisDir}"
        chown -R "${USER}.${USER}" "${thisDir}"
    fi
done
if [[ ! -f "${HOME}/config/arm.yaml" ]] ; then
    echo "creating example ARM config ${HOME}/config/arm.yaml"
    cp /opt/arm/docs/arm.yaml.sample "${HOME}/config/arm.yaml"
    chown "${USER}.${USER}" "${HOME}/config/arm.yaml"
fi
if [[ ! -f "${HOME}/config/apprise.yaml" ]] ; then
    echo "creating example apprise config ${HOME}/config/apprise.yaml"
    cp /opt/arm/docs/apprise.yaml "${HOME}/config/apprise.yaml"
    chown "${USER}.${USER}" "${HOME}/config/apprise.yaml"
fi
if [[ ! -f "${HOME}/.abcde.conf" ]] ; then
    echo "creating example abcde config ${HOME}/.abcde.conf"
    cp /opt/arm/setup/.abcde.conf "${HOME}/.abcde.conf"
    ln -sv "${HOME}/.abcde.conf" "${HOME}/config/.abcde.conf"
    chown "${USER}.${USER}" "${HOME}/.abcde.conf"
fi

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

