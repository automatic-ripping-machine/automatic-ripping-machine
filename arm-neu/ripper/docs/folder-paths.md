# Configuration Reference

Comprehensive map of every host -> container path, env var, `arm.yaml` key,
and runtime override across the three services (arm-rippers, arm-transcoder,
arm-ui), including scratch/temp paths and the layering model that decides
which knob wins.

> **Conventions**
> - "Container path" = path inside the container (what code sees).
> - "Host path" = path on the host (what `docker compose` mounts from).
> - `${VAR}` shows the env var; `${VAR:-default}` shows its fallback.
> - Bind-mount targets that don't exist on the host are auto-created by Docker
>   as root - the entrypoints `chown` them where possible.

## Table of contents

- [Part A: How configuration layers](#part-a-how-configuration-layers)
  - [1. ARM ripper precedence](#1-arm-ripper-precedence)
  - [2. arm-transcoder precedence](#2-arm-transcoder-precedence)
  - [3. arm-ui precedence](#3-arm-ui-precedence)
  - [4. Cross-cutting wires (auth, UID/GID, GPU)](#4-cross-cutting-wires)
- [Part B: Per-service paths and env](#part-b-per-service-paths-and-env)
  - [5. arm-rippers](#5-arm-rippers)
  - [6. arm-transcoder](#6-arm-transcoder)
  - [7. arm-ui (BFF)](#7-arm-ui-bff)
- [Part C: Scratch, temp, and ephemeral paths](#part-c-scratch-temp-and-ephemeral-paths)
  - [8. ARM scratch staging (LOCAL_RAW -> SHARED_RAW)](#8-arm-scratch-staging-local_raw---shared_raw)
  - [9. Transcoder work dir + other temp paths](#9-transcoder-work-dir--other-temp-paths)
- [Part D: Deployment variants](#part-d-deployment-variants)
  - [10. Production (all-in-one)](#10-production-all-in-one)
  - [11. Ripper-only](#11-ripper-only)
  - [12. Remote transcoder](#12-remote-transcoder)
  - [13. Dev overlay](#13-dev-overlay)
  - [14. NFS-readiness overlay](#14-nfs-readiness-overlay)
- [Part E: Skim tables](#part-e-skim-tables)
  - [15. Where does X live?](#15-where-does-x-live)
  - [16. Where do I change X?](#16-where-do-i-change-x)
  - [17. Env var quick index](#17-env-var-quick-index)

---

## Part A: How configuration layers

Each service has its own precedence chain. Getting this wrong is the usual
cause of "I changed it and nothing happened."

### 1. ARM ripper precedence

Three layers, last one wins:

1. **Image defaults** baked into `setup/arm.yaml` (template; copied on first
   boot when no `arm.yaml` exists in the config volume).
2. **`arm.yaml`** at `/etc/arm/config/arm.yaml` (operator config). The
   container migrates new keys in from the template on every startup
   (`arm/config/config.py:43-79`), so upgrading never loses your
   customizations but new defaults appear automatically.
3. **Env-driven yaml rewrites** applied by `arm_user_files_setup.sh:160-187`
   BEFORE the Python process starts. Only these env vars rewrite
   `arm.yaml` keys:

   | Env var | -> arm.yaml key |
   |---|---|
   | `ARM_TRANSCODER_URL` | `TRANSCODER_URL` |
   | `ARM_TRANSCODER_WEBHOOK_SECRET` | `TRANSCODER_WEBHOOK_SECRET` |
   | `ARM_LOCAL_RAW_PATH` | `LOCAL_RAW_PATH` |
   | `ARM_SHARED_RAW_PATH` | `SHARED_RAW_PATH` |
   | `MOVIES_SUBDIR` | `MOVIES_SUBDIR` |
   | `TV_SUBDIR` | `TV_SUBDIR` |
   | `AUDIO_SUBDIR` | `AUDIO_SUBDIR` |
   | `UNIDENTIFIED_SUBDIR` | `UNIDENTIFIED_SUBDIR` |
   | `ARM_TRANSCODER_ENABLED=false` | force-clears `TRANSCODER_URL` + `TRANSCODER_WEBHOOK_SECRET` |

   The four `*_SUBDIR` env vars match their yaml-key names (no `ARM_`
   prefix) because they're shared with the transcoder service, which
   uses the same env names. One env var per concept, both services
   honor it.

A few env vars are read directly by Python (no yaml hop):

| Env var | Where read | Default |
|---|---|---|
| `ARM_CONFIG_FILE` | `arm/config/config.py:15` | `/etc/arm/config/arm.yaml` |
| `ARM_DATABASE_URL` | `arm/config/config.py:108` (`get_db_uri`) | unset -> yaml `DATABASE_URL` -> `sqlite:///${DBFILE}` |
| `ARM_UID` / `ARM_GID` | `arm/services/file_browser.py:432-433` | `1000` / `1000` |
| `ARM_MEDIA_PATH` / `ARM_CONFIG_PATH` / `ARM_LOGS_PATH` / `ARM_MUSIC_PATH` | `arm/services/preflight.py:19-24` | (host-path resolution fallback) |
| `TZ` | `/etc/localtime` symlink in entrypoint | `Etc/UTC` |

**Per-job overrides**: the disc-review panel can write
`job.transcode_overrides` (JSON column; validated via
`arm_contracts.TranscodeJobConfig` in `arm/api/v1/jobs.py:853-872`). These
do NOT mutate `arm.yaml` - they ride on the outbound webhook and override
the transcoder's preset/global config for that one job.

### 2. arm-transcoder precedence

Three layers, last one wins:

1. **`Settings` defaults** in `src/config.py:39-131` (pydantic-settings,
   `env_prefix=""`, case-insensitive).
2. **Env vars** at process startup (every `Settings` field is env-driven).
3. **DB-persisted overrides** in the `config_overrides` table, loaded by
   `load_config_overrides()` and patched onto the singleton
   (`src/config.py:168-245`). The UI's settings page writes here via
   `PATCH /config`.

> **Important**: Only fields in `UPDATABLE_KEYS` (~14 fields, mostly
> preset/file/concurrency knobs) can be changed via the API. Path fields
> (`raw_path`, `completed_path`, ...), auth fields, and GPU fields are
> env-only - rebuild required to change them.

Env vars consumed outside the `Settings` model:

| Env var | Where read | Notes |
|---|---|---|
| `GPU_VENDOR` | `presets/__init__.py:161`, `main.py:95` | Baked at image build (see [section 4](#4-cross-cutting-wires)) |
| `VAAPI_DEVICE` | `transcoder.py:135,1566` | AMD/Intel only; default `/dev/dri/renderD128` |
| `FAKE_GPU_STATS` | `routers/health.py:106` | Test hook to short-circuit live GPU monitoring |

**Per-job overrides**: each ARM webhook can include a `config_overrides`
field that acts as a one-shot `Settings`-shaped patch for that job. Stored
as part of the job row; never written back to env or DB defaults.

### 3. arm-ui precedence

One layer, env-only, loaded once at startup (`backend/config.py:1-17`):

- Pydantic `Settings` with `env_prefix="ARM_UI_"`.
- All fields are env-driven (paths, URLs, secrets, port).
- **No runtime mutation API.** Secret rotation requires a container restart
  (memory: `feedback_arm_ui_webhook_secret_load_once.md`).

### 4. Cross-cutting wires

#### Webhook secret (ARM <-> transcoder, UI -> transcoder)

Same value on the wire, different name at every hop:

```
.env: WEBHOOK_SECRET=<value>
       │
       ├─> arm-rippers env: ARM_TRANSCODER_WEBHOOK_SECRET=<value>
       │     └─> arm.yaml: TRANSCODER_WEBHOOK_SECRET: "<value>"
       │           └─> outbound HTTP header: X-Webhook-Secret: <value>
       │
       ├─> arm-transcoder env: WEBHOOK_SECRET=<value>
       │     └─> Settings.webhook_secret -> auth check on inbound webhook
       │
       └─> arm-ui env: ARM_UI_TRANSCODER_WEBHOOK_SECRET=<value>
             └─> Settings.transcoder_webhook_secret -> outbound HTTP from UI to transcoder
```

#### API auth (UI -> transcoder)

Independent from webhook auth:

```
.env: API_KEYS=<csv>           -> transcoder env: API_KEYS
      REQUIRE_API_AUTH=<bool>  -> transcoder env: REQUIRE_API_AUTH
      TRANSCODER_API_KEY=<v>   -> arm-ui env:    ARM_UI_TRANSCODER_API_KEY
                                                  (presented by UI -> transcoder)
```

#### UID / GID propagation

```
.env: ARM_UID=1000  ARM_GID=1000
       │
       ├─> arm-rippers: ARM_UID, ARM_GID
       │     └─> usermod/groupmod the `arm` user at boot
       │         (arm_user_files_setup.sh:47-61)
       │     └─> chown of /opt/arm + /home/arm subdirs
       │     └─> Python reads ARM_UID/ARM_GID for file_browser ownership
       │         checks (services/file_browser.py:432-433)
       │
       ├─> arm-db-init (one-shot): chowns named volume /data/db to
       │     ARM_UID:ARM_GID before arm-rippers boots
       │
       └─> arm-transcoder: TRANSCODER_UID=ARM_UID, TRANSCODER_GID=ARM_GID
             └─> entrypoint usermod the transcoder user
             └─> arm-transcoder-init (one-shot) chowns ${WORK_PATH}
                 to ARM_UID:ARM_GID before transcoder boots
```

> **Why two init containers?** Docker creates bind-mount targets as root,
> and the in-container entrypoint can't recursively chown a root-owned
> mount root that it doesn't itself own. The one-shot init containers
> sidestep this by running as actual root.

#### GPU vendor (transcoder, image-build time)

| Image tag | `GPU_VENDOR` baked in | Compose adds |
|---|---|---|
| `latest` | (unset, software x265) | - |
| `latest-nvidia` | `nvidia` (`Dockerfile.nvidia:8`) | `runtime: nvidia` + GPU device reservation (`docker-compose.gpu.yml`) |
| `latest-amd` | `amd` (`Dockerfile.amd:9`) | `VAAPI_DEVICE=/dev/dri/renderD128` + `/dev/dri` mount |
| `latest-intel` | `intel` (`Dockerfile.intel:18`, also `LIBVA_DRIVER_NAME=iHD`) | `VAAPI_DEVICE=/dev/dri/renderD128` + `/dev/dri` mount |

#### Preflight host-path resolution

`arm/services/preflight.py:19-54` maps container paths back to host paths
for the setup wizard / health dashboard. Two strategies in order:

1. **Strategy 1 (preferred)**: parse `/proc/self/mountinfo` for the bind
   source.
2. **Strategy 2 (fallback)**: env-var prefix mapping:
   ```
   /home/arm/media   -> $ARM_MEDIA_PATH
   /etc/arm/config   -> $ARM_CONFIG_PATH
   /home/arm/logs    -> $ARM_LOGS_PATH
   /home/arm/music   -> $ARM_MUSIC_PATH
   ```

This is why the compose `arm-rippers` service explicitly passes
`ARM_MEDIA_PATH`/`ARM_CONFIG_PATH`/`ARM_LOGS_PATH`/`ARM_MUSIC_PATH` into the
container env even though they're already used at the volume layer - the
container needs them at runtime for the fallback.

---

## Part B: Per-service paths and env

### 5. arm-rippers

#### 5.1 arm.yaml keys (container paths)

`arm.yaml` lives at `/etc/arm/config/arm.yaml`. Read by `arm.config.config`
and consumed throughout ripper code.

| Key | Default | Purpose |
|---|---|---|
| `INSTALLPATH` | `/opt/arm/` | ARM Python source root |
| `RAW_PATH` | `/home/arm/media/raw/` | MakeMKV output (one subdir per job) |
| `TRANSCODE_PATH` | `/home/arm/media/transcode/` | Read-only view of transcoder work dir (file browser only) |
| `COMPLETED_PATH` | `/home/arm/media/completed/` | Final ripped/transcoded files |
| `MUSIC_PATH` | `/home/arm/music/` | abcde audio CD output |
| `INGRESS_PATH` | `""` (mount defaults to `/home/arm/media/ingress`) | Folder import root - file browser is scoped here for BDMV/VIDEO_TS |
| `LOGPATH` | `/home/arm/logs/` | All logs |
| `DBFILE` | `/home/arm/db/arm.db` | SQLite DB (DSN-pluggable since Phase 3 PR-A) |
| `ABCDE_CONFIG_FILE` | `/etc/arm/config/abcde.conf` | abcde config |
| `EXTRAS_SUB` | `extras` | Movie extras subdir name |
| `LOCAL_RAW_PATH` / `SHARED_RAW_PATH` | `""` / `""` | Scratch staging - see [section 8](#8-arm-scratch-staging-local_raw---shared_raw) |
| `MOVIES_SUBDIR` / `TV_SUBDIR` / `AUDIO_SUBDIR` / `UNIDENTIFIED_SUBDIR` | `movies` / `tv` / `music` / `unidentified` | Per-video-type subdirs under `COMPLETED_PATH` and `TRANSCODE_PATH`. Honored by both ARM ripper (via `Job.type_subfolder`) and transcoder. Slashes allowed for nested layouts. |

#### 5.2 Host -> container mounts

From `docker-compose.yml`, populated by `.env`:

| Env var | Default (host) | Container mount |
|---|---|---|
| `ARM_MUSIC_PATH` | `/home/arm/music` | `/home/arm/music` |
| `ARM_LOGS_PATH` | `/home/arm/logs` | `/home/arm/logs` |
| `ARM_MEDIA_PATH` | `/home/arm/media` | `/home/arm/media` (also reused by transcoder for `raw/` + `completed/`) |
| `ARM_CONFIG_PATH` | `/etc/arm/config` | `/etc/arm/config` |
| `ARM_MAKEMKV_PATH` | `/home/arm/.MakeMKV` (or named volume `makemkv-settings`) | `/home/arm/.MakeMKV` |
| `ARM_SCRATCH_PATH` | falls back to `${ARM_MEDIA_PATH}` | `/home/arm/scratch` |
| `ARM_INGRESS_PATH` | `/home/arm/media/ingress` | `/home/arm/media/ingress` (`:ro`) |
| `TRANSCODER_WORK_PATH` | `./work` | `/home/arm/media/transcode` (`:ro`, file browser only) |
| named volume `arm-db` | docker-managed | `/home/arm/db` |
| `/dev:/dev` | (live) | `/dev` (USB optical hot-plug) |

> **Note** - `ARM_SCRATCH_PATH` is mounted unconditionally. When unset it
> aliases the media path so the LOCAL_RAW/SHARED_RAW staging logic still
> works without a real SSD.

#### 5.3 Subdirs auto-created at startup

`arm_user_files_setup.sh:82` ensures these exist (created as the `arm` user
so NFS root_squash doesn't leave them root-owned):

```
/home/arm/media
/home/arm/media/completed
/home/arm/media/raw
/home/arm/media/movies
/home/arm/media/transcode    # mountpoint for read-only transcoder work bind
/home/arm/logs
/home/arm/logs/progress      # MakeMKV heartbeat + per-job progress logs
/home/arm/db
/home/arm/music
/home/arm/.MakeMKV
```

### 6. arm-transcoder

#### 6.1 Container paths (env-driven, fixed by compose)

Settings keys are env-driven but the production composes pin them to the
canonical container locations - the host bind decides where data lives.

| Container path | Env var | Purpose |
|---|---|---|
| `/data/raw` | `RAW_PATH` | Where ARM dropped the raw MakeMKV output |
| `/data/completed` | `COMPLETED_PATH` | Final transcoded output |
| `/data/work` | `WORK_PATH` | **Scratch**: in-flight HandBrake/FFmpeg working dir |
| `/data/db/transcoder.db` | `DB_PATH` | Transcoder SQLite (jobs + pending callbacks) |
| `/data/logs` | `LOG_PATH` | Transcoder logs |
| `/config/presets` | (no env, fixed) | Read-only preset definitions |

#### 6.2 Host -> container mounts (all-in-one)

From `docker-compose.yml` in arm-neu:

| Host source | Container target |
|---|---|
| `${ARM_MEDIA_PATH}/raw` | `/data/raw` (rw) |
| `${ARM_MEDIA_PATH}/completed` | `/data/completed` (rw) |
| `${TRANSCODER_WORK_PATH:-./work}` | `/data/work` (rw, also re-mounted `:ro` into ripper as `/home/arm/media/transcode`) |
| named volume `transcoder-db` | `/data/db` |
| named volume `transcoder-logs` | `/data/logs` |
| `${TRANSCODER_PRESET_PATH:-./presets}` | `/config/presets` (`:ro`) |

#### 6.3 Host -> container mounts (standalone repo compose)

From `docker-compose.yml` in arm-transcoder repo:

| Host source | Container target |
|---|---|
| `${HOST_RAW_PATH:-./raw}` | `/data/raw` |
| `${HOST_COMPLETED_PATH:-./completed}` | `/data/completed` |
| `${WORK_PATH:-./work}` | `/data/work` |
| `${DB_PATH:-./data}` | `/data/db` |
| `${LOG_PATH:-./logs}` | `/data/logs` |
| `${PRESET_PATH:-./presets}` | `/config/presets` (`:ro`) |

#### 6.4 Cross-service path consistency

`RAW_PATH` and `COMPLETED_PATH` MUST resolve to the same files on both
sides. The all-in-one compose enforces this by binding
`${ARM_MEDIA_PATH}/raw` and `${ARM_MEDIA_PATH}/completed` to both
containers. Webhook payloads carry container-relative basenames
(`raw_basename = os.path.basename(job.raw_path)`) so the transcoder
re-resolves them under its own `/data/raw`.

For split deployments (NFS), the host paths can differ - what matters is
that the **container paths are identical**.

### 7. arm-ui (BFF)

The UI has zero filesystem coupling to the ripper since v17.3 (Phase 2).
All ripper data flows over REST.

#### 7.1 Env (all `ARM_UI_*` prefixed via pydantic-settings)

`backend/config.py`:

| Env var | Default | Purpose |
|---|---|---|
| `ARM_UI_THEMES_PATH` | `/data/themes` | Custom theme JSON storage |
| `ARM_UI_IMAGE_CACHE_PATH` | `/data/cache/images` | Poster/thumbnail cache |
| `ARM_UI_ARM_URL` | `http://localhost:8080` | URL of arm-rippers |
| `ARM_UI_TRANSCODER_URL` | `http://localhost:5000` | URL of arm-transcoder |
| `ARM_UI_TRANSCODER_API_KEY` | `""` | API key for transcoder |
| `ARM_UI_TRANSCODER_WEBHOOK_SECRET` | `""` | **Loads once at startup**; rotation requires restart |
| `ARM_UI_TRANSCODER_ENABLED` | `True` | Hide transcoder UI when false |
| `ARM_UI_PORT` | `8888` | HTTP listen port |

#### 7.2 Container mounts

| Host source | Container target |
|---|---|
| named volume `arm-ui-themes` | `/data/themes` (rw) |
| named volume `ui-image-cache` | `/data/cache/images` (rw) |

---

## Part C: Scratch, temp, and ephemeral paths

### 8. ARM scratch staging (LOCAL_RAW -> SHARED_RAW)

Two `arm.yaml` keys, both empty by default. When **both** are set, ARM rips
to a fast local SSD then rsyncs to shared storage before notifying the
transcoder.

| Key | Typical | Role |
|---|---|---|
| `LOCAL_RAW_PATH` | e.g. `/home/arm/scratch/raw/` | Fast local SSD - MakeMKV output target |
| `SHARED_RAW_PATH` | e.g. `/home/arm/media/raw/` | NFS/shared - final raw destination read by transcoder |

**Mechanics** (`arm/ripper/utils.py:141-189`, `_move_to_shared_storage`):

1. Job rips to `${LOCAL_RAW_PATH}/<basename>/`.
2. After rip finishes, ARM forks `rsync -a --remove-source-files` to copy
   to `${SHARED_RAW_PATH}/<basename>/`. The subprocess shields the API
   event loop from NFS D-state stalls.
3. `job.raw_path` is rewritten to the shared location and committed.
4. Webhook fires; transcoder reads from its `/data/raw` mount.
5. Empty source dirs are then `shutil.rmtree`'d.

> If only one of the two is set, the move is a no-op (the rip just lands
> wherever `LOCAL_RAW_PATH` or `RAW_PATH` resolved to). Setting **both** is
> the opt-in switch.

**Compose plumbing** (`.env`):

```
ARM_SCRATCH_PATH=/mnt/ssd/arm-scratch          # HOST path -> /home/arm/scratch
ARM_LOCAL_RAW_PATH=/home/arm/scratch/raw       # CONTAINER path (-> arm.yaml LOCAL_RAW_PATH)
ARM_SHARED_RAW_PATH=/home/arm/media/raw        # CONTAINER path (-> arm.yaml SHARED_RAW_PATH)
```

- `ARM_SCRATCH_PATH` is the **host** path bound to `/home/arm/scratch`.
- `ARM_LOCAL_RAW_PATH` and `ARM_SHARED_RAW_PATH` are propagated into
  `arm.yaml` by the entrypoint and refer to **container** paths.

### 9. Transcoder work dir + other temp paths

#### 9.1 Transcoder `WORK_PATH`

`/data/work` is the transcoder's HandBrake working directory. It's the
ONLY transcoder-side scratch path. Recommended to bind to a fast local
SSD (`TRANSCODER_WORK_PATH=./work` is fine for a single-host deployment
but should be a real SSD for production).

The all-in-one compose also re-mounts this into the ripper as
`/home/arm/media/transcode:ro` purely so the file browser can show
in-progress transcodes - the ripper never writes here.

`arm-transcoder-init` (one-shot) chowns `/data/work` to `ARM_UID:ARM_GID`
before the transcoder boots, because Docker creates bind-mount targets as
root.

#### 9.2 Other temp/scratch

| Path | Owner | Purpose |
|---|---|---|
| `/home/arm/logs/progress/.makemkv_heartbeat_<pid>` | ripper (`makemkv.py:1846`) | MakeMKV liveness heartbeat - watchdog kills stalled rips |
| `/home/arm/logs/faulthandler.log` | ripper (`main.py:26`) | Python `faulthandler` C-stack dumps |
| `/tmp/abcde_custom_*.conf` | ripper (`utils.py:705-747`) | Per-rip abcde config override (`tempfile.NamedTemporaryFile`) |
| `/dev/shm/...` | abcde / cdparanoia | OS-level scratch for CD ripping (not configured by us) |
| `/tmp/...` | various Python libs | Default `tempfile` location; not pinned |

#### 9.3 Dev cache (host-only)

| Host path | Purpose |
|---|---|
| `./dev-data/cache/` | Workspace-local dev artifacts |
| `./dev-data/cache/images/` | Dev arm-ui image cache (replaces named volume `ui-image-cache`) |

---

## Part D: Deployment variants

### 10. Production (all-in-one)

`docker-compose.yml` + `.env`. Three services on one host:

- `arm-rippers` (privileged, `/dev` mounted)
- `arm-transcoder` (optionally with `docker-compose.gpu.yml` overlay)
- `arm-ui`

Plus two one-shot init containers (`arm-db-init`, `arm-transcoder-init`)
that chown bind-mount roots before the long-running services boot.

See sections [5](#5-arm-rippers), [6](#6-arm-transcoder), [7](#7-arm-ui-bff)
for path tables.

### 11. Ripper-only

`docker-compose.ripper-only.yml` + `.env.ripper-only.example`.

Same ripper paths as production. **No transcoder service.** UI runs with
`ARM_UI_TRANSCODER_ENABLED=false`. The ripper entrypoint sees
`ARM_TRANSCODER_ENABLED=false` and force-clears `TRANSCODER_URL` +
`TRANSCODER_WEBHOOK_SECRET` in `arm.yaml`. ARM falls into the
`finalize_output` path - writes named files directly to `COMPLETED_PATH`,
skipping the transcoder roundtrip entirely.

Notably **no** `TRANSCODER_WORK_PATH` mount, since there's no
`/home/arm/media/transcode` source.

### 12. Remote transcoder

`docker-compose.remote-transcoder.yml` + `.env.remote-transcoder.example`.

Ripper + UI on this host; transcoder on a remote box running its own
compose from the arm-transcoder repo with its own NFS/SMB mount of the
same shared storage.

- `TRANSCODER_HOST` / `TRANSCODER_PORT` (env, ripper-side) build
  `ARM_TRANSCODER_URL=http://${TRANSCODER_HOST}:${TRANSCODER_PORT}/webhook/arm`.
- `WEBHOOK_SECRET` must match on both ends.
- Shared storage is the contract: both hosts must mount the same media
  share at `/home/arm/media` (ripper) and `/data/raw` + `/data/completed`
  (transcoder).

### 13. Dev overlay

`docker-compose.dev.yml` (overlay on top of production compose). Live-reload
from sibling source repos.

| Host source | Container target | Service |
|---|---|---|
| `./dev-data/music` | `/home/arm/music` | arm-rippers |
| `./dev-data/logs` | `/home/arm/logs` | arm-rippers |
| `./dev-data/config` | `/etc/arm/config` | arm-rippers |
| `./dev-data/makemkv` | `/home/arm/.MakeMKV` | arm-rippers |
| `${UI_SRC_PATH:-../automatic-ripping-machine-ui}/backend` | `/app/backend` (`:ro`) | arm-ui (uvicorn `--reload`) |
| `${UI_SRC_PATH:-...}/frontend/build` | `/app/frontend/build` (`:ro`) | arm-ui |
| `./dev-data/cache/images` | `/data/cache/images` (rw) | arm-ui |
| `${TRANSCODER_SRC_PATH:-../automatic-ripping-machine-transcoder}/src` | `/app` (rw) | arm-transcoder (uvicorn `--reload`) |
| `${TRANSCODER_SRC_PATH:-...}/components/contracts` | `/app/components/contracts` (`:ro`) | arm-transcoder (re-mount required) |
| `${TRANSCODER_SRC_PATH:-...}/presets` | `/config/presets` (`:ro`) | arm-transcoder |
| `./dev-data/transcoder-logs` | `/data/logs` (rw) | arm-transcoder |

> **Media path is intentionally NOT overridden** so the dev transcoder can
> find ripped files on the shared NFS mount.

> **Gotcha**: the `/app` bind shadows the image's `/app/components`, which
> the editable install's `.pth` file points at. Without the
> `components/contracts` re-mount, `import arm_contracts` fails inside the
> dev transcoder container.

### 14. NFS-readiness overlay

`docker-compose.nfs.yml` (opt-in overlay). Apply on top of any primary
compose for NFS-backed deployments where docker may start before NFS is
mounted.

```bash
docker compose -f docker-compose.yml                    -f docker-compose.nfs.yml up -d
docker compose -f docker-compose.remote-transcoder.yml  -f docker-compose.nfs.yml up -d
docker compose -f docker-compose.ripper-only.yml        -f docker-compose.nfs.yml up -d
```

**What it does**: adds an `arm-nfs-check` init container that fails
fast if the sentinel file `${ARM_MEDIA_PATH}/.arm-nfs-heartbeat` is
not visible. `arm-rippers` `depends_on` it, so it won't start (and
won't silently fossilize binds to local disk) if NFS isn't mounted.

**One-time setup**: on the NFS server, `touch
<share-path>/.arm-nfs-heartbeat`.

**Why this matters**: when `_netdev` in `/etc/fstab` doesn't gate
docker's start order, a host reboot can leave docker running with
binds captured against the empty local-disk shadow of an unmounted NFS
path. Rips land on local disk, the remote transcoder never sees them,
jobs fail with "Source path does not exist". The overlay turns this
silent failure into a loud refusal-to-start.

---

## Part E: Skim tables

### 15. Where does X live?

| Concept | Container | Host (default) |
|---|---|---|
| Raw MakeMKV output | `/home/arm/media/raw/` | `${ARM_MEDIA_PATH}/raw/` |
| Final transcoded files (root) | `/home/arm/media/completed/` | `${ARM_COMPLETED_PATH:-${ARM_MEDIA_PATH}/completed}` |
| Movie output | `/home/arm/media/completed/${MOVIES_SUBDIR}/<title>/` | `${ARM_COMPLETED_PATH:-${ARM_MEDIA_PATH}/completed}/${MOVIES_SUBDIR}/<title>/` |
| TV output | `/home/arm/media/completed/${TV_SUBDIR}/<show>/Season N/` | `${ARM_COMPLETED_PATH:-${ARM_MEDIA_PATH}/completed}/${TV_SUBDIR}/<show>/...` |
| Audio CD output | `/home/arm/media/completed/${AUDIO_SUBDIR}/<artist>/<album>/` | `${ARM_COMPLETED_PATH:-${ARM_MEDIA_PATH}/completed}/${AUDIO_SUBDIR}/...` |
| Music CDs (raw rip target) | `/home/arm/music/` | `${ARM_MUSIC_PATH}` |
| ARM SQLite | `/home/arm/db/arm.db` | named volume `arm-db` |
| Transcoder SQLite | `/data/db/transcoder.db` | named volume `transcoder-db` |
| ARM logs | `/home/arm/logs/` | `${ARM_LOGS_PATH}` (recommend local; avoid NFS for in-progress rip log writes) |
| Transcoder logs | `/data/logs/` | named volume `transcoder-logs` |
| ARM config (`arm.yaml`, `apprise.yaml`, `abcde.conf`) | `/etc/arm/config/` | `${ARM_CONFIG_PATH}` |
| MakeMKV settings + keydb | `/home/arm/.MakeMKV/` | named volume `makemkv-settings` (or `${ARM_MAKEMKV_PATH}`) |
| Folder import sources | `/home/arm/media/ingress/` (`:ro`) | `${ARM_INGRESS_PATH}` |
| Local SSD scratch (rip target) | `/home/arm/scratch/raw/` | `${ARM_SCRATCH_PATH}/raw/` |
| Transcoder work scratch | `/data/work/` | `${TRANSCODER_WORK_PATH}` |
| Transcoder presets | `/config/presets/` (`:ro`) | `${TRANSCODER_PRESET_PATH}` |
| UI themes | `/data/themes/` | named volume `arm-ui-themes` |
| UI image cache | `/data/cache/images/` | named volume `ui-image-cache` |
| MakeMKV heartbeat / faulthandler | `/home/arm/logs/progress/` + `faulthandler.log` | `${ARM_LOGS_PATH}/...` |
| abcde tmp config | `/tmp/abcde_custom_*.conf` | (ephemeral, container tmpfs) |

### 16. Where do I change X?

| Setting | Source of truth | How to change |
|---|---|---|
| Folder paths inside ripper container | `arm.yaml` | Edit `/etc/arm/config/arm.yaml` (or via UI Settings, which writes back to yaml) |
| Folder paths inside transcoder container | env vars | Edit `.env`, `docker compose up -d --force-recreate arm-transcoder` |
| Host -> container mounts | `.env` + `docker-compose*.yml` | Edit `.env`, `docker compose up -d` |
| Transcoder webhook URL/secret | env (`ARM_TRANSCODER_URL`, `WEBHOOK_SECRET`) | Edit `.env`, restart ripper. Entrypoint rewrites `arm.yaml` on every boot. |
| Scratch staging | env (`ARM_LOCAL_RAW_PATH` + `ARM_SHARED_RAW_PATH`) | Edit `.env`, restart ripper |
| GPU vendor | image tag (`TRANSCODER_VERSION=latest-nvidia` etc.) | Switch tag, `docker compose up -d --force-recreate arm-transcoder` |
| Transcoder presets / file handling / concurrency | DB (preferred) or env defaults | UI Settings page (writes via `PATCH /config`); env only sets the boot default |
| Library subdir layout (movies/tv/audio dirs) | `arm.yaml` (via env) | Edit `.env` (`MOVIES_SUBDIR=Movies/0.Rips` etc.), restart ripper. Entrypoint rewrites `arm.yaml`; both ARM and transcoder honor the same value. |
| Per-job transcode overrides | DB column `job.transcode_overrides` | UI disc-review panel; one-shot, attaches to outbound webhook only |
| Database URL | env `ARM_DATABASE_URL` -> yaml `DATABASE_URL` -> default sqlite | Either env or yaml; Phase 3 PR-A landed 2026-05-03 |
| UI themes / image cache paths | env (`ARM_UI_THEMES_PATH`, `ARM_UI_IMAGE_CACHE_PATH`) | Edit compose, restart UI |
| UI -> transcoder credentials | env (`ARM_UI_TRANSCODER_API_KEY`, `ARM_UI_TRANSCODER_WEBHOOK_SECRET`) | Edit `.env`, **restart UI** (loaded once - rotation needs a restart) |

### 17. Env var quick index

| Env var | Read by | Notes |
|---|---|---|
| `ARM_VERSION`, `UI_VERSION`, `TRANSCODER_VERSION` | docker-compose only | Image tag pinning |
| `TRANSCODER_HOST`, `TRANSCODER_PORT` | `docker-compose.remote-transcoder.yml` | Construct `ARM_TRANSCODER_URL` and `ARM_UI_TRANSCODER_URL` for split deployments |
| `ARM_UID`, `ARM_GID` | ripper entrypoint, `file_browser.py`, init containers | UID/GID alignment |
| `TRANSCODER_UID`, `TRANSCODER_GID` | transcoder entrypoint | Should match `ARM_UID`/`ARM_GID` |
| `TZ` | All three entrypoints (symlinks `/etc/localtime`) | Also re-baked into tzdata |
| `ARM_COMMUNITY_KEYDB` | ripper entrypoint (`arm_user_files_setup.sh:119`) + `update_keydb.sh` | Gates the FindVUK download |
| `ARM_CONFIG_FILE` | `arm/config/config.py:15` | Rare override; set in dev only |
| `ARM_DATABASE_URL` | `arm/config/config.py:108` | Postgres readiness PR-A |
| `ARM_TRANSCODER_ENABLED` | ripper entrypoint | Force-clears yaml when `false` |
| `ARM_TRANSCODER_URL` | ripper entrypoint -> yaml | Webhook target |
| `ARM_TRANSCODER_WEBHOOK_SECRET` | ripper entrypoint -> yaml | Shared secret |
| `ARM_LOCAL_RAW_PATH`, `ARM_SHARED_RAW_PATH` | ripper entrypoint -> yaml | Scratch staging |
| `MOVIES_SUBDIR`, `TV_SUBDIR`, `AUDIO_SUBDIR`, `UNIDENTIFIED_SUBDIR` | ripper entrypoint -> yaml; transcoder Settings | Library subdir layout - shared between services |
| `ARM_COMPLETED_PATH` | compose volume layer | Optional host-path override; binds to `/home/arm/media/completed` (ripper) and `/data/completed` (transcoder) |
| `ARM_MEDIA_PATH`, `ARM_CONFIG_PATH`, `ARM_LOGS_PATH`, `ARM_MUSIC_PATH` | preflight.py fallback + compose volume layer | Passed twice on purpose |
| `ARM_SCRATCH_PATH`, `ARM_INGRESS_PATH`, `ARM_MAKEMKV_PATH` | compose volume layer | Optional host-path overrides |
| `WEBHOOK_SECRET` | transcoder Settings | Inbound auth check |
| `API_KEYS`, `REQUIRE_API_AUTH` | transcoder Settings -> `auth.py` | API key gate |
| `ARM_CALLBACK_URL` | transcoder Settings | Callback URL for completion notifications |
| `GPU_VENDOR` | transcoder `presets/__init__.py:161`, `main.py:95` | Baked into `Dockerfile.{nvidia,amd,intel}` |
| `VAAPI_DEVICE` | transcoder `transcoder.py:135,1566` | AMD/Intel only |
| `FAKE_GPU_STATS` | transcoder `routers/health.py:106` | Test hook |
| `ARM_UI_*` (all) | arm-ui `backend/config.py` | Every UI knob is env-prefixed |
| `UI_SRC_PATH`, `TRANSCODER_SRC_PATH` | dev compose only | Sibling-repo source bind sources |
