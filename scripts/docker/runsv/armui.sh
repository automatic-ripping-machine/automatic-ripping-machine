#!/bin/sh -i

if /etc/init.d/udev status | grep -q 'is not running'; then
  echo "Udev not running.... Starting Udev"
  /etc/init.d/udev start
else
  ehco "Udev is already running"
fi
