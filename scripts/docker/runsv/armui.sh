#!/bin/bash

echo "Starting web ui"
chmod +x /opt/arm/arm/runui.py
exec /sbin/setuser ubuntu /bin/python3 /opt/arm/arm/runui.py