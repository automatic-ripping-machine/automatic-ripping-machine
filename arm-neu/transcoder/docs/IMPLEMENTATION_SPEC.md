# ARM Transcoder - Security & Quality Improvements Specification

**Version:** 2.1
**Date:** February 8, 2026
**Status:** In Progress

## Overview

This specification addresses critical security vulnerabilities, high-priority bugs, and code quality issues identified in the initial codebase review. All changes maintain backward compatibility with existing deployments where possible.

---

## 1. Critical Security Fixes

### 1.1 Path Traversal Protection — COMPLETE

**Issue:** User-controlled webhook input directly used in file paths
**Severity:** Critical
**Impact:** Arbitrary file system access

**Implementation:**
- ~~Add `PathValidator` utility class to sanitize and validate all paths~~
- ~~Use `Path.resolve()` to normalize paths and check they're within allowed directories~~
- ~~Reject paths containing `..`, absolute paths, or symbolic links outside allowed dirs~~
- ~~Add `validate_source_path()` method to verify paths before queuing jobs~~

**Files Modified:**
- `src/utils.py` — PathValidator class with `validate()` and `validate_existing()` methods
- `src/main.py` — webhook handler validates paths before queuing
- `src/transcoder.py` — path validation before processing

**Test Cases (all covered in `tests/test_utils.py` and `tests/test_security.py`):**
- ~~Path with `../` sequences~~
- ~~Absolute paths~~
- ~~Symbolic links outside allowed directories~~
- ~~Windows-style paths with backslashes~~
- ~~URL-encoded traversal, null bytes, tilde expansion, env variable expansion~~

### 1.2 Webhook Input Validation — COMPLETE

**Issue:** No validation on webhook payloads
**Severity:** Critical
**Impact:** Memory exhaustion, database overflow, type errors

**Implementation:**
- ~~Use Pydantic `WebhookPayload` model for all webhook requests~~
- ~~Add field validators: max string lengths, allowed characters~~
- ~~Implement request size limits (10KB max)~~
- ~~Add FastAPI `Request` body size validator~~

**Validation Rules (all enforced):**
- ~~`title`: max 500 chars, control characters stripped~~
- ~~`body`: max 2000 chars, preserves newlines/tabs~~
- ~~`path`: max 1000 chars, null bytes and control chars stripped~~
- ~~`job_id`: max 50 chars, alphanumeric + hyphens only~~
- ~~Reject requests > 10KB~~

**Files Modified:**
- `src/models.py` — WebhookPayload with Pydantic field validators
- `src/main.py` — uses validated model, enforces 10KB body limit

### 1.3 Command Injection Prevention — COMPLETE

**Issue:** Unvalidated environment variables used in subprocess calls
**Severity:** Critical
**Impact:** Arbitrary command execution

**Implementation:**
- ~~Create allowlist of valid HandBrake preset names~~
- ~~Validate `video_encoder` against known encoder list~~
- ~~Add `CommandValidator` class to sanitize all subprocess arguments~~
- ~~Use absolute paths for all binaries~~

**Files Modified:**
- `src/config.py` — Pydantic validators for video_encoder, audio_encoder, subtitle_mode
- `src/utils.py` — CommandValidator with allowlist validation
- `src/constants.py` — VALID_VIDEO_ENCODERS, VALID_AUDIO_ENCODERS, VALID_SUBTITLE_MODES

---

## 2. High Priority Fixes

### 2.1 FFmpeg Stream Mapping — COMPLETE

**Issue:** No explicit stream mapping, may drop audio tracks
**Severity:** High
**Impact:** Data loss (missing audio/subtitle tracks)

**Implementation:**
- ~~Add explicit `-map 0:v:0`, `-map 0:a?`, `-map 0:s?`/`-map 0:s:0?` based on subtitle_mode~~
- ~~Subtitle stream selection handled by `-map` flags, `-c:s copy` for codec~~
- ~~Audio mapping uses `?` suffix for optional (no error on missing streams)~~

