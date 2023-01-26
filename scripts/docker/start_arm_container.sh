#!/bin/bash
docker run -d \
    -p "8080:8080" \
    -e ARM_UID="<id -u arm>" \
    -e ARM_GID="<id -g arm>" \
    -v "<path_to_arm_user_home_folder>:/home/arm" \
    -v "<path_to_music_folder>:/home/arm/Music" \
    -v "<path_to_logs_folder>:/home/arm/logs" \
    -v "<path_to_media_folder>:/home/arm/media" \
    -v "<path_to_config_folder>:/etc/arm/config" \
    --device="/dev/sr0:/dev/sr0" \
    --device="/dev/sr1:/dev/sr1" \
    --device="/dev/sr2:/dev/sr2" \
    --device="/dev/sr3:/dev/sr3" \
    --privileged \
    --restart "always" \
    --name "arm-rippers" \
    --cpus="3" \
    IMAGE_NAME
