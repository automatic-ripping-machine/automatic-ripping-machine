#!/usr/bin/env bash

# This script is inspired by the script posted on the forums.
# Given that it hasn't been taken down I'm going to assume they
# don't have a problem with users programmatically scraping the
# beta key.
# Link: https://forum.makemkv.com/forum/viewtopic.php?p=119221#p119221

MAKEMKV_PERMA_KEY=
if [ -n "$1" ]; then
    MAKEMKV_PERMA_KEY=$1
fi

makemkv_serial_url="https://forum.makemkv.com/forum/viewtopic.php?f=5&t=1053"
makemkv_serial=$(curl -fsSL "$makemkv_serial_url" | grep -oP 'T-[\w\d@]{66}')
echo "MakeMKV beta key for this month: $makemkv_serial"

mkdir -p "/home/arm/.MakeMKV"
chown arm:arm "/home/arm/.MakeMKV"

# if file exists OR grep doesn't find key string in settings
SETTINGS_FILE="/home/arm/.MakeMKV/settings.conf"
if [[ -f $SETTINGS_FILE ]] || ! grep -q "app_Key" "$SETTINGS_FILE"; then
    echo "Either $SETTINGS_FILE doesn't exist, or app_Key is not inside it"
    # if run w/arg
    if [ -n "$MAKEMKV_PERMA_KEY" ]; then
        # append permakey string to settings
        echo "app_Key = \"$MAKEMKV_PERMA_KEY\"" > "/home/arm/.MakeMKV/settings.conf"
    else
        # append beta key to settings
        echo "app_Key = \"$makemkv_serial\"" > /home/arm/.MakeMKV/settings.conf
    fi
else
    # if run w/arg
    if [ -n "$MAKEMKV_PERMA_KEY" ]; then
        # sed replace key in settings w/permakey
        sed -i "s|app_Key = \"T-.*\"|app_Key = \"$MAKEMKV_PERMA_KEY\"|" $SETTINGS_FILE
    else
        # sed replace key is settings w/beta key
        sed -i "s|app_Key = \"T-.*\"|app_Key = \"$makemkv_serial\"|" $SETTINGS_FILE
    fi
fi

chown arm:arm "/home/arm/.MakeMKV/settings.conf"