**Files Modified:**
- `src/transcoder.py` (`_build_ffmpeg_command`)

### 2.2 Worker Race Condition — COMPLETE

**Issue:** Worker may be None during startup/shutdown
**Severity:** High
**Impact:** Application crashes

**Implementation:**
- ~~Add worker readiness check before accepting webhooks~~
- ~~Return 503 Service Unavailable if worker not ready~~
- ~~Guards on webhook handler and retry endpoint~~

**Note:** Worker stored on `app.state.worker`. `is_running` checks `_running and not _shutdown_event.is_set()`. Multi-worker architecture uses per-worker `WorkerStatus` tracking.

**Files Modified:**
- `src/main.py` (readiness checks on webhook and retry endpoints)

### 2.3 Database Session Management — COMPLETE

**Issue:** Long-running sessions held during transcode
**Severity:** High
**Impact:** Database locks, session timeouts

**Implementation:**
- ~~Refactor to use short-lived sessions for each DB operation~~
- ~~Create `_update_job()` helper that opens/closes session per update~~
- ~~Progress update batching via `_update_progress()` with delta + time gating~~
- ~~`_process_job` no longer holds a session open during transcoding~~

**Files Modified:**
- `src/database.py` — async context manager with `get_db()`, auto-rollback on error
- `src/transcoder.py` — `_update_job()`, `_update_progress()` for short-lived sessions

### 2.4 Progress Update Optimization — COMPLETE

**Issue:** Excessive database writes on same progress value
**Severity:** High
**Impact:** Database contention, performance degradation

**Implementation:**
- ~~Track `_last_progress` and `_last_progress_time` per job~~
- ~~Only commit when progress increases by >= `PROGRESS_UPDATE_THRESHOLD` (5%)~~
- ~~Time-based rate limiting: max 1 update per `PROGRESS_UPDATE_MIN_INTERVAL` (10 seconds)~~
- ~~Short-lived DB sessions for each progress update~~
- ~~Clean up tracking state in `finally` block after job completes~~

**Files Modified:**
- `src/transcoder.py` (`_update_progress` method, `_transcode_file_ffmpeg`, `_transcode_file_handbrake`)

---

## 3. Medium Priority Fixes

### 3.1 Deprecated API Replacements — COMPLETE

**Issue:** Using deprecated `datetime.utcnow()`
**Severity:** Medium
**Impact:** Future Python version compatibility

