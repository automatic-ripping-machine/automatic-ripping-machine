[![CI](https://github.com/uprightbass360/automatic-ripping-machine-neu/actions/workflows/test.yml/badge.svg)](https://github.com/uprightbass360/automatic-ripping-machine-neu/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/uprightbass360/automatic-ripping-machine-neu/graph/badge.svg)](https://codecov.io/gh/uprightbass360/automatic-ripping-machine-neu)
[![GitHub release](https://img.shields.io/github/v/release/uprightbass360/automatic-ripping-machine-neu?include_prereleases)](https://github.com/uprightbass360/automatic-ripping-machine-neu/releases)
[![Docker Image](https://img.shields.io/docker/v/uprightbass360/automatic-ripping-machine?label=docker)](https://hub.docker.com/r/uprightbass360/automatic-ripping-machine)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

# Automatic Ripping Machine (ARM) - Neu

A fork of the [Automatic Ripping Machine](https://github.com/automatic-ripping-machine/automatic-ripping-machine) with many bug fixes, new features, and a companion service architecture for offloading GPU transcoding to a separate machine.

### What's different from upstream

- **Offloaded GPU transcoding** — dedicated [transcoder service](https://github.com/uprightbass360/automatic-ripping-machine-transcoder) with auto-detected GPU encoding (NVIDIA NVENC, Intel QSV, AMD VCN/VAAPI, or CPU fallback)
- **Modern dashboard** — [replacement UI](https://github.com/uprightbass360/automatic-ripping-machine-ui) built with SvelteKit, replacing the original Flask/Jinja2 templates and deployed separately.
- **TVDB episode matching** — runtime-based track-to-episode mapping for TV series discs
- **REST API** — updated structured JSON API for job management, metadata, and external integrations
- **Richer notifications** — webhook payloads include job ID, paths, video type, and env vars for custom scripts
- **Auto keydb updates** — community makemkv Blu-ray decryption keys fetched automatically at startup. No more reliance on Russian servers (unfortunately very unreliable in America)
- **Docker Compose deployment** — single-machine or split ripper/transcoder across hosts with published images. Many examples and dev overlays available.
- **Pre-scan drive detection** — richer workflow for new job reviewing
- **Many bug fixes**

## Related Projects

Part of the Automatic Ripping Machine (neu) ecosystem:

| Project | Description |
|---------|-------------|
| **automatic-ripping-machine-neu** | Fork of ARM with fixes and improvements (this project) |
| [automatic-ripping-machine-ui](https://github.com/uprightbass360/automatic-ripping-machine-ui) | Modern replacement dashboard (SvelteKit + FastAPI) |
| [automatic-ripping-machine-transcoder](https://github.com/uprightbass360/automatic-ripping-machine-transcoder) | GPU-accelerated transcoding service |

Insert an optical disc (Blu-ray, DVD, CD) and ARM automatically detects, identifies, rips, and transcodes it. Headless and server-based, designed for unattended operation with one or more optical drives. This fork adds bug fixes, better notification payloads for external service integration, and improved compatibility with the companion transcoder and UI projects.

## Screenshots

| | |
|---|---|
| ![Dashboard](screenshots/01-dashboard.png) | ![Job Detail](screenshots/15-job-detail-tracks.png) |
| Dashboard with active rips and job cards | Job detail with per-episode track status |

More screenshots and theme examples in the [UI project README](https://github.com/uprightbass360/automatic-ripping-machine-ui#screenshots).

## Features

- Automatic disc detection via udev — insert a disc and walk away
- Identifies Blu-ray, DVD, CD, and data discs automatically
- Video discs: metadata lookup via OMDb/TMDb, rips with MakeMKV, queues transcoding
- Audio CDs: rips with abcde using MusicBrainz metadata
- Data discs: creates ISO backups
- TVDB episode matching for TV series discs (runtime-based track-to-episode mapping)
- Multi-drive parallel ripping with per-drive naming
- GPU-accelerated transcoding via companion service (NVIDIA, AMD, Intel, or CPU fallback)
- Notifications via Apprise (Discord, Slack, Telegram, email, and 30+ more), Pushbullet, Pushover, IFTTT, or custom scripts
- Modern dashboard UI with real-time job tracking, file browser, and settings management
- REST API for job management and external integrations
- Automatic MakeMKV community keydb updates for Blu-ray decryption
- Docker-first deployment — single-machine or split ripper/transcoder across hosts

## Requirements

- A system capable of running Docker containers
- One or more optical drives
- Storage for your media library (local or NAS)

## Quick Start

### 1. Clone and configure

```bash
git clone --recurse-submodules https://github.com/uprightbass360/automatic-ripping-machine-neu.git
cd automatic-ripping-machine-neu
cp .env.example .env
```

Edit `.env` with your paths and settings. At minimum, set:

```bash
ARM_UID=1000
ARM_GID=1000
ARM_MUSIC_PATH=/home/arm/music
ARM_LOGS_PATH=/home/arm/logs
ARM_MEDIA_PATH=/home/arm/media
ARM_CONFIG_PATH=/etc/arm/config
```

### 2. Start the stack

```bash
# CPU-only (all three services)
docker compose up -d

# With NVIDIA GPU for transcoding
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

This pulls versioned images for all three services:

| Service | Image | Default Port |
|---------|-------|-------------|
| ARM ripper | `uprightbass360/automatic-ripping-machine` | 8080 |
| UI dashboard | `uprightbass360/arm-ui` | 8888 |
| Transcoder | `uprightbass360/arm-transcoder` | 5000 |

### 3. Verify

```bash
# ARM web interface
curl http://localhost:8080

# UI dashboard
curl http://localhost:8888

# Transcoder health
curl http://localhost:5000/health
```

Insert a disc and ARM handles the rest — rip, identify, and organize.

### Remote Transcoder

If your GPU is on a separate machine, use the split deployment:

```bash
cp .env.remote-transcoder.example .env
# Set TRANSCODER_HOST to the remote machine's IP
docker compose -f docker-compose.remote-transcoder.yml up -d
```

See the [transcoder README](https://github.com/uprightbass360/automatic-ripping-machine-transcoder) for setting up the remote side.

### Development

Clone all three repos as siblings and start the dev stack:

```bash
cd ~/src
git clone https://github.com/uprightbass360/automatic-ripping-machine-neu.git
git clone https://github.com/uprightbass360/automatic-ripping-machine-ui.git
git clone https://github.com/uprightbass360/automatic-ripping-machine-transcoder.git

cd automatic-ripping-machine-neu
cp .env.example .env  # edit as needed
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

The dev overlay builds from sibling repos and bind-mounts source for hot-reload. See `CLAUDE.md` for details.

> **Note:** `components/ui/` and `components/transcoder/` are git submodules managed by CI. Do not build from them during development.

## Docker Images

Pre-built images are published to Docker Hub and GHCR on every release:

| Component | Docker Hub | Purpose |
|-----------|-----------|---------|
| Base dependencies | `uprightbass360/arm-dependencies` | MakeMKV, system deps |
| ARM | `uprightbass360/automatic-ripping-machine` | Ripper application |
| UI | `uprightbass360/arm-ui` | Dashboard (SvelteKit + FastAPI) |
| Transcoder | `uprightbass360/arm-transcoder` | GPU-accelerated transcoding |

ARM, base dependencies, and transcoder images are built for `linux/amd64`. The UI image is multi-platform (`amd64` + `arm64`). The transcoder also publishes GPU-specific tag suffixes (`-nvidia`, `-amd`, `-intel`).

### Version Pinning

Pin all three versions in your `.env` for reproducible deployments (check each repo's releases for the latest version):

```bash
ARM_VERSION=X.Y.Z
UI_VERSION=X.Y.Z
TRANSCODER_VERSION=X.Y.Z
```

## Upstream

This project is forked from [automatic-ripping-machine/automatic-ripping-machine](https://github.com/automatic-ripping-machine/automatic-ripping-machine), originally created by Benjamin Bryan and maintained by the ARM community.

For detailed ARM configuration, see the [upstream wiki](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/).

## License

[MIT License](LICENSE)
