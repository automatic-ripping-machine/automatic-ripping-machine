#!/bin/bash

# This script installs dependencies used by the install_makemkv.sh script
echo -e "${RED}Installing build dependencies for MakeMKV${NC}"

apt update && apt upgrade -qy

# makemkv deps
apt install -yq --no-install-recommends openjdk-11-jre-headless
apt install -yq --no-install-recommends ca-certificates g++ gcc gnupg dirmngr libavcodec-dev libexpat-dev libssl-dev make pkg-config qtbase5-dev wget zlib1g-dev

# cleanup
apt autoremove
apt clean
rm -r /var/lib/apt/lists/*
