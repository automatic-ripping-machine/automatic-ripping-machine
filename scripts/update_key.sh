#!/usr/bin/env bash

# This script is inspired by the script posted on the forums.
# Given that it hasn't been taken down I'm going to assume they
# don't have a problem with users programmatically scraping the
# beta key.
# Link: https://forum.makemkv.com/forum/viewtopic.php?p=119221#p119221

makemkv_serial_url="https://forum.makemkv.com/forum/viewtopic.php?f=5&t=1053"
makemkv_serial=$(curl -fsSL "$makemkv_serial_url" | grep -oP 'T-[\w\d@]{66}')
echo "MakeMKV beta key for this month: $makemkv_serial"
# TODO: implement this
# if file exists OR grep doesn't find key string in settings
#     if run w/arg
#         append permakey string to settings
#     else
#         append beta key to settings
# else
#     if run w/arg
#         sed replace key in settings w/permakey
#     else
#         sed replace key is settings w/beta key
mkdir -p "/home/arm/.MakeMKV"
chown arm:arm "/home/arm/.MakeMKV"
echo "app_Key = \"$makemkv_serial\"" > /home/arm/.MakeMKV/settings.conf
chown arm:arm "/home/arm/.MakeMKV/settings.conf"
