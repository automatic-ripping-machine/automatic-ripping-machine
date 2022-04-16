#!/bin/sh -i

echo "Trying to start udev"
/etc/init.d/udev start > /dev/null 2>&1
echo "udev Started successfully"