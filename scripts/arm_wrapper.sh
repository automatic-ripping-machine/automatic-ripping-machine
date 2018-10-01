#!/bin/bash

DEVNAME=$1

echo "Starting ARM on ${DEVNAME}" | logger -t ARM
/bin/su -l -c "echo /usr/bin/python3 /opt/arm/arm/ripper/main.py -d ${DEVNAME} | at now" -s /bin/bash arm
