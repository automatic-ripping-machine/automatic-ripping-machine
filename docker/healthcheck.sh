#!/bin/bash
set -euo pipefail

curl --fail "http://$(hostname):8080"
sv check armui
sv check disc-monitor
sv check mount-helper
makemkvcon 2>&1 | grep -q www.makemkv.com/developers
HandBrakeCLI --version
abcde -v
