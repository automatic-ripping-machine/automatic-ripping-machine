# Decoupled Deployment Guide

ARM + UI on the **ripping host** and Transcoder on the **GPU host**.

## Architecture

```
┌──────────────────────────────┐     NFS      ┌──────────────────────────────┐
│  <ARM_HOST> (ripping host)   │◄────────────►│  <GPU_HOST> (transcoder)     │
│                              │              │                              │
│  arm-rippers  (rip discs)    │   webhook    │  arm-transcoder (GPU encode) │
│  arm-ui       (dashboard)    │─────────────►│                              │
│  arm-hb-presets              │              │                              │
│  arm-db-init                 │              │                              │
│                              │              │                              │
│  /home/arm/media/raw/  ──────┤── NFS ──────►│  /mnt/media/raw/   (ro)      │
│  /home/arm/media/completed/  │◄── NFS ──────┤  /mnt/media/completed/ (rw)  │
└──────────────────────────────┘              └──────────────────────────────┘
```

Replace `<ARM_HOST>` and `<GPU_HOST>` with your actual IPs or hostnames throughout.

## Prerequisites

- Docker + Docker Compose on both hosts
- GPU runtime on the transcoder host (NVIDIA Container Toolkit, or VAAPI for AMD/Intel)
- NFS (or other shared filesystem) between both hosts
- Matching UID/GID on both hosts for file permissions

## Step 1 — NFS Setup

### ARM host — NFS server

```bash
sudo apt install nfs-kernel-server

# Export the media directory (replace <GPU_HOST> with the transcoder's IP)
echo '/home/arm/media <GPU_HOST>(rw,sync,no_subtree_check,no_root_squash)' | sudo tee -a /etc/exports

# Create directories if needed
sudo mkdir -p /home/arm/media/{raw,completed}
sudo chown -R 1000:1000 /home/arm/media

sudo exportfs -ra
sudo systemctl enable --now nfs-server
```

### Transcoder host — NFS client

```bash
sudo apt install nfs-common

# Create mount points
sudo mkdir -p /mnt/media/raw /mnt/media/completed

# Mount (test — replace <ARM_HOST> with the ripping host's IP)
sudo mount -t nfs <ARM_HOST>:/home/arm/media/raw /mnt/media/raw
sudo mount -t nfs <ARM_HOST>:/home/arm/media/completed /mnt/media/completed

# Persist in fstab
echo '<ARM_HOST>:/home/arm/media/raw       /mnt/media/raw       nfs defaults,_netdev 0 0' | sudo tee -a /etc/fstab
echo '<ARM_HOST>:/home/arm/media/completed  /mnt/media/completed nfs defaults,_netdev 0 0' | sudo tee -a /etc/fstab
```

## Step 2 — ARM Host

```bash
# Clone repo (or copy files)
git clone https://github.com/uprightbass360/automatic-ripping-machine-neu.git
cd automatic-ripping-machine-neu

# Create .env from the remote-transcoder template
cp .env.remote-transcoder.example .env

# Edit .env — set TRANSCODER_HOST to the GPU host's IP, adjust paths/drives/CPU
nano .env

# Create directories
sudo mkdir -p /home/arm/{music,logs,media/{raw,completed}} /etc/arm/config
sudo chown -R 1000:1000 /home/arm /etc/arm/config

# Start ARM + UI
docker compose -f docker-compose.remote-transcoder.yml up -d
```

### Configure notify_transcoder.sh

ARM notifies the transcoder when a rip completes via a bash script webhook.

```bash
# Copy the notification script into the ARM config volume
sudo cp dev-data/config/notify_transcoder.sh /etc/arm/config/notify_transcoder.sh
sudo chmod +x /etc/arm/config/notify_transcoder.sh
```

Edit `/etc/arm/config/notify_transcoder.sh` — update these lines:

```bash
TRANSCODER_URL="http://<GPU_HOST>:5000/webhook/arm"
WEBHOOK_SECRET=""  # Set this to match WEBHOOK_SECRET in the transcoder's .env
```

Edit `/etc/arm/config/arm.yaml` — set the BASH_SCRIPT path:

```yaml
BASH_SCRIPT: "/etc/arm/config/notify_transcoder.sh"
JSON_URL: ""  # Clear this to avoid duplicate notifications
```

## Step 3 — Transcoder Host

```bash
# Clone repo
git clone https://github.com/uprightbass360/automatic-ripping-machine-transcoder.git
cd automatic-ripping-machine-transcoder

# Create .env from template
cp .env.example .env

# Edit .env — set HOST_RAW_PATH, HOST_COMPLETED_PATH to your NFS mount paths.
# Set ARM_CALLBACK_URL to the ARM host (e.g. http://<ARM_HOST>:8080) so the
# transcoder can notify ARM when jobs complete.
# VIDEO_ENCODER and presets are auto-detected from GPU hardware at startup.
nano .env

# Create local directories
mkdir -p work data

# Start transcoder (choose your GPU compose file)
# NVIDIA:
docker compose up -d --build
# AMD:
docker compose -f docker-compose.amd.yml up -d --build
# Intel:
docker compose -f docker-compose.intel.yml up -d --build
```

### Verify GPU access

```bash
# NVIDIA
docker compose exec arm-transcoder nvidia-smi
# AMD/Intel (VAAPI)
docker compose exec arm-transcoder ls /dev/dri/
```

## Step 4 — Verify

### Check services are running

```bash
# ARM host
docker compose -f docker-compose.remote-transcoder.yml ps

# Transcoder host
docker compose ps
```

### Check transcoder health

```bash
curl http://<GPU_HOST>:5000/health
```

### Check UI can reach transcoder

Open `http://<ARM_HOST>:8888` — the dashboard should show transcoder status.

### Test the notification pipeline

```bash
# From the ARM host, simulate a webhook
curl -X POST http://<GPU_HOST>:5000/webhook/arm \
  -H "Content-Type: application/json" \
  -d '{"title": "test", "body": "test notification", "type": "info"}'
```

## Ports Summary

| Service | Host | Port |
|---------|------|------|
| ARM (Flask UI) | ARM host | 8080 |
| ARM UI (SvelteKit) | ARM host | 8888 |
| Transcoder API | GPU host | 5000 |

## Troubleshooting

**Transcoder can't read raw files:**
- Verify NFS mounts: `ls /mnt/media/raw/` on the transcoder host
- Check UID/GID match: files should be owned by 1000:1000 on both hosts

**UI shows transcoder as offline:**
- Verify `TRANSCODER_HOST` in the ARM host's `.env` matches the GPU host IP
- Check firewall: `curl http://<GPU_HOST>:5000/health` from the ARM host

**Notification script fails:**
- Check ARM logs: `docker logs arm-rippers 2>&1 | grep -i notify`
- Test script manually: `docker exec arm-rippers /etc/arm/config/notify_transcoder.sh "test" "test body"`
