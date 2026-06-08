# ARM Transcoder - Proxmox LXC Setup

This guide covers setting up arm-transcoder in a Proxmox LXC container with NVIDIA GPU passthrough, similar to your Plex setup.

## Prerequisites

- Proxmox VE with NVIDIA driver 580.119.02 installed on host
- nvidia_uvm module loading on boot (`/etc/modules-load.d/nvidia.conf`)
- Shared storage mounted on host (NFS, SMB/CIFS, etc.)

## Step 1: Create the LXC Container

On the Proxmox host (frank):

```bash
# Create a new privileged Ubuntu container
# Adjust storage and size as needed
pct create 108 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
    --hostname arm-transcoder \
    --memory 8192 \
    --cores 4 \
    --net0 name=eth0,bridge=vmbr0,ip=dhcp \
    --storage local-lvm \
    --rootfs local-lvm:16 \
    --unprivileged 0 \
    --features nesting=1,mount=nfs \
    --onboot 1
```

## Step 2: Add GPU Passthrough

Add to `/etc/pve/lxc/108.conf`:

```bash
cat <<EOF >> /etc/pve/lxc/108.conf

# NVIDIA GPU passthrough (same as Plex container)
lxc.cgroup2.devices.allow: c 195:* rwm
lxc.cgroup2.devices.allow: c 234:* rwm
lxc.cgroup2.devices.allow: c 237:* rwm
lxc.mount.entry: /dev/nvidia0 dev/nvidia0 none bind,optional,create=file
lxc.mount.entry: /dev/nvidiactl dev/nvidiactl none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-uvm dev/nvidia-uvm none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-uvm-tools dev/nvidia-uvm-tools none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-caps/nvidia-cap1 dev/nvidia-caps/nvidia-cap1 none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-caps/nvidia-cap2 dev/nvidia-caps/nvidia-cap2 none bind,optional,create=file
EOF
```

## Step 3: Add Storage Mounts

Add bind mounts for shared storage to the container config:

```bash
# Add to /etc/pve/lxc/108.conf
# Adjust paths to match your shared storage mounts on the host

cat <<EOF >> /etc/pve/lxc/108.conf

# Shared storage mounts (NFS, SMB, etc.)
lxc.mount.entry: /mnt/media/raw mnt/raw none bind,create=dir 0 0
lxc.mount.entry: /mnt/media/completed mnt/completed none bind,create=dir 0 0
EOF
```

## Step 4: Start Container and Install NVIDIA Driver

```bash
pct start 108
pct enter 108
```

Inside the container:

```bash
apt update
apt install -y wget build-essential

# Install NVIDIA driver (same version as host - NO kernel modules)
wget https://us.download.nvidia.com/XFree86/Linux-x86_64/580.119.02/NVIDIA-Linux-x86_64-580.119.02.run
chmod +x NVIDIA-Linux-x86_64-580.119.02.run
./NVIDIA-Linux-x86_64-580.119.02.run --no-kernel-module

# Verify
nvidia-smi
```

## Step 5: Install ARM Transcoder

```bash
# Clone or copy the arm-transcoder files
cd /root
git clone https://github.com/yourusername/arm-transcoder.git
cd arm-transcoder

# Run installer
chmod +x scripts/lxc-guest-install.sh
./scripts/lxc-guest-install.sh
```

## Step 6: Configure

Edit `/etc/arm-transcoder.env`:

```bash
nano /etc/arm-transcoder.env
```

Key settings for your environment:

```env
# Paths (matching the bind mounts)
RAW_PATH=/mnt/raw
COMPLETED_PATH=/mnt/completed
WORK_PATH=/var/lib/arm-transcoder/work
DB_PATH=/var/lib/arm-transcoder/transcoder.db
```

## Step 7: Start the Service

```bash
systemctl start arm-transcoder
systemctl status arm-transcoder

# Check logs
tail -f /var/log/arm-transcoder/service.log
```

## Step 8: Configure ARM Ripper

Update your ARM ripper's `arm.yaml`:

```yaml
SKIP_TRANSCODE: false
RIPMETHOD: "mkv"
DELRAWFILES: false
TRANSCODER_URL: "http://192.168.0.XX:5000/webhook/arm"  # IP of container 108
```

## Verification

1. Check GPU is accessible:
   ```bash
   su -s /bin/bash transcoder -c 'nvidia-smi'
   ```

2. Check service health:
   ```bash
   curl http://localhost:5000/health
   ```

3. Test webhook:
   ```bash
   curl -X POST http://localhost:5000/webhook/arm \
     -H "Content-Type: application/json" \
     -d '{"title":"Test","body":"Rip of Test Movie (2024) complete"}'
   ```

## GPU Sharing with Plex

Both containers (Plex LXC 107 and ARM Transcoder LXC 108) can share the GTX 1660. NVENC supports multiple simultaneous encode sessions (GTX 1660 supports 3 concurrent sessions).

To prevent conflicts:
- Set `MAX_CONCURRENT=1` in arm-transcoder to leave headroom for Plex
- Consider scheduling heavy transcodes during off-peak Plex usage

## Troubleshooting

### CUDA Error 999
Ensure `nvidia_uvm` module is loaded on host:
```bash
# On host (frank)
lsmod | grep nvidia_uvm
# If missing:
modprobe nvidia_uvm
```

### Driver Version Mismatch
Container driver must match host exactly:
```bash
# Check host version
nvidia-smi | head -3

# Inside container, reinstall if mismatched
./NVIDIA-Linux-x86_64-580.119.02.run --no-kernel-module
```

### HandBrake NVENC Not Working
Verify HandBrake sees the encoder:
```bash
HandBrakeCLI --help 2>&1 | grep -i nvenc
```

If not listed, you may need to compile HandBrake with NVENC support or use the flatpak version.
