#!/bin/bash
podman run -d \
    --uidmap="+1000:@1000"\
    -p "8080:8080" \
    -e ARM_UID="1000" \
    -e ARM_GID="1000" \
    -v "$HOME/arm:/home/arm:Z" \
    -v "$HOME/arm/music:/home/arm/music:Z" \
    -v "$HOME/arm/logs:/home/arm/logs:Z" \
    -v "$HOME/arm/media:/home/arm/media:Z" \
    -v "$HOME/arm/config:/etc/arm/config:Z" \
    --device="/dev/sr0:/dev/sr0" \
    --device="/dev/sr1:/dev/sr1" \
    --device="/dev/sr2:/dev/sr2" \
    --device="/dev/sr3:/dev/sr3" \
    --device="/dev/dri:/dev/dri" \
    --restart "always" \
    --name "arm" \
    localhost/arm:latest

