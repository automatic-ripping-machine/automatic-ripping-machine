# Claude Code Project Instructions

## Git Commits
- Never include `Co-Authored-By` lines in commit messages
- Do not sign commits with Claude's name or email

## First-Time Docker Setup (Single Machine, All-in-One)

This guide covers deploying ARM + UI + Transcoder on one machine using published Docker Hub images.

### Prerequisites

- Docker Engine + Docker Compose v2
- One or more optical drives (`/dev/sr0`, `/dev/sr1`, etc.)
- `linux/amd64` host (MakeMKV and HandBrake are not built for ARM/arm64)
- NVIDIA GPU + `nvidia-container-toolkit` if using GPU transcoding (optional — CPU fallback with `x265` works fine)

### 1. Clone the repo

```bash
git clone https://github.com/uprightbass360/automatic-ripping-machine-neu.git
cd automatic-ripping-machine-neu
```

No need for `--recurse-submodules` unless you plan to do development.

### 2. Create host directories

ARM expects these directories to exist on the host. Adjust paths to your setup:

```bash
sudo mkdir -p /home/arm/media/raw /home/arm/media/completed /home/arm/logs /home/arm/music /etc/arm/config
sudo chown -R 1000:1000 /home/arm /etc/arm
```

The UID/GID (1000:1000) must match `ARM_UID`/`ARM_GID` in your `.env`.

### 3. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env` — the critical settings to review:

| Variable | What to set | Notes |
|----------|-------------|-------|
| `ARM_UID` / `ARM_GID` | Your user's UID/GID (`id -u` / `id -g`) | Must own the media directories |
| `TZ` | Your timezone (e.g. `America/New_York`) | |
| `ARM_MEDIA_PATH` | `/home/arm/media` | Contains `raw/` and `completed/` subdirs |
| `ARM_LOGS_PATH` | `/home/arm/logs` | |
| `ARM_CONFIG_PATH` | `/etc/arm/config` | Where `arm.yaml` lives |
| `ARM_MUSIC_PATH` | `/home/arm/music` | For CD rips |
| `VIDEO_ENCODER` | `x265` (CPU) or `nvenc_h265` (NVIDIA GPU) | Default is `x265` for CPU-only |
| `TRANSCODER_WORK_PATH` | Path to fast local storage (SSD) | Scratch space during transcoding |

### 4. Uncomment optical drives

**This step is required.** Without it, ARM cannot see your disc drives. In `docker-compose.yml`, uncomment the `devices:` section under `arm-rippers` and list your drives:

```yaml
devices:
  - /dev/sr0:/dev/sr0
  # - /dev/sr1:/dev/sr1
```

Verify your drives exist on the host first: `ls -la /dev/sr*`. The `privileged: true` flag alone is not sufficient — you must explicitly map each drive.

### 5. Install udev rules on the host

ARM detects disc insertion via udev. Create the rule file on the **host** (not inside Docker):

```bash
# Download the udev rule
sudo cp setup/51-automedia.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
```

The udev rule triggers `docker exec arm-rippers` to start a rip when a disc is inserted. If you don't have the rule file, create `/etc/udev/rules.d/51-automedia.rules`:

```
ACTION=="change", SUBSYSTEM=="block", KERNEL=="sr[0-9]*", ENV{ID_CDROM_MEDIA}=="1", \
  RUN+="/usr/bin/docker exec -d arm-rippers /opt/arm/scripts/arm_wrapper.sh %k"
```

### 6. Start the stack

