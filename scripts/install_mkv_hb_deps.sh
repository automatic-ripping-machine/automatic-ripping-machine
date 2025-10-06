#!/bin/bash

# This script installs dependencies used by the install_makemkv.sh and install_handbrake.sh scripts
echo -e "${RED}Installing build dependencies for MakeMKV and HandBrakeCLI${NC}"

apt update && apt upgrade -qy

# makemkv deps
apt install -yq --no-install-recommends openjdk-11-jre-headless
apt install -yq --no-install-recommends ca-certificates g++ gcc gnupg dirmngr libavcodec-dev libexpat-dev libssl-dev make pkg-config qtbase5-dev wget zlib1g-dev


# handbrake deps
# if architecture is any flavor of arm, install standard HandBrakeCLI and exit cleanly
if [[ $(dpkg --print-architecture) =~ arm.* ]]; then
    echo "Running on arm - using apt for HandBrakeCLI"
    apt install -yqq handbrake-cli
    cp /usr/bin/HandBrakeCLI /usr/local/bin/HandBrakeCLI
    exit 0
fi

apt install -yq autoconf automake autopoint appstream build-essential cmake git libass-dev libbz2-dev libfontconfig1-dev libfreetype6-dev libfribidi-dev libharfbuzz-dev libjansson-dev liblzma-dev libmp3lame-dev libnuma-dev libogg-dev libopus-dev libsamplerate-dev libspeex-dev libtheora-dev libtool libtool-bin libturbojpeg0-dev libvorbis-dev libx264-dev libxml2-dev libvpx-dev m4 make meson nasm ninja-build patch pkg-config tar zlib1g-dev clang libavcodec-dev  libva-dev libdrm-dev


# cleanup
apt autoremove
apt clean
rm -r /var/lib/apt/lists/*