**Implementation:**
- ~~Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)`~~
- ~~Use timezone-aware datetimes throughout~~

**Files Modified:**
- `src/transcoder.py` (all datetime usages)
- `src/models.py` (DateTime column defaults already correct)

### 3.2 Concurrent Processing Implementation — COMPLETE

**Issue:** `max_concurrent` setting unused
**Severity:** Medium
**Impact:** Misleading configuration

**Implementation:**
- ~~Spawn `max_concurrent` worker tasks from shared `asyncio.Queue`~~
- ~~Per-worker `WorkerStatus` tracking (id, status, current_job, started_at)~~
- ~~Sentinel-based shutdown (None in queue stops one worker)~~
- ~~Worker crash isolation (one failure doesn't affect others)~~
- ~~`GET /workers` endpoint for dashboard integration~~
- ~~`/health` and `/stats` updated with `active_count`, `max_concurrent`~~
- ~~Config docs updated with GPU vendor session limits (NVIDIA 3-5, AMD 1-2, Intel 2-3, CPU 2-3)~~
- ~~All blocking filesystem ops moved to `run_in_executor`~~

**Note:** Multi-worker pool pattern chosen over semaphore — N workers pull from queue naturally, no semaphore bookkeeping needed.

**Files Modified:**
- `src/transcoder.py` (WorkerStatus, run(worker_id), sentinel shutdown, is_running, active_jobs)
- `src/main.py` (spawn N worker tasks in lifespan, sentinel shutdown)
- `src/routers/workers.py` (new — GET /workers)
- `src/routers/health.py` (active_count, max_concurrent)
- `src/routers/stats.py` (active_count, max_concurrent)
- `src/config.py` (max_concurrent description)

### 3.3 Docker Dependencies — COMPLETE

**Issue:** HandBrake dependencies may be incomplete
**Severity:** Medium
**Impact:** Runtime failures

**Implementation:**
- ~~Option A: Install HandBrake via apt in nvidia/cuda image~~
- ~~Add runtime check on startup to verify HandBrakeCLI works~~

**Files Modified:**
- `Dockerfile` — installs HandBrake from Ubuntu universe repo
- `src/transcoder.py` — `check_gpu_support()` verifies HandBrake and FFmpeg on startup

### 3.4 Graceful Shutdown — COMPLETE

**Issue:** Active transcodes killed on shutdown
**Severity:** Medium
**Impact:** Partial files, wasted work

**Implementation:**
- ~~Configurable timeout via `SHUTDOWN_TIMEOUT` (default 300s)~~
- ~~Worker finishes current job before exiting (`asyncio.wait_for`)~~
- ~~Falls back to cancel on timeout~~
- ~~Log shutdown progress~~
- ~~Sentinel-based multi-worker shutdown (one None per worker task)~~

**Files Modified:**
- `src/main.py` (lifespan shutdown with sentinels + per-task `wait_for` + timeout)
- `src/constants.py` (`SHUTDOWN_TIMEOUT`)

### 3.5 Code Organization — COMPLETE

**Issue:** Imports inside functions, unused imports, monolithic main.py
**Severity:** Low
**Impact:** Code clarity, maintainability

**Implementation:**
- ~~Move all imports to module level~~
- ~~Remove unused `BackgroundTasks` import~~
- ~~Organize imports: stdlib, third-party, local~~
- ~~Split 686-line main.py into FastAPI routers (main.py now ~157 lines)~~
- ~~`routers/health.py`, `config.py`, `jobs.py`, `stats.py`, `logs.py`, `workers.py`~~
- ~~Worker stored on `app.state` instead of module global~~
- ~~Modern `Annotated` type hints for FastAPI DI~~

**Files Modified:**
- `src/main.py` — app creation, lifespan, logging only
- `src/routers/` — 7 focused router modules

### 3.6 Hardcoded Values — COMPLETE

**Issue:** Magic numbers throughout code
**Severity:** Low
**Impact:** Maintainability

**Implementation:**
- ~~Create constants file with named values~~

**Files Modified:**
- `src/constants.py` — STABILIZE_CHECK_INTERVAL, PROGRESS_UPDATE_THRESHOLD, NVENC_PRESET_DEFAULT, SHUTDOWN_TIMEOUT, encoder/audio/subtitle allowlists, AUDIO_FILE_EXTENSIONS, disk space constants, rate limit constants

---

## 4. Missing Features

### 4.1 API Authentication — COMPLETE

**Implementation:**
- ~~Add API key authentication via header~~
- ~~Support multiple API keys (read-only vs admin)~~
- ~~Admin key required for delete/retry operations~~
- ~~Read-only key for stats/list operations~~
- ~~Anonymous access disabled by default~~

**Configuration:**
```
API_KEYS="admin:key1,readonly:key2"
REQUIRE_API_AUTH=true
WEBHOOK_SECRET=mySecret
```

**Files:**
- `src/auth.py` — APIKeyAuth class with role parsing, `get_current_user()` and `require_admin()` dependencies
- `src/main.py` — auth dependencies on protected endpoints
- `src/config.py` — `require_api_auth`, `api_keys`, `webhook_secret` settings
- `docs/AUTHENTICATION.md` — setup guide

### 4.2 Rate Limiting

**Implementation:**
- Use `slowapi` for rate limiting
- Webhook endpoint: 10 requests/minute per IP
- API endpoints: 60 requests/minute per API key
- Return 429 Too Many Requests when exceeded

**Current state:** Not started — constants defined but no slowapi dependency or decorators.

**Files:**
- `requirements.txt` (add slowapi)
- `src/main.py` (rate limit decorators)

### 4.3 Metrics & Monitoring

**Implementation:**
- Add `/metrics` endpoint for Prometheus
- Track metrics:
  - Total jobs processed
  - Success/failure rates
  - Average transcode time
  - Current queue depth
  - GPU utilization (via nvidia-smi)
  - Disk space remaining

**Current state:** Not started.

**Files:**
- `requirements.txt` (add prometheus-client)
- `src/metrics.py` (new file)
- `src/main.py` (metrics endpoint)

### 4.4 Job Cancellation

**Implementation:**
- ~~Add `CANCELLED` job status~~
- Add `/jobs/{id}/cancel` endpoint
- Kill subprocess for cancelled jobs
- Clean up partial output files
- Update database status

**Current state:** Partial — `CANCELLED` status exists in JobStatus enum, tracked in /stats. No cancel endpoint or subprocess kill logic.

**Files:**
- `src/models.py` — CANCELLED status added
- `src/main.py` (cancel endpoint — not yet)
- `src/transcoder.py` (cancel handler — not yet)

### 4.5 Retry Limits — COMPLETE

**Implementation:**
- ~~Add `retry_count` column to TranscodeJobDB~~
- ~~Max 3 retries per job by default (configurable)~~
- Exponential backoff between retries (1min, 5min, 15min)
- ~~Mark as permanently failed after max retries~~

**Note:** Exponential backoff not implemented — retries are immediate. All other retry logic is complete.

**Files:**
- `src/models.py` — `retry_count` column with default 0
- `src/config.py` — `max_retry_count` setting (default 3, range 0-10)
- `src/main.py` — `/jobs/{id}/retry` endpoint with limit enforcement

### 4.6 Disk Space Checks — COMPLETE

**Implementation:**
- ~~Check available disk space before starting job~~
- ~~Estimate required space: source_size * 0.6 (reasonable compression)~~
- ~~Fail job immediately if insufficient space~~
- ~~Add minimum free space requirement (10GB default)~~
- Add disk space to health check endpoint — not yet

**Note:** Health check integration pending (see 5.2).

**Files:**
- `src/utils.py` — disk space functions implemented
- `src/config.py` — `minimum_free_space_gb` setting (default 10)
- `src/transcoder.py` — pre-job check wired in `_process_job` before copy

### 4.7 Audio CD Passthrough — COMPLETE (v17.x), superseded by webhook-driven output_path in v18.0.0

**v17.x implementation (audio passthrough still in place):**
- ~~Detect audio-only source directories (FLAC/MP3/OGG/WAV/M4A/WMA/AAC/ALAC)~~
- ~~Copy audio files directly without transcoding~~
- ~~Mark job as COMPLETED with track count~~
- ~~Clean up source directory when `delete_source` is set~~
- ~~Mixed MKV + audio directories treated as video (MKV path takes priority)~~

**Output-path partitioning removed in v18.0.0:**
- The transcoder no longer infers an audio subdirectory from config. ARM resolves the full output directory (including any `AUDIO_SUBDIR`-style partition) and sends it as the webhook's `output_path` field. The transcoder joins `payload.output_path` to `settings.completed_path` and writes there.
- `audio_subdir` was removed from `src/config.py`; the matching `AUDIO_SUBDIR` env var no longer has any effect on transcoder side.

**Files (current):**
- `src/constants.py` — `AUDIO_FILE_EXTENSIONS` set (still used to detect audio-only sources)
- `src/transcoder.py` — `_discover_audio_files()`, `_passthrough_audio()` still ship the bytes; output dir comes from `payload.output_path`

### 4.8 TV/Movie Routing — moved to ARM in v18.0.0

**Pre-v18 transcoder behavior (REMOVED):**
- ~~Detect TV shows via naming patterns (`S01`, `S01E01`)~~
- ~~Route TV to `TV_SUBDIR`, movies to `MOVIES_SUBDIR` from transcoder config~~

**Current v18.0.0+ behavior:**
- The transcoder does not classify or route by video type. ARM is the single source of truth for output paths and folds any per-type subdir partition (movies/, tv/, audio/, unidentified/) into the webhook's `output_path` field.
- `tv_subdir`, `movies_subdir`, `audio_subdir`, `unidentified_subdir` were removed from `src/config.py`. The matching `TV_SUBDIR` / `MOVIES_SUBDIR` / `AUDIO_SUBDIR` / `UNIDENTIFIED_SUBDIR` env vars are now ARM-side (in `arm.yaml`) and have no effect on the transcoder.
- `_detect_video_type()` / `_determine_output_path()` in the pre-v18 transcoder are gone; see the `output_path` handling in the webhook router instead.

See `docs/WEBHOOK-PAYLOAD.md` for the current path policy.

### 4.9 Resolution-Based Preset Selection — COMPLETE

**Implementation:**
- ~~Detect source video resolution via ffprobe before transcoding~~
- ~~Three-tier encoding: 4K (>1080p), Blu-ray (720p–1080p), DVD (<720p)~~
- ~~HandBrake: 4K uses `HANDBRAKE_PRESET_4K`, DVD adds `--width 1280` upscale~~
- ~~FFmpeg: DVD upscale via GPU-native filters (`scale_cuda`, `scale_vaapi`, `vpp_qsv`, `scale`)~~
- ~~Graceful fallback to standard preset when ffprobe fails~~

**Configuration:**
```
HANDBRAKE_PRESET=       # auto-detected from GPU (e.g. H.265 NVENC 1080p for NVIDIA)
HANDBRAKE_PRESET_4K=    # auto-detected from GPU (e.g. H.265 NVENC 2160p 4K for NVIDIA)
```

**Files Modified:**
- `src/config.py` — `handbrake_preset_4k` setting
- `src/transcoder.py` — `_get_video_resolution()`, resolution logic in `_transcode_file_handbrake()` and `_build_ffmpeg_command()`
- All `docker-compose*.yml` — `HANDBRAKE_PRESET_4K` env var with GPU-appropriate defaults
- `.env.example` — `HANDBRAKE_PRESET_4K` documented

**Test Cases (all covered):**
- ~~Resolution parsing: valid, 4K, DVD, malformed, empty, ffprobe failure~~
- ~~HandBrake: 4K preset, 1080p standard, 480p upscale, 720p boundary, ffprobe fallback~~
- ~~FFmpeg: upscale per GPU family (NVENC, VAAPI, QSV, AMF, software), 1080p/4K no-op, PAL DVD~~
- ~~Integration: 4K source triggers 4K preset through full pipeline~~

### 4.10 Completion Notifications

**Implementation:**
- Support webhook callbacks on job completion
- Support email notifications via SMTP
- Support Apprise for multi-channel notifications
- Configurable per-job or global

**Current state:** Not started.

**Files:**
- `src/config.py` (notification config)
- `src/notifications.py` (new file)
- `src/transcoder.py` (send on completion)

---

## 5. Additional Improvements

### 5.1 Logging

**Implementation:**
- Structured logging with JSON output option
- Log levels per module
- Request IDs for tracing
- Log rotation configuration
- ~~Sensitive data masking (API keys, paths)~~

**Current state:** Partial — basic logging with configurable `log_level`, `sanitize_log_message()` in utils.py for masking sensitive data. No JSON output, no request IDs, no log rotation.

**Files:**
- `src/utils.py` — `sanitize_log_message()` implemented
- `src/logging_config.py` (not yet created)

### 5.2 Health Checks

**Implementation:**
Enhanced health check that verifies:
- ~~Worker is running~~
- Database is accessible
- GPU is available (nvidia-smi)
- Disk space > minimum
- Shared storage mounts are readable/writable

**Current state:** Partial — `/health` returns worker status and queue size. No GPU, disk, or storage mount checks.

**Files:**
- `src/main.py` (enhanced health endpoint)

### 5.3 Pagination — COMPLETE

**Implementation:**
- ~~Add `limit` and `offset` parameters to `/jobs`~~
- ~~Default limit: 50~~
- ~~Max limit: 500~~
- ~~Return total count in response~~

**Files:**
- `src/main.py` — `/jobs` endpoint with limit, offset, status filter, total count

### 5.4 Error Handling — COMPLETE

**Implementation:**
- ~~Catch and log all exceptions~~
- ~~Never silently swallow exceptions~~
- ~~Provide meaningful error messages to API users~~

**Files:**
- `src/main.py` — HTTPException with detail messages for all error paths
- `src/transcoder.py` — exception logging with exc_info, job status set to FAILED with error message

---

## 6. Testing Requirements

### 6.1 Unit Tests — COMPLETE

Required tests:
- ~~PathValidator (all attack vectors)~~
- ~~WebhookPayload validation~~
- ~~Progress tracking logic~~
- ~~Disk space calculations~~
- ~~Retry logic with backoff~~

**Files (665 tests total):**
- `tests/test_utils.py` — 48 tests (PathValidator, CommandValidator, disk space, title cleaning, log sanitization)
- `tests/test_models.py` — 34 tests (WebhookPayload validation, JobStatus, TranscodeJob)
- `tests/test_transcoder.py` — 93 tests (GPU detection, encoder routing, FFmpeg commands, file discovery, audio file discovery, resolution detection, preset selection, FFmpeg upscale per GPU, source path resolution, stream mapping, disk space pre-check)
- `tests/test_auth.py` — 27 tests (API key auth, webhook secret, settings validation)
- `tests/test_multi_worker.py` — 18 tests (WorkerStatus, worker properties, sentinel shutdown, crash isolation, /workers endpoint)
- `tests/test_router_coverage.py` — 13 tests (router endpoint coverage via ASGI client)
- `tests/test_router_direct.py` — 14 tests (direct-call coverage for jobs, stats, config, lifespan)

### 6.2 Integration Tests — COMPLETE

Required tests:
- ~~Full transcode workflow~~
- ~~Webhook to completion~~
- Job cancellation
- ~~Graceful shutdown~~
- ~~Concurrent job processing~~

**Note:** Job cancellation pending feature implementation. Graceful shutdown and concurrent processing tests complete.

**Files:**
- `tests/test_integration.py` — 31 tests (job lifecycle, retry/delete, startup restore, worker run loop, multi-file transcode, work dir cleanup, audio CD passthrough, 4K preset selection, main feature identification)

### 6.3 Security Tests — COMPLETE

Required tests:
- ~~Path traversal attempts~~
- ~~Oversized payloads~~
- ~~Command injection attempts~~
- Rate limit enforcement
- ~~API key validation~~

**Note:** Rate limit tests pending slowapi implementation.

**Files:**
- `tests/test_security.py` — 43 tests (path traversal, oversized payloads, command injection, auth bypass, webhook sanitization)
- `tests/test_api.py` — 22 tests (all API endpoints, worker 503 guards)

---

## 7. Documentation Updates

### 7.1 README Updates — COMPLETE

- ~~Add security section~~
- ~~Document API authentication~~
- ~~Add monitoring setup guide~~
- ~~Update configuration examples~~
- ~~Architecture diagram (Mermaid)~~
- ~~Encoder options table~~
- ~~Troubleshooting section~~

### 7.2 New Documentation

- `docs/AUTHENTICATION.md` — COMPLETE
- `docs/proxmox-lxc-setup.md` — COMPLETE
- `docs/SECURITY.md` - Security best practices — not started
- `docs/API.md` - Complete API reference — not started
- `docs/MONITORING.md` - Prometheus integration — not started (blocked on 4.3)
- `docs/TROUBLESHOOTING.md` - Common issues — not started

---

## 8. Implementation Order

1. **Phase 1: Critical Security** — COMPLETE
   - ~~Path traversal protection~~
   - ~~Input validation~~
   - ~~Command injection prevention~~

2. **Phase 2: High Priority Bugs** — COMPLETE
   - ~~FFmpeg stream mapping~~
   - ~~Race conditions~~
   - ~~Database sessions~~
   - ~~Progress optimization~~

3. **Phase 3: Medium Priority** — COMPLETE
   - ~~Deprecated API replacements~~
   - ~~Concurrent processing (multi-worker pool)~~
   - ~~Graceful shutdown (sentinel-based)~~
   - ~~Code cleanup (router refactor)~~
   - ~~Constants file~~
   - ~~Docker dependencies~~

4. **Phase 4: Features** — Partial
   - ~~Authentication~~
   - Rate limiting — not started
   - Metrics — not started
   - Job cancellation — partial
   - Notifications — not started
   - ~~Retry limits~~
   - ~~Audio CD passthrough~~
   - ~~Resolution-based preset selection~~

5. **Phase 5: Testing & Documentation** — Partial
   - ~~Write tests (665 tests)~~
   - ~~Update documentation~~
   - ~~Security audit~~
   - Performance testing — not started

---

## 9. Breaking Changes

The following changes may break existing deployments:

1. **API Authentication** - Existing API clients need to add API key header
2. **Webhook Validation** - Invalid webhooks now return 400 instead of being ignored
3. **Path Restrictions** - Paths outside RAW_PATH/COMPLETED_PATH are rejected
4. **Router Refactor** - Direct imports of endpoint functions from `main` module no longer work. Endpoints live in `src/routers/`.
5. **Worker API** - `run()` now requires `worker_id` parameter. `_current_job` replaced with `_active_jobs` dict. Sentinel-based shutdown.
6. **Health/Stats Response** - `/health` and `/stats` now include `active_count` and `max_concurrent` fields.

**Migration Path:**
- API keys can be disabled via `REQUIRE_API_AUTH=false` (default)
- Webhook validation is always active (backward compatible — valid ARM payloads pass)
- Path validation rejects only malicious paths; normal ARM paths are unaffected

---

## 10. Performance Targets

After implementation:

- Webhook response time: < 50ms
- Job queueing latency: < 100ms
- Database query time: < 10ms (99th percentile)
- Memory usage: < 512MB base + 200MB per concurrent job
- CPU usage (idle): < 5%
- API latency: < 20ms (excluding long-running operations)

---

## 11. Success Criteria

Implementation complete when:

- [x] All critical/high security issues resolved
- [x] All tests passing (298 tests)
- [x] Security audit passed
- [x] Documentation updated
- [ ] Performance targets met
- [x] No regressions in functionality
- [x] Backward compatibility maintained (with migration path)

---

## 12. Known Bugs

### 12.1 Source path resolution fails when ARM title differs from directory name

**Status:** Open
**Severity:** High
**Discovered:** 2026-02-10

**Problem:** When ARM's manually-corrected title differs from the auto-detected title used for the rip directory name, `_resolve_source_path()` cannot find the ripped files.

**Example:**
- ARM auto-detects title as `LOTR--the-Pronouns-of-Power` and creates rip directory: `raw/movies/LOTR--the-Pronouns-of-Power (2022)_177071496972/`
- User manually corrects title to `The Lord of the Rings- The Fellowship of the Ring`
- Webhook body sends: `"The Lord of the Rings- The Fellowship of the Ring rip complete. Starting transcode."`
- Transcoder extracts title and looks for directories starting with `The Lord of the Rings- The Fellowship of the Ring`
- No match found because directory starts with `LOTR--the-Pronouns-of-Power`

**Root cause:** The webhook notification uses `job.title` (the corrected title) but the filesystem directory uses the original auto-detected title. `_resolve_source_path()` only matches directories whose names start with the webhook title.

**Possible fixes:**
1. Modify `notify_transcoder.sh` to include the actual rip path (from `job.path`) as an explicit `path` field in the JSON payload
2. Add fuzzy matching or disc label matching in `_resolve_source_path()`
3. Have ARM pass both the title and the raw path in the webhook payload
