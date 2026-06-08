#!/bin/sh
# Check that the ARM stack is functional:
# 1. Uvicorn is listening on port 8080 (TCP connect, no HTTP - avoids
#    single-worker starvation when keep-alive clients saturate the worker)
# 2. systemd-udevd is running (disc detection)
# 3. MakeMKV is installed and functional
# 4. abcde is installed (CD ripping)
python3 -c "import socket; s=socket.create_connection(('127.0.0.1',8080),timeout=5); s.close()" || exit 1
pgrep systemd-udevd > /dev/null || exit 1
makemkvcon | grep -q www.makemkv.com/developers || exit 1
abcde -v > /dev/null 2>&1 || exit 1
