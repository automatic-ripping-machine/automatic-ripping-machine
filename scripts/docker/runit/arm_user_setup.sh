#!/bin/bash
# This script is first to run due to this: https://github.com/phusion/baseimage-docker#running_startup_scripts.
#
# It updates the UIG or GID of the included arm user to whatever value the user
# passes at runtime, if the value set is not the default value of 1000
#
# If the container is run again without specifying UID and GID, this script
# resets the UID and GID of all files in ARM directories to the defaults

DEFAULT_UID=1000
DEFAULT_GID=1000

if [[ $ARM_UID -ne $DEFAULT_UID ]]; then
    echo -e "Updating arm user id from $DEFAULT_UID to $ARM_UID..."
    usermod -u "$ARM_UID" arm
elif [[ $ARM_UID -eq $DEFAULT_UID ]]; then
    echo -e "Updating arm group id $ARM_UID to default (1000)..."
    usermod -u $DEFAULT_UID arm
fi

if [[ $ARM_GID -ne $DEFAULT_GID ]]; then
    echo -e "Updating arm group id from $DEFAULT_GID to $ARM_GID..."
    groupmod -g "$ARM_GID" arm
elif [[ $ARM_UID -eq $DEFAULT_GID ]]; then
    echo -e "Updating arm group id $ARM_GID to default (1000)..."
    groupmod -g $DEFAULT_GID arm
fi
