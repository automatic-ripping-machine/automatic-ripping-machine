#!/bin/bash

echo "Starting disc camera daemon"
chmod +x /opt/arm/arm/camera/daemon.py
exec /sbin/setuser arm /bin/python3 /opt/arm/arm/camera/daemon.py
