#!/bin/bash

# First lets make sure podman is installed
dnf -yq install podman

# Now we'll creat our arm user and add them to cdrom and render groups
useradd arm -G cdrom,render

# Give arm user SystemD linger - allows processes to run after their session ends
loginctl enable-linger arm

# Create arm and SystemD container directories
mkdir -p ~arm/arm/{config,logs,media,music} ~arm/.config/containers/systemd
cp arm.container ~arm/.config/containers/systemd
chown -R arm:arm ~arm

# Update firewall-d to allow port 8080
firewall-cmd --permanent --add-port=8080/tcp
firewall-cmd --reload

# Tell SELinux to allow containers to access devices
setsebool container_use_devices=true

# Start arm - this depends on 4 CDROM Devices - sr0-sr03, if not there, it will fail.
systemctl --user --machine=arm@ daemon-reload
systemctl --user --machine=arm@ start arm
