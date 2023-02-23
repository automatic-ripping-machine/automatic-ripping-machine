#!/usr/bin/env bash

# This script is inspired by the script posted on the forums.
# Given that it hasn't been taken down I'm going to assume they
# don't have a problem with users programmatically scraping the
# beta key.
# Link: https://forum.makemkv.com/forum/viewtopic.php?p=119221#p119221

makemkv_serial_url="https://forum.makemkv.com/forum/viewtopic.php?f=5&t=1053"
MAKEMKV_PERMA_KEY=

# save passed MAKEMKV_PERMA_KEY or scrape this month's beta key
if [ -n "$1" ]; then
    echo "MAKEMKV_PERMA_KEY passed as arg"
    MAKEMKV_PERMA_KEY=$1
else
    makemkv_serial=$(curl -fsSL "$makemkv_serial_url" | grep -oP 'T-[\w\d@]{66}')
    echo "MakeMKV beta key for this month: $makemkv_serial"
fi

# create .MakeMKV dir if it doesn't already exist
MAKEMKV_DIR="/home/arm/.MakeMKV"
if [ ! -d "$MAKEMKV_DIR" ]; then
    mkdir -p "$MAKEMKV_DIR"
    chown arm:arm "$MAKEMKV_DIR"
fi

# if file doesn't exist OR grep doesn't find key string in settings
SETTINGS_FILE="$MAKEMKV_DIR/settings.conf"
if [[ ! -f "$SETTINGS_FILE" ]] || ! grep -q "app_Key" "$SETTINGS_FILE"; then
    echo "Either $SETTINGS_FILE doesn't exist, or app_Key is not inside it"
    # if run w/arg
    if [ -n "$MAKEMKV_PERMA_KEY" ]; then
        # append permakey string to settings
        echo "app_Key = \"$MAKEMKV_PERMA_KEY\"" >> "$SETTINGS_FILE"
    else
        # append beta key to settings
        echo "app_Key = \"$makemkv_serial\"" >> "$SETTINGS_FILE"
    fi
else
    echo "$SETTINGS_FILE exists, updating value of app_Key"
    # if run w/arg
    if [ -n "$MAKEMKV_PERMA_KEY" ]; then
        # sed replace key in settings w/permakey
        sed -i "s|app_Key = \"T-.*\"|app_Key = \"$MAKEMKV_PERMA_KEY\"|" "$SETTINGS_FILE"
    else
        # sed replace key is settings w/beta key
        sed -i "s|app_Key = \"T-.*\"|app_Key = \"$makemkv_serial\"|" "$SETTINGS_FILE"
    fi
fi

chown arm:arm "/home/arm/.MakeMKV/settings.conf"
