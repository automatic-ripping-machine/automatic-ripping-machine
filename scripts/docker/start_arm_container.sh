#!/bin/bash
docker run -d \
    -p "8080:8080" \
    -e ARM_UID="<id -u arm>" \
    -e ARM_GID="<id -g arm>" \
    -v "/home/arm:<path_to_arm_user_home_folder>" \
    -v "/home/arm/Music:<path_to_music_folder>" \
    -v "/home/arm/logs:<path_to_logs_folder>" \
    -v "/home/arm/media:<path_to_media_folder>" \
    -v "/etc/arm/config:<path_to_config_folder>" \
    --device="/dev/sr0:/dev/sr0" \
    --device="/dev/sr1:/dev/sr1" \
    --device="/dev/sr2:/dev/sr2" \
    --device="/dev/sr3:/dev/sr3" \
    --priveleged \
    --restart "always" \
    --name "arm-rippers"
    $IMAGE
