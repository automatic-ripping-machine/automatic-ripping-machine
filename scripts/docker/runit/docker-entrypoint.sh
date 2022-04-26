#!/bin/bash
#
# set up a user and switch to that user

set -euo pipefail

export ARM_HOME="/home/arm"

# setup needed/expected dirs if not found
SUBDIRS="media media/completed media/raw media/movies logs db Music .MakeMKV"
for dir in $SUBDIRS ; do
    thisDir="${ARM_HOME}/${dir}"
    if [[ ! -d "${thisDir}" ]] ; then
        echo "creating dir ${thisDir}"
        mkdir -p 0777 "${thisDir}"
    fi
done

# setup config files if not found
mkdir -p /etc/arm/config
CONFS="arm.yaml apprise.yaml .abcde.conf"
for conf in $CONFS; do
    thisConf="/etc/arm/config/${conf}"
    if [[ ! -f "${thisConf}" ]] ; then
        # Don't overwrite with defaults during reinstall
        cp --no-clobber "/opt/arm/setup/${conf}" "${thisConf}"
    fi
done

exec "$@"
