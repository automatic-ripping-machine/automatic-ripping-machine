#!/bin/bash
# This script is first to run due to this: https://github.com/phusion/baseimage-docker#running_startup_scripts.
#
# It updates the UIG or GID of the included arm user to whatever value the user
# passes at runtime, if the value set is not the default value of 1000
#
# If the container is run again without specifying UID and GID, this script
# resets the UID and GID of all files in ARM directories to the defaults

set -euo pipefail

export ARM_HOME="/home/arm"
DEFAULT_UID=1000
DEFAULT_GID=1000

### Setup User
if [[ $ARM_UID -ne $DEFAULT_UID ]]; then
    echo -e "Updating arm user id from $DEFAULT_UID to $ARM_UID..."
    usermod -u "$ARM_UID" arm
elif [[ $ARM_UID -eq $DEFAULT_UID ]]; then
    echo -e "Updating arm group id $ARM_UID to default (1000)..."
    usermod -u $DEFAULT_UID arm
fi

if [[ $ARM_GID -ne $DEFAULT_GID ]]; then
    echo -e "Updating arm group id from $DEFAULT_GID to $ARM_GID..."
    groupmod -og "$ARM_GID" arm
elif [[ $ARM_UID -eq $DEFAULT_GID ]]; then
    echo -e "Updating arm group id $ARM_GID to default (1000)..."
    groupmod -og $DEFAULT_GID arm
fi
echo "Adding arm user to 'render' group"
usermod -a -G render arm

### Setup Files
chown -R arm:arm /opt/arm

# setup needed/expected dirs if not found
SUBDIRS="media media/completed media/raw media/movies media/transcode logs logs/progress db Music .MakeMKV"
for dir in $SUBDIRS ; do
    thisDir="$ARM_HOME/$dir"
    if [[ ! -d "$thisDir" ]] ; then
        echo "Creating dir: $thisDir"
        mkdir -p "$thisDir"
    fi
    chown -R arm:arm "$thisDir"
done

    ##### Setup ARM-specific config files if not found
    mkdir -p /etc/arm/config
    CONFS="arm.yaml apprise.yaml"
    for conf in $CONFS; do
        thisConf="/etc/arm/config/${conf}"
        if [[ ! -f "${thisConf}" ]] ; then
            echo "Config not found! Creating config file: ${thisConf}"
            # Don't overwrite with defaults during reinstall
            cp --no-clobber "/opt/arm/setup/${conf}" "${thisConf}"
        fi
    done
    chown -R arm:arm /etc/arm/
    
    # abcde.conf is expected in /etc by the abcde installation
    cp --no-clobber "/opt/arm/setup/.abcde.conf" "/etc/.abcde.conf"
    ln -sf /etc/.abcde.conf /etc/arm/config/abcde.conf
    chown arm:arm "/etc/.abcde.conf" "/etc/arm/config/abcde.conf"
