# Fork Features

Major differences between this fork and upstream `automatic-ripping-machine` (surveyed 2026-04-25 against `upstream/main` ~v2.23.x and `upstream/3.0_devel` HEAD).

This document focuses on the larger architectural and product changes. Small bug fixes are listed at the bottom; one-line refactors and routine cleanup are not listed at all.

## Architecture

**Three-service split with a shared contracts layer.**
The single upstream Flask monolith is broken into three independently-versioned services:
- [automatic-ripping-machine-neu](https://github.com/uprightbass360/automatic-ripping-machine-neu) - the ripper backend (FastAPI + async)
- [automatic-ripping-machine-ui](https://github.com/uprightbass360/automatic-ripping-machine-ui) - the dashboard (SvelteKit + TypeScript SPA, with its own thin FastAPI BFF)
- [automatic-ripping-machine-transcoder](https://github.com/uprightbass360/automatic-ripping-machine-transcoder) - GPU-aware transcoding service

A shared-contracts Python package (`components/contracts`) defines the typed enums and Pydantic models all three services exchange, with submodule-lockstep CI so a contract change cannot ship to one service without the others. Services can be deployed on one host or split across machines.

## User-facing dashboard

**SvelteKit + TypeScript SPA replacing Flask/Jinja templates.** Full rewrite of the web UI, decoupled from the backend over a versioned REST + WebSocket API. Upstream has an `arm-vuejs` branch but it is unmerged and not on the release line.

**Real-time job dashboard over WebSockets.** Job state, phase (rip / transcode / finalize), and per-phase progress stream live to all connected clients without polling.

**Phase-aware progress bars.** Rather than one generic "% done" bar, the UI renders distinct visual states per pipeline phase, including a dedicated FINISHING dashboard section for jobs in the copying / waiting-for-transcode / ejecting phases (instead of showing stale 100% rip progress).

**Real-time track status during the MakeMKV rip.** Tracks flip to "ripped" mid-job by parsing MakeMKV's `FILE_ADDED` (MSG 3307) message stream, rather than waiting for the whole rip to complete and reconciling at the end.

**Cross-service system stats sidebar.** Live CPU, memory, and storage usage for both the ripper and the (possibly remote) transcoder, plus service-health indicators for ARM, the database, and the transcoder.

**File browser with permissions, rename, and delete.** Tabbed view across Raw / Completed / Transcode / Music directories, with permission display and in-UI file management. Upstream has no real file browser.

**Job management toolbox.** Abandon, delete, fix-permissions, toggle multi-title mode, force-complete stuck jobs, and "Skip Transcode & Finalize" recovery action - all from the job detail page with confirmation dialogs.

**30 built-in themes.** Color schemes including Default, Ocean, Forest, Terminal, LCARS, Dracula Pro, Hollywood Video, and many more, with custom themes loadable from a config directory and runtime CSS injection (no rebuild needed to add a theme).

**First-run setup wizard.** Eight-step state machine that detects database initialization, drive presence, and config completeness, then walks the operator through onboarding (welcome -> drives -> settings -> review) before unlocking normal operation. Backed by a `setup_complete` flag in `AppState` so transient DB errors don't bounce returning users back to the wizard.

**Image cache for poster art and metadata thumbnails.** SHA256-indexed disk cache with TTL (default 7 days) and size limits in front of OMDb / TMDb / MusicBrainz artwork, with maintenance endpoints to inspect stats and purge. Avoids re-fetching cover art on every dashboard load and survives metadata-API outages.

## Ripping pipeline

**TVDB v4 episode matching for TV series discs.** Runtime-based track-to-episode mapping for multi-episode TV discs, with a Browse/Match two-tab UI, per-season episode viewer, tolerance sliders, and alternative-season quick-buttons. Includes auto-detection of the best season across multi-season discs.

**Preset system for transcoding profiles.** Database-driven, named, slugged presets with per-job overrides. Presets are snapshotted at job-start time so mid-pipeline edits cannot retroactively change a running job, and slug validation is enforced through the shared-contracts layer end-to-end.

**Named-file overrides + naming preview.** Per-job custom output filenames via API, plus a `/naming-preview` endpoint that renders the final filenames for every track before the rip starts - so naming bugs surface before disc time is spent.

**MakeMKV hardening.** Per-drive USB buffer / read-speed tuning, robust TINFO parsing with fallback to post-rip disk scan, prescan tuning controls (`PRESCAN_QUALITY`, `PRESCAN_MIN_FILE_SIZE`), UDF stale-handle workaround for multi-layer Blu-ray reads, and TV-disc label parsing (e.g. `STARGATE_ATLANTIS_S1_D2`) for season/disc folder naming. Pioneer USB stability workarounds for UHD dual-layer reading.

**Auto-fetched MakeMKV community keydb.** Decryption keys updated at startup without manual intervention or reliance on third-party servers.

**Folder import (rip from BDMV / VIDEO_TS folders).** A parallel pipeline (`folder_ripper.py`) accepts a folder containing a Blu-ray (`BDMV/`) or DVD (`VIDEO_TS/`) disc structure and feeds it through the same MakeMKV remux + identification / metadata / track-status / transcoding flow as a disc rip - same job model, same UI, same naming - just without a physical drive. Lets you backfill a library or re-process disc images saved as folders without standing them up as a fresh disc job. ISO files are handled by a separate ISO-import pipeline.

**Music CD pipeline overhaul.** Full MusicBrainz disc-ID rewrite, `disc_number` tagging for multi-disc albums, automatic `.m3u` playlist generation per album folder, and a comprehensive abcde / cdparanoia / cd-discid output classifier so partial-success rips and silent I/O errors are caught instead of being marked complete.

## Transcoding

**Separate GPU transcoder service.** Transcoding runs in its own service with its own deployment, scaling, and image variants for NVIDIA (`-nvidia`), AMD (`-amd`), and Intel (`-intel`) - each with provider-specific encoder probes.

**Multi-worker concurrent transcoding.** Worker tasks are spawned from a shared queue with `MAX_CONCURRENT` configurable per GPU (e.g. NVIDIA 3-5, AMD 1-2, Intel 2-3, CPU 2-3), and each worker exposes its current job and state via a `/workers` endpoint for dashboard visibility.

**Resolution-tier-aware presets (DVD / Blu-ray / UHD).** Every preset defines per-tier encoder, quality, and HandBrake settings; the tier is auto-selected from the input video's resolution at job start. 4K is preserved as UHD, Blu-ray runs at 1080p, DVDs are upscaled to 720p. Built-in `balanced` / `quality` / `fast` variants per scheme, plus user-created custom presets.

**Local scratch storage for network shares.** A copy-transcode-move pattern keeps heavy I/O off the NFS / SMB mount during transcoding, then moves the finished file into place atomically. Critical for split-host deployments where the source/dest is on shared storage.

**Live GPU utilization metrics.** `/system/stats` exposes per-vendor live GPU metrics: NVIDIA via `nvidia-smi` (utilization, VRAM, temperature, encoder %), AMD via sysfs `gpu_busy_percent`, Intel via `intel_gpu_top`. The UI renders these in real time.

**GPU encoder probe gated on a functional no-op encode.** A working GPU is verified by actually running an encode at startup, not by reading driver capabilities. Prevents broken NVIDIA / VAAPI drivers from being silently selected when they would fail at runtime.

**Durable webhook callbacks.** The transcoder-to-ripper notification pipeline is backed by a `pending_callbacks` table + drainer loop, so callbacks survive transcoder restarts and intermittent network failures rather than being lost in memory.

**Typed multi-channel notification system.** User notifications run through a self-contained `arm/notifications/` module: a DB-backed outbox with an async dispatcher (retry + backoff + stale-reaper), three channel types (Apprise, rich-payload Webhook with HMAC-SHA256, and Bash script), an Apprise-introspected service catalog, per-channel/per-event message templates, and six lifecycle events published from the ripper. Channels are managed via `/api/v1/notifications/` and the arm-ui Notifications page. This replaces the legacy flat-config notification fields (`PB_KEY`, `IFTTT_KEY`, `PO_USER_KEY`, `PO_APP_KEY`, `JSON_URL`, `APPRISE`, `BASH_SCRIPT`, `NOTIFY_RIP`, `NOTIFY_TRANSCODE`), which an alembic migration translates into channel rows before dropping the columns.

**API key authentication with admin/readonly RBAC.** Optional `REQUIRE_API_AUTH` gates the transcoder REST API; admin keys can mutate (create/delete presets, retry/delete jobs, restart, PATCH config) while readonly keys can only observe. Webhook endpoint has its own `X-Webhook-Secret` separate from API keys.

**Job-level transcode overrides + retranscode.** Bitrate, codec, preset, and output format can be overridden per-job via the webhook payload, and a completed job can be re-transcoded with new settings without re-ripping the disc.

## Deployment

**Three deployment modes shipped as compose files.**
- All-in-one (single host)
- Remote transcoder (ripper + UI on one host, GPU transcoder on another)
- Ripper-only (no transcoder at all - the ripper writes final named files directly via the `finalize_output` path; UI hides every transcoder surface)

Each mode is gated by `TRANSCODER_ENABLED` and `TRANSCODER_HOST` so the same images run in all three.

**Slimmed ARM image and self-published base image.** Now that transcoding lives in its own service, HandBrake and FFmpeg were removed from the ARM image entirely (~2,500 lines of orchestration deleted, ~20 min cut from base-image build time). The base image (MakeMKV + system deps) was also pulled out of the upstream `arm-dependencies` submodule and is now built and published from this fork's `docker/base/` as `uprightbass360/arm-dependencies`, so releases are no longer coupled to upstream's cadence.

**Operational tooling for split deployments.** A `setup-arm.sh` script on the transcoder side patches the ripper's `arm.yaml` for the webhook URL, deploys the notification script when `WEBHOOK_SECRET` is in use, and optionally restarts ARM - so wiring up a remote-transcoder install doesn't require hand-editing config on two machines.

## Reliability

**Hardened udev / startup pipeline for optical drives.** The disc-detection path between host udev, the container, and the ripper has been substantially rebuilt to survive USB drives, container restarts, and SIGKILLed jobs. Concretely:

- Three udev rule files for distinct concerns: in-container detection (`61-docker-arm.rules`), host-driven `docker exec` triggering (`51-arm-disc-insert.rules`), and a host-side rate-limited watcher for USB drives (`99-arm-drive-watcher.rules`).
- Per-device `flock` on `/home/arm/.arm_<dev>.lock` prevents concurrent ARM runs and post-eject retriggering. Stale locks (held with no live `main.py` process) are detected and broken on next attempt.
- `event_timeout` raised from the udev default of 180s to 7200s and configurable via `UDEV_EVENT_TIMEOUT` env var, so udev no longer SIGKILLs in-progress rips that take longer than 3 minutes.
- Container `udev` startup is non-blocking with a 30s timeout so a hung udev never blocks container boot. Missing `/dev/sr*` device nodes are auto-created from `/sys/block` after udev settles.
- USB re-enumeration handling: stale `sr*` nodes (whose `/sys/block/` backing has disappeared) are scrubbed before launching ARM, so phantom drives don't get processed.
- Host-side drive watcher rate-limits to one rescan per device per 120s, preventing Pioneer-style continuous-ADD-event storms during USB bus resets, and uses an `ioctl(CDROM_DRIVE_STATUS)` check before invoking ARM so empty trays don't trigger jobs.
- Phantom udev events for non-existent device nodes are detected and skipped instead of crashing the wrapper.

**Orphaned-job cleanup on container startup.** A first-run service (`arm/services/job_cleanup.py`) walks the DB on boot, fails any ARM-owned jobs left in intermediate states from a crashed or SIGKILLed container, releases the drive, and sends a summary notification. Per-device lock files left from the previous lifecycle are also scrubbed so the next udev event lands cleanly.

**Drive diagnostic API and UI surface.** `/api/v1/drives/diagnostic` runs live checks (udevd running, kernel cdrom info, devnode presence) and returns a structured issue list to the dashboard, alongside `/drives/rescan` and per-drive `/drives/{id}/scan` endpoints. The UI surfaces drive-level health rather than just "ARM is up."

**Startup permission and UID/GID handling.** `arm_user_files_setup.sh` remaps the in-container `arm` user to whatever UID/GID the host passes via `ARM_UID`/`ARM_GID`, then verifies access to every required directory - falling back to a real read/write test for NFS / group / ACL cases where strict UID match is impossible. Subdirectories are created as the `arm` user (not root) to avoid root-owned files on NFS mounts. Read-only media/transcode mounts are detected and skipped instead of failing startup.

**Graceful transcoder-down behavior.** When the transcoder is unreachable, the ripper falls back to the finalize path rather than failing jobs - this is what makes the ripper-only deployment mode possible.

**Structured logging across all three services.** A single structlog `ProcessorFormatter` setup (in `arm/ripper/logger.py` for the ripper, `src/log_format.py` for the transcoder) wraps the stdlib logging module so all 200+ existing `logging.info/error/...` call sites get structured output without code changes. Three sinks run simultaneously per service: JSON lines to per-job (or per-service) files, colored human-readable to stdout for `docker logs`, and compact key=value to syslog. Per-job runs automatically bind `job_id`, `label`, and `devpath` into `structlog.contextvars` so every log line inside a job carries that context without the caller passing it. The UI's BFF and the transcoder both expose the JSON logs back through `/logs/{file}/structured` endpoints that support level filtering and full-text search, with a structured log viewer in the dashboard.

**~4,300 automated tests across the three services.** Roughly 1,960 pytest cases in the ripper, 700 in the UI's FastAPI BFF, 780 in the transcoder, plus 860 vitest cases on Svelte components / stores / API clients and a small Playwright visual-snapshot suite. Coverage reported to Codecov on every PR.

## Bug fixes still open upstream

The following 14 issues are fixed in this fork and remain open in upstream `automatic-ripping-machine/automatic-ripping-machine`:

| Issue | Title | Fork commit(s) |
|-------|-------|---|
| [#1281](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1281) | Filename error moving file after transcode | `c1f6caa`, `2623b11` |
| [#1345](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1345) | `fatal: invalid object name 'origin/HEAD'` | `edac6d2`, `e3d0e03` |
| [#1355](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1355) | Comma in filename breaks file move | `c1f6caa`, `2623b11` |
| [#1430](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1430) | OMDb "Too many results" for short queries | `9a87349`, `ed39afc`, `d939362` |
| [#1457](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1457) | Single quote in disc name breaks transcoding | `4f32270` |
| [#1526](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1526) | abcde I/O error not detected (zero exit) | `abc4f68`, `830a743` |
| [#1584](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1584) | NOT NULL on `system_drives.name` at startup | `2e63381`, `d939362` |
| [#1628](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1628) | ffprobe failure crashes HandBrake transcode | `96697d1`, `c10d917` |
| [#1641](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1641) | `calc_process_time` fails on >24h jobs | `78ab2e9`, `40bf39f` |
| [#1650](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1650) | Malformed BDMV XML crashes identification | `efa139d`, `ac33272` |
| [#1651](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1651) | Data disc same label silently overwrites | `500e89d`, `830a743` |
| [#1664](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1664) | DVD stays mounted - MakeMKV can't access drive | `ac33272`, `d939362` |
| [#1684](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1684) | Settings values not trimmed on save | `edac6d2` |
| [#1688](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1688) | Unparsed MakeMKV lines cause fatal error | `7297893` |

---

**Notes on upstream state (surveyed 2026-04-25):**
- Upstream `main` is on the v2.x line (~v2.23.x) with the original Flask + Jinja monolith.
- Upstream `3.0_devel` is partway toward a service split but still in-progress; this fork's split-and-shared-contracts model is well past that point.
- Upstream has an `arm-vuejs` branch (last touched 2025-10) but it is unmerged and not on the v2 release line. This fork's SvelteKit + TypeScript SPA is independent of that effort.
