#!/bin/bash
set -a && source /etc/environment && set +a
exec gosu arm python3 /opt/arm/arm/runui.py