```bash
# CPU-only transcoding
docker compose up -d

# With NVIDIA GPU transcoding
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

Wait for images to pull and all containers to start. Check status:

```bash
docker compose ps
```

You should see: `arm-rippers` (healthy), `arm-ui` (running), `arm-transcoder` (healthy), plus the one-shot init containers (exited).

### 7. ARM first-run configuration

On first startup, ARM creates a default `arm.yaml` in your config directory. You need to configure it:

```bash
# Edit ARM config
nano /etc/arm/config/arm.yaml
```

Key settings in `arm.yaml`:

| Setting | Purpose |
|---------|---------|
| `OMDB_API_KEY` | **Required** for movie identification. Get a free key at [omdbapi.com](https://www.omdbapi.com/apikey.aspx) |
| `TMDB_API_KEY` | Optional backup metadata source. Get at [themoviedb.org](https://www.themoviedb.org/settings/api) |
| `SKIP_TRANSCODE` | Set to `true` — the external transcoder handles this |
| `NOTIFY_RIP` | Set to `true` to get notifications when rips complete |
| `NOTIFY_TRANSCODE` | Set to `true` if using built-in transcoding |
| `RAW_PATH` | Default `/home/arm/media/raw/` — MakeMKV output |
| `COMPLETED_PATH` | Default `/home/arm/media/completed/` — final media destination |
| `MAINFEATURE` | `false` = rip all titles; `true` = main feature only |
| `MINLENGTH` / `MAXLENGTH` | Filter titles by duration (seconds) |
| `RIPMETHOD` | `mkv` (default) or `backup` (full ISO) |

After editing, restart ARM to pick up changes:

```bash
docker restart arm-rippers
```

### 8. MakeMKV registration

MakeMKV requires a beta key (free, updated monthly). The key is entered via the ARM web UI at `http://localhost:8080` or by editing `~/.MakeMKV/settings.conf` inside the container. The key is persisted in the `makemkv-settings` Docker volume.

