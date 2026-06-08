#!/bin/bash
# ARM Transcoder - Proxmox LXC Creation Script
# Run this on the Proxmox host to create and configure the container
#
# Usage: ./lxc-host-create.sh [VMID] [IP_ADDRESS]
# Example: ./lxc-host-create.sh 108 192.168.1.100

set -e

VMID="${1:-108}"
IP_ADDRESS="${2:-dhcp}"
HOSTNAME="arm-transcoder"
MEMORY=8192
CORES=4
DISK_SIZE=16
STORAGE="local-lvm"
TEMPLATE="local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"

# Shared storage paths on host (adjust these!)
RAW_STORAGE="/mnt/media/raw"
COMPLETED_STORAGE="/mnt/media/completed"

echo "=== Creating ARM Transcoder LXC Container ==="
echo "VMID: ${VMID}"
echo "Hostname: ${HOSTNAME}"
echo "IP: ${IP_ADDRESS}"
echo ""

# Check if VMID already exists
if pct status ${VMID} &>/dev/null; then
    echo "ERROR: Container ${VMID} already exists"
    exit 1
fi

# Check template exists
if [[ ! -f "/var/lib/vz/template/cache/ubuntu-22.04-standard_22.04-1_amd64.tar.zst" ]]; then
    echo "Downloading Ubuntu 22.04 template..."
    pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
fi

# Create container
echo "Creating container..."
if [[ "$IP_ADDRESS" = "dhcp" ]]; then
    NET_CONFIG="name=eth0,bridge=vmbr0,ip=dhcp"
else
    NET_CONFIG="name=eth0,bridge=vmbr0,gw=192.168.1.1,ip=${IP_ADDRESS}/24"
fi

pct create ${VMID} ${TEMPLATE} \
    --hostname ${HOSTNAME} \
    --memory ${MEMORY} \
    --cores ${CORES} \
    --net0 "${NET_CONFIG}" \
    --storage ${STORAGE} \
    --rootfs ${STORAGE}:${DISK_SIZE} \
    --unprivileged 0 \
    --features nesting=1,mount=nfs \
    --onboot 1

echo "Container created"

# Add GPU passthrough and storage mounts
echo "Configuring GPU passthrough and mounts..."
cat <<EOF >> /etc/pve/lxc/${VMID}.conf

# NVIDIA GPU passthrough
lxc.cgroup2.devices.allow: c 195:* rwm
lxc.cgroup2.devices.allow: c 234:* rwm
lxc.cgroup2.devices.allow: c 237:* rwm
lxc.mount.entry: /dev/nvidia0 dev/nvidia0 none bind,optional,create=file
lxc.mount.entry: /dev/nvidiactl dev/nvidiactl none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-uvm dev/nvidia-uvm none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-uvm-tools dev/nvidia-uvm-tools none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-caps/nvidia-cap1 dev/nvidia-caps/nvidia-cap1 none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-caps/nvidia-cap2 dev/nvidia-caps/nvidia-cap2 none bind,optional,create=file

# Shared storage bind mounts
lxc.mount.entry: ${RAW_STORAGE} mnt/raw none bind,create=dir 0 0
lxc.mount.entry: ${COMPLETED_STORAGE} mnt/completed none bind,create=dir 0 0
EOF

echo "Starting container..."
pct start ${VMID}
sleep 5

echo ""
echo "=== Container ${VMID} created and started ==="
echo ""
echo "Next steps:"
echo "  1. Enter container: pct enter ${VMID}"
echo "  2. Install NVIDIA driver:"
echo "     wget https://us.download.nvidia.com/XFree86/Linux-x86_64/580.119.02/NVIDIA-Linux-x86_64-580.119.02.run"
echo "     chmod +x NVIDIA-Linux-x86_64-580.119.02.run"
echo "     ./NVIDIA-Linux-x86_64-580.119.02.run --no-kernel-module"
echo "  3. Verify: nvidia-smi"
echo "  4. Clone arm-transcoder and run scripts/lxc-guest-install.sh"
echo ""
echo "Container IP:"
pct exec ${VMID} -- hostname -I
