#!/bin/bash

# Automatic Ripping Machine Docker container configuration
# Modify these settings to match your system and preferences

docker run -d \
    # Port Configuration <docker>:<arm-internal>
    -p "8080:8080" \
    # Set this to the owner of the below volumes
    -e ARM_UID="<id -u arm>" \
    -e ARM_GID="<id -g arm>" \
    # ARM Docker volumes <user path>:<arm-internal>
    -v "<path_to_arm_user_home_folder>:/home/arm" \
    -v "<path_to_music_folder>:/home/arm/music" \
    -v "<path_to_logs_folder>:/home/arm/logs" \
    -v "<path_to_media_folder>:/home/arm/media" \
    -v "<path_to_config_folder>:/etc/arm/config" \
    # CD/DVD/Bluray drive pass through - modify to suit the number of drives to pass through to the ARM docker
    --device="/dev/sr0:/dev/sr0" \
    --device="/dev/sr1:/dev/sr1" \
    --device="/dev/sr2:/dev/sr2" \
    --device="/dev/sr3:/dev/sr3" \
    --privileged \
    --restart "always" \
    --name "arm-rippers" \
    --cpuset-cpus='2,3,4,5,6,7...' \
    # Change this to a unique name for your system
    # example: automatic-ripping-machine
    IMAGE_NAME
