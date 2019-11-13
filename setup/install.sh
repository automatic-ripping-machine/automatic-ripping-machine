#!/bin/bash

echo set variables
ARMSETUP="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ARMDIR=$ARMSETUP/..
ARMLOG=$ARMDIR/logs
ARMSCRIPTS=$ARMDIR/scripts
ARMCONF=$ARMDIR/conf/arm.yaml
ARMSOURCE=$ARMDIR/arm

echo create symlinks
ln -s /opt/arm $ARMDIR
ln -s /var/log/arm $ARMLOG
ln -s /etc/arm.yaml $ARMCONF
ln -s /home/arm/.abcde.conf $ARMSETUP/.abcde.conf
ln -s /lib/udev/rules.d/51-automedia.rules $ARMSETUP/51-automedia.rules

echo perform setup
$ARMSCRIPTS/update_makemkv.sh
echo pseudocode: if armconf not exist, copy armdir/docs/arm.yaml.sample armconf
echo I dunno, probably more. Check logger.py for checking filepath