Current beta key: check [makemkv.com/forum/viewtopic.php?t=1053](https://www.makemkv.com/forum/viewtopic.php?t=1053)

**Blu-ray decryption keys:** ARM auto-downloads the community `keydb.cfg` from the FindVUK Online Database (`fvonline-db.bplaced.net`) at container startup. This provides Volume Unique Keys (VUKs) needed for Blu-ray disc decryption. The script (`scripts/update_keydb.sh`) uses the non-Russian `bplaced.net` mirror instead of the original Russian-hosted FindVUK site, which is geoblocked in some regions. The keydb is cached for 7 days and can be disabled via `MAKEMKV_COMMUNITY_KEYDB: false` in `arm.yaml`.

### 9. Verify everything works

```bash
# ARM legacy web UI (should show the dashboard)
curl -s http://localhost:8080 | head -5

# New UI dashboard
curl -s http://localhost:8888 | head -5

# Transcoder health check
curl -s http://localhost:5000/health | python3 -m json.tool
```

Open `http://<your-ip>:8888` in a browser for the UI dashboard.

Insert a disc — ARM should detect it automatically and start ripping.

### Service Ports

| Port | Service | Purpose |
|------|---------|---------|
| 8080 | arm-rippers | ARM legacy Flask UI |
| 8888 | arm-ui | New SvelteKit dashboard |
| 5000 | arm-transcoder | Transcoder API + webhook receiver |

### Compose Files

| File | Use case |
|------|----------|
| `docker-compose.yml` | All-in-one (ARM + UI + Transcoder), CPU-only |
| `docker-compose.gpu.yml` | Overlay — adds NVIDIA GPU to transcoder |
| `docker-compose.remote-transcoder.yml` | Split — ARM + UI only, transcoder on another machine |
| `docker-compose.dev.yml` | Overlay — builds from local source for development |

### Troubleshooting

- **No disc detection / drive not visible in container**: The most common cause is the `devices:` block in `docker-compose.yml` is still commented out. Uncomment it and map your drives (e.g. `- /dev/sr0:/dev/sr0`). Verify drives exist on the host with `ls -la /dev/sr*`. Also check udev rules are installed on the host and `arm-rippers` is running with `privileged: true`
- **Permission errors on media dirs**: Ensure `ARM_UID`/`ARM_GID` match the owner of your host directories
- **Transcoder fails to start with GPU**: Install `nvidia-container-toolkit`, check `nvidia-smi` works on host
- **UI shows "ARM Offline"**: Check `arm-rippers` is healthy (`docker compose ps`); the UI waits for ARM's healthcheck
- **Movies not identified**: Set `OMDB_API_KEY` in `arm.yaml` — without it, discs rip but use the disc label as the title

## Development Workflow

### Three Sibling Repos

Development uses three git repositories cloned as siblings:

```
~/src/
  automatic-ripping-machine-neu/        # ARM ripper (this repo)
  automatic-ripping-machine-ui/          # UI dashboard (SvelteKit + FastAPI)
  automatic-ripping-machine-transcoder/  # GPU transcoding service
```

**The `components/ui/` and `components/transcoder/` directories are git submodules auto-updated by CI. They are always behind the working copies. NEVER build from submodules. NEVER manually update submodule pointers.**

### Prerequisites

- Docker Engine + Docker Compose v2
- Node.js >= 20 (for building the UI frontend; v24 recommended)
- Three sibling repos cloned (see above)

### First-Time Dev Setup

```bash
# 1. Create .env from the example and adjust for CPU-only dev
cp .env.example .env
# Edit .env: set VIDEO_ENCODER=x265 (unless you have an NVIDIA GPU)

# 2. Build the UI frontend (required before first start)
cd ../automatic-ripping-machine-ui/frontend
npm ci && npm run build
cd -

# 3. Start the dev stack
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 4. Fix dev-data permissions (Docker creates transcoder-logs as root,
#    but the transcoder container runs as UID 1001)
sudo chown -R 1001:1000 dev-data/transcoder-logs
docker restart arm-transcoder
```

### Starting the Dev Stack

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Builds from sibling repos (not submodules) and enables hot-reload:

| Service | Build From | Hot-Reload | Rebuild When |
|---------|-----------|------------|-------------|
| arm-rippers | This repo (`.`) | No | Any change |
| arm-ui | `../automatic-ripping-machine-ui/` | Yes (backend) | `requirements.txt` |
| arm-transcoder | `../automatic-ripping-machine-transcoder/` | Yes | `requirements.txt` |

### Hot-Reload

- **UI backend**: Edit `~/src/automatic-ripping-machine-ui/backend/` — uvicorn picks up changes automatically
- **UI frontend**: Run `npm run build` in `~/src/automatic-ripping-machine-ui/frontend/`, then `docker restart arm-ui`
- **Transcoder**: Edit `~/src/automatic-ripping-machine-transcoder/src/` — uvicorn picks up changes automatically
- **ARM ripper**: Requires rebuild: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build arm-rippers`

### Source Path Overrides

If repos aren't siblings, set in `.env`:
```bash
UI_SRC_PATH=/path/to/ui/repo
TRANSCODER_SRC_PATH=/path/to/transcoder/repo
```

### Dev Troubleshooting

- **UI returns connection reset / `Directory 'frontend/build/_app' does not exist`**: You need to build the frontend first — `cd ../automatic-ripping-machine-ui/frontend && npm ci && npm run build`, then `docker restart arm-ui`
- **Frontend build fails with "Vite requires Node.js version 20.19+"**: Upgrade Node.js to >= 20 on the host (v24 recommended). If using Ubuntu: `curl -fsSL https://deb.nodesource.com/setup_24.x | sudo bash - && sudo apt-get install -y nodejs`
- **Transcoder `PermissionError: Permission denied: '/data/logs/transcoder.log'`**: The `dev-data/transcoder-logs/` directory was created by Docker as root, but the transcoder runs as UID 1001. Fix with `sudo chown -R 1001:1000 dev-data/transcoder-logs && docker restart arm-transcoder`
- **`.env` variables not set warnings**: You forgot to copy `.env.example` to `.env` — run `cp .env.example .env`
