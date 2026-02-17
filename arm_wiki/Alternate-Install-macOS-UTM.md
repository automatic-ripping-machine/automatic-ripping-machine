# macOS with UTM (Docker)

> [!CAUTION]
> This installation method is not supported or maintained by the ARM Developers.
> For full support and continued maintenance,
> we recommend installing ARM via the supported [Docker Container](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/docker).
> This installation method was developed for macOS users who cannot run Docker natively with USB passthrough.
>
> **Use at your own risk**

This guide covers installing ARM using Docker inside an Ubuntu Server VM running on macOS via UTM. This approach is necessary because ARM requires Linux and direct USB device access, which macOS cannot provide natively.

> **Important:** You must use UTM's **QEMU backend** (Emulate), not Apple Virtualization (Virtualize). Apple Virtualization does not support USB passthrough.

## Prerequisites

- Mac (Apple Silicon or Intel)
- External USB DVD/Blu-ray drive
- [Ubuntu Server 24.04 ISO](https://ubuntu.com/download/server) (ARM64 for Apple Silicon, AMD64 for Intel)
- At least 4GB RAM and 64GB storage available for the VM

---

## Part 1: Install UTM

1. Download UTM from [https://mac.getutm.app](https://mac.getutm.app)
2. Open the downloaded DMG file
3. Drag UTM to your Applications folder
4. Launch UTM from Applications

> **Tip:** If macOS blocks the app, go to **System Settings → Privacy & Security** and click **Open Anyway**.

---

## Part 2: Create the Ubuntu VM

### Step 1: Start a New VM

1. Open UTM and click **Create a New Virtual Machine**
2. Select **Emulate** (NOT Virtualize - critical for USB passthrough)
3. Select **Linux**

### Step 2: Configure the VM

**Boot ISO:**
- Click **Browse** and select your Ubuntu Server ISO

**Hardware Settings (Apple Silicon):**
- Architecture: `ARM64 (aarch64)`
- System: `QEMU 8.2 ARM Virtual Machine`
- RAM: `4096 MB` (minimum)
- CPU Cores: `4`

**Hardware Settings (Intel Mac):**
- Architecture: `x86_64`
- System: `Standard PC (Q35 + ICH9, 2009)`
- RAM: `4096 MB` (minimum)
- CPU Cores: `4`

**Storage:**
- Size: `64 GB` (minimum recommended)

**Network:**
- Select **Bridged (Advanced)** and choose your network interface (usually `en0`)

### Step 3: Name and Create

- Name: `ARM` or `Ubuntu-ARM`
- Click **Save**

---

## Part 3: Install Ubuntu Server

1. Start the VM and select **Try or Install Ubuntu Server**
2. Follow the installation wizard:
   - Installation type: **Ubuntu Server** (full, not minimized)
   - **Enable OpenSSH server**
   - Skip featured snaps
3. After installation, remove the ISO from the virtual CD drive in UTM settings
4. Get the VM's IP address:

```bash
ip addr show
```

---

## Part 4: Connect USB DVD Drive

### Attach the Drive in UTM

1. With the VM running, plug in your USB DVD drive
2. In the UTM window toolbar, click the **USB icon**
3. Select your DVD drive to connect it to the VM

### Verify the Drive

SSH into your VM:

```bash
ssh username@<VM_IP_ADDRESS>
```

Check if the drive is detected:

```bash
ls -la /dev/sr0
```

Expected output:
```
brw-rw----+ 1 root cdrom 11, 0 Jan 29 05:28 /dev/sr0
```

---

## Part 5: Install Docker

```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Log out and back in for group changes to take effect, then verify:

```bash
docker --version
```

---

## Part 6: Install ARM

### Create Directory Structure

```bash
mkdir -p ~/arm/{config,logs,music,movies,completed}
cd ~/arm
```

### Create Docker Compose File

```bash
cat > docker-compose.yml << 'EOF'
services:
  arm:
    image: automaticrippingmachine/automatic-ripping-machine:latest
    container_name: arm
    restart: unless-stopped
    privileged: true
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
      - ARM_UID=1000
      - ARM_GID=1000
    volumes:
      - ./config:/etc/arm/config
      - ./logs:/home/arm/logs
      - ./music:/home/arm/music
      - ./movies:/home/arm/media/movies
      - ./completed:/home/arm/media/completed
    ports:
      - "8080:8080"
    devices:
      - /dev/sr0:/dev/sr0
EOF
```

> **Note:** Adjust `TZ` to your timezone (e.g., `America/Los_Angeles`, `Europe/London`)

### Start ARM

```bash
docker compose pull
docker compose up -d
```

### Verify ARM is Running

```bash
docker logs arm --tail 20
```

Look for:
```
INFO ARM: DriveUtils.drives_search Optical drive detected: /dev/sr0
```

---

## Part 7: Access ARM

Open your browser and navigate to:

```
http://<VM_IP_ADDRESS>:8080
```

**Default credentials:**
- Username: `admin`
- Password: `password`

> **Change the default password immediately** in Settings.

---

## Optional: Shared Media Library

To save ripped media directly to a macOS folder, configure a VirtFS shared directory in UTM:

1. Shut down the VM
2. In UTM, edit the VM settings
3. Under **Sharing**, add a directory path (e.g., `/Volumes/Media Library`)
4. Start the VM and mount the share:

```bash
sudo mkdir -p /mnt/media-library
sudo mount -t 9p -o trans=virtio share0 /mnt/media-library -oversion=9p2000.L
```

5. Update your `docker-compose.yml` volumes to use `/mnt/media-library`

For persistent mounting, add to `/etc/fstab`:

```
share0 /mnt/media-library 9p trans=virtio,version=9p2000.L,rw,_netdev 0 0
```

> **Note:** VirtFS permissions require `chmod 777` on the shared directory due to UID mismatches between macOS and Linux.

---

## Troubleshooting

### USB Drive Not Detected

1. Verify you selected **Emulate** (QEMU), not Virtualize when creating the VM
2. Check UTM's USB menu to ensure the drive is connected
3. Run `ls -la /dev/sr*` in the VM

### ARM Shows "No drives found"

1. Verify `/dev/sr0` exists: `ls -la /dev/sr0`
2. Check docker-compose.yml device path
3. Restart the container: `docker compose restart`

### Cannot Access Web UI

1. Verify container is running: `docker ps`
2. Check if VM IP changed: `ip addr show`
3. Confirm port 8080 is exposed: `docker port arm`

### Performance

QEMU emulation is slower than native virtualization. This is the tradeoff for USB passthrough support. Ripping works but takes longer than on native hardware.

---

## Maintenance Commands

```bash
# View logs
docker logs arm -f

# Restart ARM
cd ~/arm && docker compose restart

# Update ARM
cd ~/arm && docker compose pull && docker compose up -d

# Stop ARM
cd ~/arm && docker compose down
```

---

## Summary

| Component | Value |
|-----------|-------|
| VM Software | UTM with QEMU backend |
| Guest OS | Ubuntu Server 24.04 |
| Container | `automaticrippingmachine/automatic-ripping-machine` |
| Web Interface | `http://VM_IP:8080` |
| Default Login | admin / password |
| DVD Device | /dev/sr0 |
