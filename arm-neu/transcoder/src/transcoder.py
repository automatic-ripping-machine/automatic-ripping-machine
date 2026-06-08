"""
Transcode worker - handles GPU transcoding with HandBrake or FFmpeg
"""

import asyncio
import dataclasses
import json
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

import httpx
import structlog
from sqlalchemy import select

from file_transfer import async_copy, async_copy_file, async_move_file, async_rmtree
from config import settings
from presets import Preset, resolve_preset
from constants import (
    AUDIO_FILE_EXTENSIONS,
    PROGRESS_UPDATE_MIN_INTERVAL,
    PROGRESS_UPDATE_THRESHOLD,
)
from database import get_db
from log_format import json_formatter
from arm_contracts import JobStatus as _ContractJobStatus, TranscodeCallbackPayload, TranscodePhase
from models import TranscodeJobDB, JobStatus, PendingCallbackDB, TranscodeJob
from utils import check_sufficient_disk_space, clean_title_for_filesystem, estimate_transcode_size
from version import API_VERSION


def log_filename(job_id: int) -> str:
    """Canonical log filename for a transcode job. Single source of truth."""
    return f"JOB_{job_id}_Transcode.log"

logger = logging.getLogger(__name__)

_MKV_GLOB = "*.mkv"

# Progress-line regexes used inside the encoder stdout loops.
# Compiled once at module load so each line in a long transcode reuses
# them. They use atomic, non-overlapping fragments (no nested quantifiers
# on overlapping classes) to stay linear under adversarial input - HandBrake
# and FFmpeg can produce very long lines and we don't want to give an
# attacker who can influence the output a way to wedge the worker.
_NUM = r'\d+(?:\.\d+)?'  # Non-overlapping integer + optional fractional.
# HandBrake progress is now parsed from --json blocks (see
# _HandBrakeJsonProgress); the old %/fps line scrapers were removed with
# that switch. FFmpeg still writes fps to stderr regardless of TTY.
_FFMPEG_FPS_PATTERN = re.compile(rf'\bfps=\s*({_NUM})')  # FFmpeg "fps=24.0"
_TIME_PATTERN = re.compile(rf'time=(\d+):(\d+):({_NUM})')


class _HandBrakeJsonProgress:
    """Accumulate HandBrake ``--json`` progress blocks fed one line at a time.

    HandBrakeCLI 1.10.2 does not emit the human ``\\r12.3 % (45 fps)``
    progress line when stdout is a pipe (no TTY), so the old %-scraping
    handler never fired and the UI showed jobs stuck at 0%. With ``--json``
    HandBrake instead prints labelled JSON objects, e.g.::

        Progress:
        {
            "Progress": { "Progress": 0.4231, "Rate": 45.6, "RateAvg": 40.1, ... },
            "State": "WORKING"
        }

    The stdout reader (:meth:`TranscodeWorker._stream_progress_lines`)
    normalises ``\\r``→``\\n`` and splits, so this parser is fed ONE line at
    a time and must buffer a block across calls. :meth:`feed` returns
    ``(fraction, fps)`` once, on the line that closes a ``Progress:`` block,
    and ``None`` otherwise. ``fraction`` is the per-file 0..1 value;
    ``fps`` prefers the instantaneous ``Rate`` and falls back to ``RateAvg``.

    Non-progress blocks HandBrake also emits with ``--json`` (``Version:``,
    ``JSON Title Set:``) are ignored because we only start collecting after
    the literal ``Progress:`` label. Malformed JSON self-heals: the parser
    resets to idle and returns ``None`` without raising.
    """

    def __init__(self) -> None:
        self._collecting = False
        self._lines: list[str] = []
        self._depth = 0

    def feed(self, line: str) -> tuple[float, float | None] | None:
        if not self._collecting:
            # Only the literal "Progress:" label opens a block we care about.
            if line.strip() == "Progress:":
                self._collecting = True
                self._lines = []
                self._depth = 0
            return None

        self._lines.append(line)
        self._depth += line.count("{") - line.count("}")
        # The object is complete once braces balance and we've seen at least
        # one '{'. Until the first '{' arrives depth stays 0, so guard on it.
        if self._depth > 0 or not any("{" in s for s in self._lines):
            return None

        block = "\n".join(self._lines)
        self._collecting = False
        self._lines = []
        try:
            data = json.loads(block)
            prog = data.get("Progress", {})
            fraction = prog.get("Progress")
            if not isinstance(fraction, (int, float)):
                return None
            rate = prog.get("Rate")
            if not isinstance(rate, (int, float)) or rate <= 0:
                rate = prog.get("RateAvg")
            fps = float(rate) if isinstance(rate, (int, float)) and rate > 0 else None
            return float(fraction), fps
        except (ValueError, TypeError):
            # Malformed JSON: drop the block and recover on the next one.
            return None


def _ffmpeg_encoder_works(encoder: str, hwaccel: str | None = None) -> bool:
    """Attempt a 1-frame null encode to verify the encoder actually functions.

    The encoder name being compiled into ffmpeg (visible in `ffmpeg -encoders`)
    does not mean the hardware or driver is present. Running a tiny encode
    surfaces missing devices, missing drivers, or permission errors as a
    non-zero exit code.

    Frame size: NVENC requires at least ~132x136 for H.265 and 145x49 for H.264.
    QSV and VAAPI have similar minimums. 256x256 is safely above all of them.
    """
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    if hwaccel:
        cmd += ["-hwaccel", hwaccel]
    cmd += [
        "-f", "lavfi", "-i", "nullsrc=s=256x256:d=0.1",
        "-c:v", encoder,
        "-f", "null", "-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _ffmpeg_has_encoder(encoder: str) -> bool:
    """Check if ffmpeg has the encoder compiled in (fast, no hardware test)."""
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=10,
        )
        return encoder in proc.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def check_gpu_support() -> dict:
    """Check which GPU encoders are actually functional.

    For each ffmpeg encoder we check both: compiled in AND runs successfully
    against available hardware. This avoids reporting encoders as available
    when the hardware or driver is missing (common on CPU-only hosts where
    ffmpeg ships with NVENC/VAAPI/QSV compiled in regardless).
    """
    result = {
        "handbrake_nvenc": False,
        "handbrake_qsv": False,
        "ffmpeg_nvenc_h265": False,
        "ffmpeg_nvenc_h264": False,
        "ffmpeg_vaapi_h265": False,
        "ffmpeg_vaapi_h264": False,
        "ffmpeg_amf_h265": False,
        "ffmpeg_amf_h264": False,
        "ffmpeg_qsv_h265": False,
        "ffmpeg_qsv_h264": False,
        "vaapi_device": False,
    }

    # HandBrake checks: --help listing is compile-time, still a hint not proof.
    # HandBrake returns false correctly when hardware is absent because its
    # --help output is gated on runtime probe results (unlike ffmpeg's).
    try:
        output = subprocess.run(
            ["HandBrakeCLI", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        combined = output.stdout.lower() + output.stderr.lower()
        if "nvenc" in combined:
            result["handbrake_nvenc"] = True
        if "qsv" in combined:
            result["handbrake_qsv"] = True
    except Exception:
        pass

    # VAAPI/QSV device detection (needed before gated encoder probes)
    vaapi_device = os.environ.get("VAAPI_DEVICE", "/dev/dri/renderD128")
    result["vaapi_device"] = os.path.exists(vaapi_device)

    # FFmpeg encoder probes: compiled-in check + functional test.
    # The functional test is what catches the false-positive case.
    ffmpeg_probes = [
        ("ffmpeg_nvenc_h265", "hevc_nvenc", None),
        ("ffmpeg_nvenc_h264", "h264_nvenc", None),
        ("ffmpeg_amf_h265",   "hevc_amf",   None),
        ("ffmpeg_amf_h264",   "h264_amf",   None),
    ]
    for key, encoder, hwaccel in ffmpeg_probes:
        if _ffmpeg_has_encoder(encoder) and _ffmpeg_encoder_works(encoder, hwaccel):
            result[key] = True

    # VAAPI/QSV: skip functional test if no device node; saves ~10s timeout
    if result["vaapi_device"]:
        for key, encoder, hwaccel in [
            ("ffmpeg_vaapi_h265", "hevc_vaapi", "vaapi"),
            ("ffmpeg_vaapi_h264", "h264_vaapi", "vaapi"),
            ("ffmpeg_qsv_h265",   "hevc_qsv",   "qsv"),
            ("ffmpeg_qsv_h264",   "h264_qsv",   "qsv"),
        ]:
            if _ffmpeg_has_encoder(encoder) and _ffmpeg_encoder_works(encoder, hwaccel):
                result[key] = True

    return result


# Keep backward-compatible alias
check_nvenc_support = check_gpu_support


@dataclasses.dataclass
class WorkerStatus:
    """Per-worker status for tracking active jobs."""
    worker_id: int
    status: Literal["idle", "processing"] = "idle"
    current_job: Optional[str] = None
    current_job_id: Optional[int] = None
    started_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "status": self.status,
            "current_job": self.current_job,
            "current_job_id": self.current_job_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
        }


@dataclasses.dataclass(frozen=True)
class PresetSnapshot:
    """Job-scoped snapshot of the resolved preset + merged overrides.

    Captured once at the start of a job to eliminate per-file DB hits
    (custom-preset lookups) and to prevent mid-job PATCH races to
    ``/config`` from leaking new settings into in-flight tracks. Per-file
    encoding still selects the tier based on the track's own resolution.
    """
    preset: Preset
    combined_overrides: dict[str, Any] | None


class TranscodeWorker:
    """Background worker that processes transcode jobs."""

    def __init__(self, gpu_support: dict | None = None):
        self._queue: asyncio.Queue[TranscodeJob | None] = asyncio.Queue()
        self._running = False
        self._active_jobs: dict[int, WorkerStatus] = {}
        self._shutdown_event = asyncio.Event()
        self._gpu_support = gpu_support if gpu_support is not None else check_gpu_support()
        self._last_progress: dict[int, float] = {}
        self._last_progress_time: dict[int, float] = {}
        self._queue_lock = asyncio.Lock()
        # Strong refs to fire-and-forget progress tasks so the GC doesn't reap
        # them mid-flight (asyncio's task list is weak-ref only).
        self._progress_tasks: set[asyncio.Task] = set()
        # Set by main.py lifespan after worker construction. See callback_drainer.py.
        self._drainer = None

        logger.info(f"GPU support: {self._gpu_support}")

        # Determine default encoder from the active scheme's default preset
        from main import active_scheme
        default_preset = active_scheme.default_preset
        default_encoder = default_preset.shared.get("video_encoder", "x265")
        self._encoder_family = self._detect_encoder_family(default_encoder)
        self._encoder_backend = self._select_backend(default_encoder, self._encoder_family)

        logger.info(f"Encoder family: {self._encoder_family}, backend: {self._encoder_backend}")

    def _effective(self, key: str, overrides: dict | None) -> object:
        """Return per-job override if set, otherwise global setting.

        Used for non-encoding fields (delete_source, output_extension, etc.).
        Encoding fields (video_encoder, video_quality, audio_encoder,
        subtitle_mode, handbrake_preset, etc.) are resolved via
        _resolve_effective_settings() and the scheme/preset system.
        """
        if overrides and key in overrides:
            return overrides[key]
        return getattr(settings, key)

    async def _snapshot_preset(self, overrides: dict | None) -> PresetSnapshot:
        """Resolve the active preset + merged overrides once for a whole job.

        Runs the DB lookup for custom presets and reads
        ``settings.global_overrides`` / ``settings.selected_preset_slug``
        exactly once. The returned snapshot is passed into each per-file
        transcode call so the entire job sees a single consistent view even
        if the user PATCHes ``/config`` while the job is running.

        Merge layering (applied per-file in _resolve_effective_settings):
          1. preset.shared
          2. preset.tiers[tier]
          3. global_overrides (from settings at snapshot time)
          4. job-level overrides
        """
        from main import active_scheme
        import json as _json

        # Determine preset: job override > global > scheme default
        preset_slug = None
        if overrides and "preset_slug" in overrides:
            preset_slug = overrides["preset_slug"]
        if not preset_slug:
            preset_slug = settings.selected_preset_slug
        # Coerce to string and drop whitespace - settings can round-trip as
        # empty string on fresh installs
        preset_slug = str(preset_slug).strip() if isinstance(preset_slug, str) else None

        preset = None
        if preset_slug:
            preset = active_scheme.get_preset(preset_slug)
            if not preset:
                # Check custom presets in DB (one-time per job)
                from models import CustomPresetDB
                async with get_db() as db:
                    custom = await db.get(CustomPresetDB, preset_slug)
                if custom and custom.scheme == active_scheme.slug:
                    parent = active_scheme.get_preset(custom.parent_slug)
                    if parent:
                        custom_overrides = _json.loads(custom.overrides_json) if custom.overrides_json else {}
                        preset = Preset(
                            slug=custom.slug, name=custom.name, scheme=custom.scheme,
                            description="", shared={**parent.shared, **custom_overrides.get("shared", {})},
                            tiers={
                                t: {**parent.tiers.get(t, {}), **custom_overrides.get("tiers", {}).get(t, {})}
                                for t in ("dvd", "bluray", "uhd")
                            },
                        )

        if preset_slug and not preset:
            logger.error(f"Preset '{preset_slug}' not found for scheme '{active_scheme.slug}', using default")

        if not preset:
            preset = active_scheme.default_preset

        # Snapshot global overrides at job start — no mid-job PATCH race
        raw_global = settings.global_overrides
        global_overrides = _json.loads(raw_global) if isinstance(raw_global, str) and raw_global else None

        # Merge job overrides (new shape: overrides["overrides"] is the diff)
        job_overrides = overrides.get("overrides") if overrides else None

        # Also handle legacy flat overrides (old shape: {"video_encoder": "...", "video_quality": 22, ...})
        if overrides and "preset_slug" not in overrides and "video_encoder" in overrides:
            legacy = {k: v for k, v in overrides.items() if k not in ("preset_slug", "overrides")}
            job_overrides = {"shared": legacy}

        # Chain: global -> job (applied over preset per-file)
        combined_overrides: dict[str, Any] = {}
        for layer in [global_overrides, job_overrides]:
            if layer:
                for section in ["shared", "tiers"]:
                    if section in layer:
                        combined_overrides.setdefault(section, {})
                        if section == "shared":
                            combined_overrides[section].update(layer[section])
                        else:
                            for t, fields in layer[section].items():
                                combined_overrides[section].setdefault(t, {}).update(fields)

        return PresetSnapshot(
            preset=preset,
            combined_overrides=combined_overrides or None,
        )

    async def _resolve_effective_settings(
        self,
        resolution: tuple[int, int] | None,
        overrides: dict | None,
        *,
        snapshot: PresetSnapshot | None = None,
    ) -> dict[str, Any]:
        """Return effective settings for a single file.

        If *snapshot* is provided (the normal job-scoped path), reuse the
        already-resolved preset + merged overrides - no DB hit, no
        re-read of settings.global_overrides. Tier is still chosen
        per-file based on the track's resolution so DVD extras on a
        Blu-ray can pick the dvd tier.

        If *snapshot* is None, fall back to resolving on the fly. Kept
        for backwards compatibility with callers that never received a
        job-scoped snapshot (direct unit tests of the transcode methods,
        external callers).
        """
        # Determine tier from resolution (cheap, always per-file)
        if resolution and resolution[1] > 1080:
            tier = "uhd"
        elif resolution and resolution[1] < 720:
            tier = "dvd"
        else:
            tier = "bluray"

        if snapshot is None:
            snapshot = await self._snapshot_preset(overrides)

        effective = resolve_preset(snapshot.preset, tier, snapshot.combined_overrides)
        logger.info(
            f"Resolved settings: tier={tier}, preset={snapshot.preset.slug}, "
            f"encoder={effective.get('video_encoder')}"
        )
        return effective

    def _detect_encoder_family(self, encoder: str) -> str:
        """Determine encoder family from encoder name."""
        if "vaapi" in encoder:
            return "vaapi"
        if "amf" in encoder:
            return "amf"
        if "nvenc" in encoder:
            return "nvenc"
        if "qsv" in encoder:
            return "qsv"
        if encoder in ("x265", "x264"):
            return "software"
        return "unknown"

    def _select_backend(self, encoder: str, family: str) -> str:
        """Select transcoding backend (handbrake or ffmpeg) based on encoder."""
        if family == "nvenc":
            if self._gpu_support["handbrake_nvenc"]:
                logger.info("Using HandBrake with NVENC")
                return "handbrake"
            elif self._gpu_support["ffmpeg_nvenc_h265"] or self._gpu_support["ffmpeg_nvenc_h264"]:
                logger.info("Using FFmpeg with NVENC")
                return "ffmpeg"
            else:
                logger.warning("NVENC not detected - will attempt FFmpeg anyway")
                return "ffmpeg"
        elif family == "vaapi":
            if not self._gpu_support["vaapi_device"]:
                logger.warning("VAAPI device not found at /dev/dri/renderD128 - encoding may fail")
            logger.info("Using FFmpeg with VAAPI (AMD/Intel)")
            return "ffmpeg"
        elif family == "amf":
            logger.info("Using FFmpeg with AMF (AMD)")
            return "ffmpeg"
        elif family == "qsv":
            if self._gpu_support.get("handbrake_qsv"):
                logger.info("Using HandBrake with QSV")
                return "handbrake"
            logger.info("Using FFmpeg with Quick Sync (Intel)")
            return "ffmpeg"
        elif family == "software":
            logger.info("Using FFmpeg with software encoding")
            return "ffmpeg"
        else:
            logger.info("Using HandBrake (default backend)")
            return "handbrake"

    @property
    def is_running(self) -> bool:
        return self._running and not self._shutdown_event.is_set()

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def current_job(self) -> Optional[str]:
        """First active job title, for backward compatibility."""
        for ws in self._active_jobs.values():
            if ws.status == "processing":
                return ws.current_job
        return None

    @property
    def active_count(self) -> int:
        return sum(1 for ws in self._active_jobs.values() if ws.status == "processing")

    @property
    def active_jobs(self) -> list[dict]:
        return [ws.to_dict() for ws in sorted(self._active_jobs.values(), key=lambda w: w.worker_id)]

    @property
    def gpu_support(self) -> dict:
        return self._gpu_support

    def shutdown(self):
        """Signal worker to shutdown."""
        self._shutdown_event.set()

    async def queue_sentinel(self):
        """Put a sentinel None into the queue to stop one worker."""
        await self._queue.put(None)

    async def queue_job(
        self,
        job_id: int,
        source_path: str,
        title: str,
        video_type: Optional[str] = None,
        year: Optional[str] = None,
        disctype: Optional[str] = None,
        poster_url: Optional[str] = None,
        config_overrides: dict | None = None,
        multi_title: bool = False,
        tracks: list[dict] | None = None,
        output_path: str | None = None,
        title_name: str | None = None,
    ) -> tuple[int, bool]:
        """Add a job to the transcode queue.

        job_id is the ARM job ID, used as the primary key.
        Returns (job_id, created) — created is False when an existing
        active job already covers the same ID.
        """
        overrides_json = json.dumps(config_overrides) if config_overrides else None
        track_meta_json = json.dumps(tracks) if tracks else None
        async with self._queue_lock:
            async with get_db() as db:
                # Check for existing job by primary key
                existing = await db.get(TranscodeJobDB, job_id)
                if existing:
                    if existing.status in (JobStatus.PENDING, JobStatus.PROCESSING):
                        # Active job — return idempotently
                        logger.info(
                            f"Duplicate webhook — job {existing.id} already "
                            f"{existing.status.value} for {source_path}"
                        )
                        return existing.id, False
                    else:
                        # Terminal job (COMPLETED/FAILED) — reset for re-queue
                        existing.status = JobStatus.PENDING
                        existing.phase = TranscodePhase.queued.value
                        existing.progress = 0.0
                        existing.error = None
                        existing.started_at = None
                        existing.completed_at = None
                        existing.retry_count = (existing.retry_count or 0) + 1
                        existing.source_path = source_path
                        existing.title = title
                        # Refresh naming metadata from the new webhook payload
                        # so corrected episode names/folders take effect.
                        existing.video_type = video_type
                        existing.year = year
                        existing.disctype = disctype
                        existing.poster_url = poster_url
                        existing.config_overrides = overrides_json
                        existing.multi_title = 1 if multi_title else 0
                        existing.track_metadata = track_meta_json
                        existing.output_path = output_path
                        existing.title_name = title_name
                        await db.commit()
                        job_db = existing
                else:
                    # Create new job with ARM job ID as PK
                    job_db = TranscodeJobDB(
                        id=job_id,
                        title=title,
                        source_path=source_path,
                        video_type=video_type,
                        year=year,
                        disctype=disctype,
                        poster_url=poster_url,
                        config_overrides=overrides_json,
                        multi_title=1 if multi_title else 0,
                        track_metadata=track_meta_json,
                        output_path=output_path,
                        title_name=title_name,
                        status=JobStatus.PENDING,
                    )
                    db.add(job_db)
                    await db.commit()

                job = TranscodeJob(
                    id=job_db.id,
                    title=title,
                    source_path=source_path,
                )

        await self._queue.put(job)
        logger.info(f"Queued job {job.id}: {title}")
        return job.id, True

    async def _update_job(self, job_id: int, **kwargs):
        """Update job fields using a short-lived DB session."""
        async with get_db() as db:
            result = await db.execute(
                select(TranscodeJobDB).where(TranscodeJobDB.id == job_id)
            )
            job_db = result.scalar_one()
            for key, value in kwargs.items():
                setattr(job_db, key, value)
            await db.commit()

    async def _update_progress(self, job_id: int, progress: float, fps: float | None = None):
        """Update job progress with delta and time-based rate limiting.

        `fps` is the most recent encoder FPS sample. It piggybacks on the
        progress-update cadence and is only persisted when a progress write
        happens, so it doesn't thrash the database.
        """
        now = asyncio.get_event_loop().time()
        last_progress = self._last_progress.get(job_id, -PROGRESS_UPDATE_THRESHOLD)
        last_time = self._last_progress_time.get(job_id, 0.0)

        delta = progress - last_progress
        elapsed = now - last_time

        if delta >= PROGRESS_UPDATE_THRESHOLD and elapsed >= PROGRESS_UPDATE_MIN_INTERVAL:
            update_kwargs = {"progress": progress}
            if fps is not None:
                update_kwargs["current_fps"] = fps
            await self._update_job(job_id, **update_kwargs)
            self._last_progress[job_id] = progress
            self._last_progress_time[job_id] = now

    def _spawn_progress_task(self, coro) -> None:
        """Schedule a fire-and-forget progress update with strong ref retention.

        asyncio's task registry holds weak refs only, so a bare
        `asyncio.create_task(coro)` can be GC'd before it runs. We pin the
        task on `self._progress_tasks` and drop it again on completion.
        """
        task = asyncio.create_task(coro)
        self._progress_tasks.add(task)
        task.add_done_callback(self._progress_tasks.discard)

    async def _stream_progress_lines(
        self,
        process,
        job_id: int,
        *,
        line_handler,
    ) -> None:
        """Read process.stdout in chunks, splitting on both \\r and \\n.

        HandBrake and FFmpeg emit progress lines using \\r to overwrite the
        same terminal line. asyncio's StreamReader.readline() only splits on
        \\n, so the default loop buffers indefinitely until LimitOverrunError.
        We read fixed-size chunks and split manually.

        Drains stdout continuously so the OS pipe buffer cannot fill and
        deadlock the subprocess waiting on stdout while we wait on stdin.
        """
        assert process.stdout is not None
        buffer = b""
        while True:
            chunk = await process.stdout.read(4096)
            # Treat non-bytes (e.g., mock leakage in tests) as EOF instead of
            # spinning a `while True` that grows `buffer` into a MagicMock chain.
            if not chunk or not isinstance(chunk, (bytes, bytearray)):
                # Flush any trailing partial line
                if buffer:
                    self._dispatch_line(buffer, line_handler)
                break
            buffer += chunk
            # Split on \r and \n; keep trailing partial for next chunk
            parts = buffer.replace(b"\r", b"\n").split(b"\n")
            buffer = parts[-1]
            for raw in parts[:-1]:
                self._dispatch_line(raw, line_handler)

    @staticmethod
    def _dispatch_line(raw: bytes, line_handler) -> None:
        """Decode a raw stdout chunk and pass to the handler. Handler
        exceptions are caught at DEBUG so a buggy parser cannot kill a
        long-running transcode."""
        try:
            line = raw.decode("utf-8", errors="replace").strip()
        except Exception:
            logger.debug("decode failed", exc_info=True)
            return
        if not line:
            return
        try:
            line_handler(line)
        except Exception:
            logger.debug("line_handler raised", exc_info=True)

    async def run(self, worker_id: int = 0):
        """Main worker loop. Multiple instances pull from the shared queue.

        Args:
            worker_id: Integer identifier for this worker (0-based).
        """
        tag = f"[worker-{worker_id}]"
        self._running = True
        self._active_jobs[worker_id] = WorkerStatus(worker_id=worker_id)
        logger.info(f"{tag} Worker started")

        # Only worker-0 loads pending jobs on startup (avoid duplicates)
        if worker_id == 0:
            await self._load_pending_jobs()

        while not self._shutdown_event.is_set():
            try:
                try:
                    job = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Sentinel None = shutdown this worker
                if job is None:
                    self._queue.task_done()
                    logger.info(f"{tag} Received shutdown sentinel")
                    break

                self._active_jobs[worker_id] = WorkerStatus(
                    worker_id=worker_id,
                    status="processing",
                    current_job=job.title,
                    current_job_id=job.id,
                    started_at=datetime.now(timezone.utc),
                )
                logger.info(f"{tag} Starting transcode: {job.title} (job_id={job.id})")

                await self._process_job(job)

                self._active_jobs[worker_id] = WorkerStatus(worker_id=worker_id)
                self._queue.task_done()
                logger.info(f"{tag} Idle — waiting for next job")

            except Exception as e:
                logger.error(f"{tag} Worker error: {e}", exc_info=True)
                self._active_jobs[worker_id] = WorkerStatus(worker_id=worker_id)
                await asyncio.sleep(5)

        self._active_jobs.pop(worker_id, None)
        logger.info(f"{tag} Worker stopped")

    async def _load_pending_jobs(self):
        """Load any pending jobs from database on startup."""
        async with get_db() as db:
            result = await db.execute(
                select(TranscodeJobDB)
                .where(TranscodeJobDB.status.in_([JobStatus.PENDING, JobStatus.PROCESSING]))
                .order_by(TranscodeJobDB.created_at)
            )
            jobs = result.scalars().all()

            for job_db in jobs:
                # Reset processing jobs to pending
                if job_db.status == JobStatus.PROCESSING:
                    job_db.status = JobStatus.PENDING
                    await db.commit()

                job = TranscodeJob(
                    id=job_db.id,
                    title=job_db.title,
                    source_path=job_db.source_path,
                )
                await self._queue.put(job)
                logger.info(f"Restored pending job {job.id}: {job.title}")

    def _setup_job_logging(self, job_id: int, logfile_name: str) -> logging.Handler | None:
        """Attach a per-job log file handler. Returns the handler or None on failure."""
        try:
            log_dir = Path(settings.log_path)
            log_dir.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(str(log_dir / logfile_name), mode='a')
            handler.setFormatter(json_formatter())

            _job_id = job_id  # capture for filter closure

            class _JobFilter(logging.Filter):
                def filter(self, record):
                    ctx = structlog.contextvars.get_contextvars()
                    return ctx.get("job_id") == _job_id

            handler.addFilter(_JobFilter())
            logging.getLogger().addHandler(handler)
            return handler
        except Exception:
            logger.warning(f"Could not create per-job log file: {logfile_name}")
            return None

    async def _load_job_metadata(self, job_id: int) -> tuple[dict | None, str | None, str | None, str | None, str | None]:
        """Load per-job config overrides and metadata from DB.

        Returns (overrides, video_type, year, output_path, title_name).
        output_path is the directory ARM resolved (relative to
        completed_path); title_name is the pre-rendered file stem.
        """
        overrides = None
        db_video_type = None
        db_year = None
        arm_output_path = None
        arm_title_name = None
        async with get_db() as db_sess:
            result = await db_sess.execute(
                select(TranscodeJobDB).where(TranscodeJobDB.id == job_id)
            )
            job_db = result.scalar_one_or_none()
            if job_db:
                db_video_type = job_db.video_type
                db_year = job_db.year
                arm_output_path = job_db.output_path
                arm_title_name = job_db.title_name
                if job_db.config_overrides:
                    try:
                        overrides = json.loads(job_db.config_overrides)
                    except (json.JSONDecodeError, TypeError):
                        pass
        if overrides:
            logger.info(f"Per-job overrides: {overrides}")
        if arm_output_path:
            logger.info(f"ARM naming: output_path={arm_output_path}, title={arm_title_name}")
        return overrides, db_video_type, db_year, arm_output_path, arm_title_name

    async def _load_track_metadata(self, job_id: int) -> dict[str, dict] | None:
        """Load per-track metadata from DB. Returns {filename_stem: metadata} map or None."""
        async with get_db() as db_sess:
            result = await db_sess.execute(
                select(TranscodeJobDB).where(TranscodeJobDB.id == job_id)
            )
            job_db = result.scalar_one_or_none()
            if not job_db or not job_db.track_metadata:
                return None
            try:
                tracks = json.loads(job_db.track_metadata)
            except (json.JSONDecodeError, TypeError):
                return None

        # Build lookup by filename stem (exact + normalized) and track number.
        # Multiple keys per track improves match resilience if ARM renames files.
        meta_map: dict[str, dict] = {}
        for t in tracks:
            filename = t.get("filename", "")
            if filename:
                stem = Path(filename).stem
                meta_map[stem] = t
                # Normalized key: lowercase, underscores for spaces
                normalized = stem.lower().replace(" ", "_")
                if normalized != stem:
                    meta_map[normalized] = t
            track_num = t.get("track_number", "")
            if track_num:
                meta_map[f"_track_{track_num}"] = t
        return meta_map if meta_map else None

    def _match_track_metadata(
        self, output_stem: str, source_files: list[Path],
        track_meta: dict[str, dict],
    ) -> dict | None:
        """Match an output file to its track metadata.

        Tries multiple strategies: exact stem match, substring match,
        and normalized (lowercase/underscore) match.
        """
        # Strategy 1: source filename embedded in output name (existing behavior)
        for src_file in source_files:
            if src_file.stem in output_stem:
                meta = track_meta.get(src_file.stem)
                if meta:
                    return meta

        # Strategy 2: direct lookup by output stem
        meta = track_meta.get(output_stem)
        if meta:
            return meta

        # Strategy 3: normalized comparison
        norm_stem = output_stem.lower().replace(" ", "_")
        meta = track_meta.get(norm_stem)
        if meta:
            return meta

        return None

    async def _resolve_and_stabilize(self, job: TranscodeJob) -> None:
        """Wait for source files to stabilize. ARM has already resolved
        the source path on its side via the webhook input_path; we trust
        that absolute path verbatim. _wait_for_stable handles NFS lag."""
        await self._wait_for_stable(job.source_path)

    async def _discover_or_passthrough(self, job: TranscodeJob) -> list[Path]:
        """Discover source files. Handles audio passthrough."""
        loop = asyncio.get_event_loop()
        source_files = await loop.run_in_executor(None, self._discover_source_files, job.source_path)

        if not source_files:
            audio_files = await loop.run_in_executor(None, self._discover_audio_files, job.source_path)
            if audio_files:
                await self._passthrough_audio(job)
                return []
            raise ValueError(f"No video or audio files found in {job.source_path}")
        return source_files

    async def _transcode_files(
        self, job: TranscodeJob, local_source_files: list[Path],
        main_feature: Path, work_output_dir: Path, folder_name: str,
        overrides: dict | None, *, multi_title: bool = False,
        preset_snapshot: PresetSnapshot | None = None,
    ) -> list[dict]:
        """Transcode all source files to the work output directory.

        Returns a list of per-file results for multi-title tracking:
        ``[{"file": "name.mkv", "status": "completed"|"failed", "error": "..."}]``

        When *multi_title* is True, a single track failure does not abort the job.

        *preset_snapshot* carries the job-scoped resolved preset + merged
        overrides so each per-file transcode call skips the custom-preset
        DB lookup and sees a consistent view even if ``/config`` is
        PATCHed mid-job.
        """
        ext = self._effective("output_extension", overrides)
        file_results: list[dict] = []
        for i, source_file in enumerate(local_source_files):
            progress = (i / len(local_source_files)) * 100
            await self._update_progress(job.id, progress)

            is_main = source_file == main_feature
            if not multi_title and (is_main or len(local_source_files) == 1):
                # Single-title: main feature uses the job-level name
                output_file = work_output_dir / f"{folder_name}.{ext}"
            else:
                # Multi-title: always embed source filename so
                # _match_track_metadata can map output → track manifest
                output_file = work_output_dir / f"{folder_name} - {source_file.stem}.{ext}"

            logger.info(
                f"Transcoding [{i+1}/{len(local_source_files)}]: {source_file.name}"
                f"{' (main feature)' if is_main else ''}"
            )

            try:
                if self._encoder_backend == "ffmpeg":
                    await self._transcode_file_ffmpeg(
                        source_file, output_file, job.id,
                        overrides=overrides, preset_snapshot=preset_snapshot,
                        file_index=i, total_files=len(local_source_files),
                    )
                else:
                    await self._transcode_file_handbrake(
                        source_file, output_file, job.id,
                        overrides=overrides, preset_snapshot=preset_snapshot,
                        file_index=i, total_files=len(local_source_files),
                    )
                file_results.append({"file": source_file.name, "status": "completed"})
            except Exception as e:
                if multi_title:
                    logger.error(
                        f"Track {i+1} ({source_file.name}) failed, continuing: {e}",
                        exc_info=True,
                    )
                    file_results.append({
                        "file": source_file.name, "status": "failed",
                        "error": str(e)[:200],
                    })
                else:
                    raise  # single-title: fail the whole job as before
        return file_results

    async def _process_job(self, job: TranscodeJob):
        """Process a single transcode job.

        Uses local scratch storage (work_path) to avoid doing heavy I/O on shared storage:
          1. Copy source from raw → local work dir
          2. Transcode locally
          3. Move output from local → completed
          4. Clean up local work dir (always, even on failure)
          5. Clean up raw source (if delete_source is set)

        Each DB update uses a short-lived session to avoid holding locks during
        long-running I/O (file copies, transcoding).
        """
        logger.info(f"Processing job {job.id}: {job.title}")

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            job_id=job.id,
            label=job.title,
        )

        work_job_dir = Path(settings.work_path) / f"job-{job.id}"
        logfile_name = log_filename(job.id)
        job_handler = None

        try:
            job_handler = self._setup_job_logging(job.id, logfile_name)
            if not job_handler:
                logfile_name = None

            await self._update_job(
                job.id,
                status=JobStatus.PROCESSING,
                phase=TranscodePhase.copying_source.value,
                progress=0.0,
                started_at=datetime.now(timezone.utc),
                logfile=logfile_name,
            )
            await self._notify_arm_callback(job, "transcoding")

            overrides, db_video_type, db_year, arm_output_path, arm_title_name = await self._load_job_metadata(job.id)
            await self._resolve_and_stabilize(job)

            source_files = await self._discover_or_passthrough(job)
            if not source_files:
                return  # audio passthrough handled

            await self._update_job(job.id, total_tracks=len(source_files))
            logger.info(f"Found {len(source_files)} MKV files to transcode")

            # Check disk space and copy source to local scratch
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: work_job_dir.mkdir(parents=True, exist_ok=True))
            source_size = await loop.run_in_executor(
                None, lambda: sum(f.stat().st_size for f in source_files)
            )
            estimated_output = estimate_transcode_size(source_size)
            sufficient, msg = check_sufficient_disk_space(
                settings.work_path, source_size + estimated_output, settings.minimum_free_space_gb
            )
            if not sufficient:
                raise ValueError(msg)

            work_source_dir = work_job_dir / "source"
            work_output_dir = work_job_dir / "output"
            source = Path(job.source_path)
            await asyncio.get_event_loop().run_in_executor(None, work_output_dir.mkdir)

            logger.info(f"Copying source to local scratch: {work_source_dir}")

            async def _cs_progress(evt):
                await self._update_progress(job.id, evt.progress_pct)

            if await asyncio.get_event_loop().run_in_executor(None, source.is_file):
                await asyncio.get_event_loop().run_in_executor(None, work_source_dir.mkdir)
                await async_copy_file(
                    str(source), str(work_source_dir / source.name),
                    on_progress=_cs_progress,
                )
            else:
                await async_copy(
                    str(source), str(work_source_dir),
                    on_progress=_cs_progress,
                )

            loop = asyncio.get_event_loop()
            local_source_files = await loop.run_in_executor(
                None, self._discover_source_files, str(work_source_dir)
            )
            main_feature = max(local_source_files, key=lambda f: f.stat().st_size)
            resolution = await self._get_video_resolution(main_feature)
            await self._update_job(job.id, main_feature_file=main_feature.name)

            # Check for multi-title per-track metadata
            track_meta = await self._load_track_metadata(job.id)

            if arm_output_path:
                # ARM resolved the full subdir + leaf via the webhook. Just
                # join to completed_path; no type detection required.
                output_dir = Path(settings.completed_path) / arm_output_path
            else:
                # Fallback: transcoder builds its own path. Used only when
                # ARM didn't send output_path (legacy clients during a
                # rolling deploy).
                output_dir = self._determine_output_path(
                    job.title, job.source_path, resolution, overrides,
                    db_year=db_year, db_video_type=db_video_type,
                )
            folder_name = arm_title_name or output_dir.name
            await loop.run_in_executor(None, lambda: os.makedirs(output_dir, exist_ok=True))
            await self._update_job(
                job.id,
                video_type=db_video_type or self._detect_video_type(job.title, job.source_path),
                output_path=str(output_dir),
            )

            is_multi = bool(track_meta)

            # Snapshot the resolved preset + merged overrides ONCE for the
            # whole job, right before per-file transcoding begins. This
            # eliminates per-file DB hits for custom-preset lookups and
            # gives the job a consistent view even if /config is PATCHed
            # mid-transcode. Tier is still chosen per-file by resolution.
            preset_snapshot = await self._snapshot_preset(overrides)

            await self._update_job(
                job.id,
                phase=TranscodePhase.encoding.value,
                progress=0.0,
            )

            file_results = await self._transcode_files(
                job, local_source_files, main_feature, work_output_dir,
                folder_name, overrides, multi_title=is_multi,
                preset_snapshot=preset_snapshot,
            )

            # Move local output → completed (with per-track routing for multi-title)
            await self._update_job(
                job.id,
                phase=TranscodePhase.finalizing.value,
                progress=0.0,  # reset for the finalizing phase
            )

            async def _fin_progress(evt):
                await self._update_progress(job.id, evt.progress_pct)

            track_results = []
            # Build a set of failed source filenames so we don't try to move
            # partial output from tracks whose transcode raised. The partial
            # files exist on disk because the failure happens after some
            # data has been written; moving them yields rsync exit 23
            # ("Skipping sender remove for changed file") because the
            # zombied transcoder process may still hold a file handle.
            failed_sources = {
                r["file"] for r in file_results
                if r.get("status") == "failed"
            }

            def _matched_source_name(output_file: Path) -> str | None:
                """Map an output file back to its source filename.

                The output filename was renamed during _transcode_files;
                we need to map it back to the source. The convention from
                _transcode_files is `<title> - <source.name>` (line 822 area).
                """
                for src_file in local_source_files:
                    if src_file.name in output_file.name:
                        return src_file.name
                    if src_file.stem in output_file.stem:
                        return src_file.name
                return None

            if track_meta:
                logger.info("Multi-title disc: routing output files per-track metadata")
                for f in work_output_dir.iterdir():
                    matched_source_name = _matched_source_name(f)
                    if matched_source_name in failed_sources:
                        logger.warning(
                            "Skipping route for %s: source %s failed to transcode",
                            f.name, matched_source_name,
                        )
                        continue
                    matched_meta = self._match_track_metadata(
                        f.stem, local_source_files, track_meta,
                    )
                    if not matched_meta:
                        # Fall back to job-level output dir
                        logger.debug(f"No per-track match for {f.name}, using job output dir")
                        await async_move_file(
                            str(f), str(output_dir / f.name),
                            on_progress=_fin_progress,
                        )
                        continue

                    track_num = matched_meta.get("track_number", "")
                    try:
                        # Build per-track output path. ARM sends the
                        # resolved output_path on each track meta entry
                        # (with the track's video_type subdir already
                        # applied), so we just join to completed_path.
                        per_video_type = matched_meta.get("video_type", db_video_type)
                        track_output_path = matched_meta.get("output_path", "")
                        if track_output_path:
                            per_output_dir = Path(settings.completed_path) / track_output_path
                        else:
                            # Fallback: transcoder builds its own path.
                            per_title = matched_meta.get("title", job.title)
                            per_year = matched_meta.get("year", db_year)
                            per_output_dir = self._determine_output_path(
                                per_title, job.source_path, resolution, overrides,
                                db_year=per_year, db_video_type=per_video_type,
                            )
                        await loop.run_in_executor(None, lambda d=per_output_dir: os.makedirs(d, exist_ok=True))
                        # title_name = display filename from ARM's naming
                        # engine; output_path = directory (already
                        # resolved by ARM). Track names include episode
                        # numbers so files are unique within their dir.
                        per_title_name = matched_meta.get("title_name")
                        if not per_title_name:
                            # Fallback when ARM doesn't provide title_name:
                            # use folder name + track number to avoid collisions
                            per_title_name = per_output_dir.name
                            if track_num:
                                per_title_name = f"{per_title_name} - Track {track_num}"
                        new_name = f"{per_title_name}{f.suffix}"
                        logger.info(f"Moving {f.name} → {per_output_dir / new_name}")
                        await async_move_file(
                            str(f), str(per_output_dir / new_name),
                            on_progress=_fin_progress,
                        )
                        track_results.append({
                            "track_number": track_num,
                            "status": "completed",
                            "output_path": str(per_output_dir / new_name),
                            "source_file": matched_source_name or f.name,
                        })
                    except Exception as e:
                        logger.error(f"Failed to route track {track_num} ({f.name}): {e}")
                        # Move to job-level dir as fallback
                        try:
                            await async_move_file(
                                str(f), str(output_dir / f.name),
                                on_progress=_fin_progress,
                            )
                        except Exception:
                            pass
                        track_results.append({
                            "track_number": track_num,
                            "status": "failed",
                            "error": str(e)[:200],
                            "source_file": matched_source_name or f.name,
                        })
            else:
                logger.info(f"Moving output to completed: {output_dir}")
                for f in work_output_dir.iterdir():
                    matched_source_name = _matched_source_name(f)
                    if matched_source_name in failed_sources:
                        logger.warning(
                            "Skipping route for %s: source %s failed to transcode",
                            f.name, matched_source_name,
                        )
                        continue
                    await async_move_file(
                        str(f), str(output_dir / f.name),
                        on_progress=_fin_progress,
                    )

            # Merge transcode file_results into track_results for the callback.
            # A track that fails BOTH transcode AND route is one failure, not
            # two; dedup by source filename to avoid the "All N tracks failed"
            # false positive when N is small.
            failed_transcodes = [r for r in file_results if r.get("status") == "failed"]
            failed_routes = [r for r in track_results if r.get("status") == "failed"]
            failed_transcode_sources = {r["file"] for r in failed_transcodes}
            # Count routes that failed for tracks NOT already in the transcode
            # failure list. (Routes for failed transcodes are skipped in the
            # finalizing block; this dedup is defense-in-depth.)
            distinct_failed_routes = [
                r for r in failed_routes
                if r.get("source_file") not in failed_transcode_sources
            ]
            all_track_results = track_results or []

            # Determine overall status
            total_failures = len(failed_transcodes) + len(distinct_failed_routes)
            if total_failures > 0 and total_failures < len(local_source_files):
                # Some tracks failed but others succeeded
                final_status = JobStatus.COMPLETED
                callback_status = "partial"
                error_summary = f"{total_failures}/{len(local_source_files)} tracks failed"
                await self._update_job(
                    job.id,
                    status=final_status,
                    progress=100.0,
                    current_fps=None,
                    completed_at=datetime.now(timezone.utc),
                    error=error_summary,
                )
            elif total_failures >= len(local_source_files):
                raise RuntimeError(f"All {len(local_source_files)} tracks failed to transcode")
            else:
                callback_status = "completed"
                await self._update_job(
                    job.id,
                    status=JobStatus.COMPLETED,
                    progress=100.0,
                    current_fps=None,
                    completed_at=datetime.now(timezone.utc),
                )

            if self._effective("delete_source", overrides):
                try:
                    await self._cleanup_source(job.source_path)
                    logger.info(f"Cleaned up source: {job.source_path}")
                except OSError as e:
                    logger.warning(f"Could not clean up source: {e}")

            logger.info(f"Completed job {job.id}: {job.title}")
            await self._notify_arm_callback(
                job, callback_status, track_results=all_track_results,
            )

        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}", exc_info=True)
            try:
                await self._update_job(
                    job.id,
                    status=JobStatus.FAILED,
                    current_fps=None,
                    error=str(e),
                )
                await self._notify_arm_callback(job, "failed", error=str(e))
            except Exception:
                logger.error(f"Failed to update job {job.id} status to FAILED", exc_info=True)

        finally:
            # Always clean up local scratch
            loop = asyncio.get_event_loop()
            if await loop.run_in_executor(None, work_job_dir.exists):
                await async_rmtree(str(work_job_dir))
                logger.info(f"Cleaned up work dir: {work_job_dir}")
            if job_handler:
                logging.getLogger().removeHandler(job_handler)
                job_handler.close()
            self._last_progress.pop(job.id, None)
            self._last_progress_time.pop(job.id, None)
            structlog.contextvars.clear_contextvars()

    async def _wait_for_stable(self, path: str, timeout: int = 3600):
        """Wait for directory to stop receiving new files."""
        path = Path(path)
        loop = asyncio.get_event_loop()
        if not await loop.run_in_executor(None, path.exists):
            # NFS mounts may lag behind — wait up to 60s for the path to appear
            logger.info(f"Source path not yet visible, waiting for NFS propagation: {path}")
            for _ in range(12):
                await asyncio.sleep(5)
                if await loop.run_in_executor(None, path.exists):
                    break
            else:
                raise ValueError(f"Source path does not exist: {path}")

        logger.info(f"Waiting for source to stabilize: {path}")

        last_size = -1
        stable_time = 0
        start_time = asyncio.get_event_loop().time()

        def _scan_dir_size(p: Path) -> int:
            return sum(f.stat().st_size for f in p.rglob('*') if f.is_file())

        loop = asyncio.get_event_loop()

        while stable_time < settings.stabilize_seconds:
            current_size = await loop.run_in_executor(None, _scan_dir_size, path)

            if current_size == last_size:
                stable_time += 5
            else:
                stable_time = 0
                last_size = current_size

            await asyncio.sleep(5)

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Source still changing after {timeout}s")

        logger.info(f"Source stabilized at {last_size} bytes")

    async def _notify_arm_callback(
        self, job: TranscodeJob, status: str, *,
        error: str | None = None,
        track_results: list[dict] | None = None,
    ):
        """Enqueue a pending callback or send informational status fire-and-forget.

        Terminal statuses (completed, partial, failed) INSERT a
        PendingCallbackDB row; the TranscodeCallbackDrainer background task
        (set up in main.py lifespan) picks it up and delivers durably,
        surviving restarts. Informational statuses (transcoding) POST once
        with no retry or persistence - a missed informational update is
        corrected by the next terminal callback.

        No-op if settings.arm_callback_url is empty.
        """
        if not settings.arm_callback_url:
            return

        is_terminal = status in ("completed", "partial", "failed")

        if not is_terminal:
            # Informational: fire-and-forget, single attempt.
            # Build through TranscodeCallbackPayload so a JobStatus rename
            # crashes here at construction, not on arm-neu's receiver. F3.
            url = (
                f"{settings.arm_callback_url.rstrip('/')}/api/v1/jobs/"
                f"{job.id}/transcode-callback"
            )
            payload = TranscodeCallbackPayload(
                status=_ContractJobStatus(status),
            ).model_dump(exclude_none=True, mode="json")
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        url,
                        json=payload,
                        headers={"X-Api-Version": API_VERSION},
                    )
                if resp.status_code < 300:
                    logger.info(
                        f"ARM callback sent ({resp.status_code}): {status} "
                        f"for job {job.id}"
                    )
                else:
                    logger.warning(
                        f"ARM callback returned {resp.status_code} for "
                        f"job {job.id} (informational, not retried)"
                    )
            except Exception as e:
                logger.warning(
                    f"ARM callback failed for job {job.id}: {e} "
                    f"(informational, not retried)"
                )
            return

        # Terminal: enqueue for the drainer
        async with get_db() as session:
            row = PendingCallbackDB(
                job_id=job.id,
                status=status,
                error=error[:500] if error else None,
                track_results_json=(
                    json.dumps(track_results) if track_results else None
                ),
            )
            session.add(row)
            await session.commit()

        logger.info(
            f"ARM callback enqueued: status={status} for job {job.id}"
        )

        # Wake the drainer if it's attached (set by main.py at startup)
        drainer = getattr(self, "_drainer", None)
        if drainer is not None:
            drainer.notify_new_row()

    def _discover_source_files(self, source_path: str) -> list[Path]:
        """Find all MKV files in source directory."""
        path = Path(source_path)

        if path.is_file():
            return [path] if path.suffix.lower() == '.mkv' else []

        # Find all MKV files, sorted by size (largest first)
        mkv_files = list(path.glob(_MKV_GLOB))
        mkv_files.sort(key=lambda f: f.stat().st_size, reverse=True)

        return mkv_files

    def _discover_audio_files(self, source_path: str) -> list[Path]:
        """Find all audio files in source directory."""
        path = Path(source_path)

        if path.is_file():
            return [path] if path.suffix.lower() in AUDIO_FILE_EXTENSIONS else []

        audio_files = [
            f for f in path.iterdir()
            if f.is_file() and f.suffix.lower() in AUDIO_FILE_EXTENSIONS
        ]
        audio_files.sort(key=lambda f: f.name)

        return audio_files

    async def _passthrough_audio(self, job: TranscodeJob):
        """Copy audio files directly to audio output folder (no transcoding).

        Honors ARM's output_path when present; falls back to a clean leaf
        directory under completed_path otherwise (legacy clients).
        """
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            job_id=job.id,
            label=job.title,
        )
        # Re-fetch the row to pick up output_path even when callers
        # don't load full job metadata (e.g. _discover_or_passthrough).
        async with get_db() as db_sess:
            result = await db_sess.execute(
                select(TranscodeJobDB).where(TranscodeJobDB.id == job.id)
            )
            job_db = result.scalar_one_or_none()
            arm_output_path = job_db.output_path if job_db else None

        if arm_output_path:
            output_dir = Path(settings.completed_path) / arm_output_path
        else:
            clean_title = clean_title_for_filesystem(job.title)
            output_dir = Path(settings.completed_path) / clean_title
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: os.makedirs(output_dir, exist_ok=True))

        audio_files = await loop.run_in_executor(None, self._discover_audio_files, job.source_path)

        logger.info(f"Audio passthrough: copying {len(audio_files)} audio files to {output_dir}")

        for f in audio_files:
            await async_copy_file(str(f), str(output_dir / f.name))

        await self._update_job(
            job.id,
            output_path=str(output_dir),
            total_tracks=len(audio_files),
            status=JobStatus.COMPLETED,
            progress=100.0,
            completed_at=datetime.now(timezone.utc),
        )

        logger.info(f"Completed audio passthrough for job {job.id}: {job.title}")
        await self._notify_arm_callback(job, "completed")

        # Clean up source directory if delete_source is set (non-fatal)
        if settings.delete_source:
            try:
                await self._cleanup_source(job.source_path)
                logger.info(f"Cleaned up source: {job.source_path}")
            except OSError as e:
                logger.warning(f"Could not clean up source {job.source_path}: {e}")

    def _detect_video_type(self, title: str, source_path: str) -> str:
        """Detect whether content is a TV show or movie based on naming patterns.

        ARM uses patterns like 'Show S01', 'Show S01E01', 'Show_S02E03'
        for TV rips. Returns 'tv' or 'movie'.
        """
        # Check both title and source directory name
        dir_name = Path(source_path).name
        for text in [title, dir_name]:
            if re.search(r'S\d{1,2}(E\d{1,2})?', text, re.IGNORECASE):
                return "tv"
        return "movie"

    @staticmethod
    def _classify_media_type(height: int) -> str:
        """Return media type label from resolution height."""
        if height < 720:
            return "DVD"
        if height <= 1080:
            return "Blu-ray"
        return "UHD Blu-ray"

    @staticmethod
    def _format_resolution(height: int) -> str:
        """Return resolution string from height."""
        if height < 720:
            return "480p"
        if height == 720:
            return "720p"
        if height == 1080:
            return "1080p"
        if height == 2160:
            return "2160p"
        return f"{height}p"

    def _get_codec_name(self, overrides: dict | None = None) -> str:
        """Map video encoder to a display name for folder naming.

        Uses the active scheme's default preset to determine the encoder,
        with legacy override support for backward compatibility.
        """
        from main import active_scheme
        if overrides and "video_encoder" in overrides:
            encoder = str(overrides["video_encoder"]).lower()
        else:
            default_preset = active_scheme.default_preset
            encoder = str(default_preset.shared.get("video_encoder", "x265")).lower()
        h265_names = {
            "nvenc_h265", "hevc_nvenc", "vaapi_h265", "hevc_vaapi",
            "amf_h265", "hevc_amf", "qsv_h265", "hevc_qsv", "x265",
        }
        h264_names = {
            "nvenc_h264", "h264_nvenc", "vaapi_h264", "h264_vaapi",
            "amf_h264", "h264_amf", "qsv_h264", "h264_qsv", "x264",
        }
        if encoder in h265_names:
            return "HEVC"
        if encoder in h264_names:
            return "H264"
        return encoder.upper()

    def _build_folder_name(
        self, clean_title: str, year: str | None,
        resolution: tuple[int, int] | None, overrides: dict | None,
    ) -> str:
        """Build metadata-enriched folder name like 'Serial Mom (1994) 480p DVD HEVC'."""
        parts = [clean_title]
        if year:
            parts.append(f"({year})")
        if resolution:
            height = resolution[1]
            parts.extend([
                self._format_resolution(height),
                self._classify_media_type(height),
                self._get_codec_name(overrides),
            ])
        return clean_title_for_filesystem(" ".join(parts))

    def _determine_output_path(
        self, title: str, source_path: str,
        resolution: tuple[int, int] | None = None,
        overrides: dict | None = None,
        *, db_year: str | None = None, db_video_type: str | None = None,
    ) -> Path:
        """Determine the output directory path (legacy fallback).

        Builds a metadata-enriched folder name like:
          Serial Mom (1994) 480p DVD HEVC

        ARM normally sends an explicit output_path via the webhook and
        we use that directly; this fallback only fires when the webhook
        omits output_path (legacy producer). Lands at the share root
        with no type-subdir partitioning - operators using this path
        should upgrade ARM.
        """
        clean_title = clean_title_for_filesystem(title)

        # Prefer year from DB; fall back to extracting from directory name
        year = db_year if db_year and db_year not in ("", "0000") else None
        if not year:
            dir_name = Path(source_path).name
            year_match = re.search(r'\((\d{4})\)', dir_name)
            year = year_match.group(1) if year_match else None

        folder_name = self._build_folder_name(clean_title, year, resolution, overrides)
        return Path(settings.completed_path) / folder_name

    async def _transcode_file_handbrake(
        self,
        source: Path,
        output: Path,
        job_id: int,
        overrides: dict | None = None,
        *,
        preset_snapshot: PresetSnapshot | None = None,
        file_index: int = 0,
        total_files: int = 1,
    ):
        """Transcode a single file using HandBrake.

        ``file_index`` (0-based) and ``total_files`` are used to scale the
        per-file progress value HandBrake emits (0..100% per file) into an
        overall job-progress value (0..100% across all files). Without
        this scaling, the rate-limiter in :meth:`_update_progress` would
        see a backwards jump at every file boundary and suppress all
        writes after file 0 completes, leaving the UI stuck at the
        file-0 high-water mark for the rest of the encode.
        """
        resolution = await self._get_video_resolution(source)
        effective = await self._resolve_effective_settings(
            resolution, overrides, snapshot=preset_snapshot,
        )

        # --json makes HandBrake emit structured progress blocks regardless
        # of TTY. Without it, HandBrakeCLI 1.10.x is silent on progress when
        # stdout is a pipe, leaving the UI stuck at 0% (jobs look "hung").
        cmd = ["HandBrakeCLI", "--json", "-i", str(source), "-o", str(output)]

        video_encoder = effective.get("video_encoder")
        if video_encoder:
            cmd.extend(["--encoder", str(video_encoder)])

        cmd.extend(["-q", str(effective.get("video_quality", 22))])

        handbrake_preset = effective.get("handbrake_preset")
        if handbrake_preset:
            cmd.extend(["--preset", str(handbrake_preset)])

        extra_args = effective.get("handbrake_extra_args")
        if extra_args:
            cmd.extend(extra_args)

        # Audio handling
        audio_encoder = effective.get("audio_encoder", "copy")
        if audio_encoder == "copy":
            cmd.extend(["--aencoder", "copy",
                         "--audio-copy-mask", "aac,ac3,eac3,dts,dtshd,truehd,flac,mp2,mp3",
                         "--audio-fallback", "aac"])
        else:
            cmd.extend(["--aencoder", str(audio_encoder)])

        # Subtitle handling
        subtitle_mode = effective.get("subtitle_mode", "all")
        if subtitle_mode == "all":
            cmd.extend(["--all-subtitles"])
        elif subtitle_mode == "first":
            cmd.extend(["--subtitle", "1"])
        # "none" = no subtitle flags

        logger.debug(f"HandBrake command: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            # No `limit=` here - we read in fixed chunks below to avoid the
            # asyncio readline() 64KB-default deadlock on CR-overwritten
            # progress output. HandBrake emits progress as
            # `\r12.34 % (45.67 fps, ...)\r12.35 % ...` with no \n in between.
        )

        # HandBrake --json emits multi-line `Progress: {...}` blocks; this
        # parser accumulates them across the one-line-at-a-time handler calls
        # and yields (per-file fraction 0..1, fps) on each block close.
        hb_progress = _HandBrakeJsonProgress()

        def _handbrake_handler(line: str) -> None:
            parsed = hb_progress.feed(line)
            if parsed is None:
                return
            file_progress_fraction, fps = parsed
            # Scale per-file progress to overall job progress so the
            # rate-limiter sees monotonically-increasing values across
            # file boundaries.
            overall = (file_index + file_progress_fraction) / total_files * 100.0
            # _update_progress is async but the handler interface is sync;
            # schedule the coroutine without blocking the reader. The
            # progress write itself is rate-limited inside _update_progress,
            # so the create_task fan-out cannot flood the DB.
            self._spawn_progress_task(
                self._update_progress(job_id, overall, fps=fps)
            )

        try:
            await self._stream_progress_lines(
                process, job_id, line_handler=_handbrake_handler,
            )
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()

        if process.returncode != 0:
            raise RuntimeError(f"HandBrake failed with exit code {process.returncode}")
        if not output.exists():
            raise RuntimeError(f"Output file was not created: {output}")

        logger.info(f"Transcoded: {source.name} -> {output.name}")

    @staticmethod
    def _resolve_ffmpeg_encoder(family: str, encoder_name: str) -> str:
        """Map encoder family + name to the FFmpeg encoder identifier."""
        is_h265 = "h265" in encoder_name or "hevc" in encoder_name
        hw_families = {
            "nvenc": ("hevc_nvenc", "h264_nvenc"),
            "vaapi": ("hevc_vaapi", "h264_vaapi"),
            "amf": ("hevc_amf", "h264_amf"),
            "qsv": ("hevc_qsv", "h264_qsv"),
        }
        if family in hw_families:
            h265_enc, h264_enc = hw_families[family]
            return h265_enc if is_h265 else h264_enc
        if family == "software":
            return "libx265" if encoder_name == "x265" else "libx264"
        return encoder_name

    @staticmethod
    def _ffmpeg_hwaccel_flags(family: str) -> list[str]:
        """Return hardware acceleration input flags for the encoder family."""
        if family == "nvenc":
            return ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
        if family == "vaapi":
            vaapi_device = os.environ.get("VAAPI_DEVICE", "/dev/dri/renderD128")
            return ["-hwaccel", "vaapi", "-hwaccel_device", vaapi_device, "-hwaccel_output_format", "vaapi"]
        if family == "qsv":
            return ["-hwaccel", "qsv", "-hwaccel_output_format", "qsv"]
        return []

    @staticmethod
    def _ffmpeg_quality_flags(family: str, quality) -> list[str]:
        """Return quality-related flags for the encoder family."""
        q = str(quality)
        mapping = {
            "nvenc": ["-preset", "p4", "-cq", q, "-b:v", "0"],
            "vaapi": ["-rc_mode", "CQP", "-qp", q],
            "amf": ["-rc", "cqp", "-qp_i", q, "-qp_p", q],
            "qsv": ["-global_quality", q],
            "software": ["-crf", q, "-preset", "medium"],
        }
        return mapping.get(family, [])

    @staticmethod
    def _ffmpeg_upscale_filter(family: str, resolution: Optional[tuple[int, int]]) -> list[str]:
        """Return upscale filter flags for low-res sources (DVD → 720p)."""
        if not resolution or resolution[1] >= 720:
            return []
        filters = {
            "nvenc": "scale_cuda=1280:-2",
            "vaapi": "scale_vaapi=w=1280:h=-2",
            "qsv": "vpp_qsv=w=1280:h=-2",
        }
        vf = filters.get(family, "scale=1280:-2")
        logger.info(f"Low-res source ({resolution[0]}x{resolution[1]}), upscaling to 720p")
        return ["-vf", vf]

    def _build_ffmpeg_command(
        self, source: Path, output: Path,
        effective: dict[str, Any],
        resolution: Optional[tuple[int, int]] = None,
    ) -> list[str]:
        """Build FFmpeg command from resolved effective settings."""
        encoder_name = str(effective.get("video_encoder", "x265"))
        family = self._detect_encoder_family(encoder_name)
        quality = effective.get("video_quality", 22)

        ffmpeg_encoder = self._resolve_ffmpeg_encoder(family, encoder_name)

        cmd = ["ffmpeg", "-y"]
        cmd.extend(self._ffmpeg_hwaccel_flags(family))
        cmd.extend(["-i", str(source)])

        # Stream mapping
        subtitle_mode = effective.get("subtitle_mode", "all")
        cmd.extend(["-map", "0:v:0", "-map", "0:a?"])
        if subtitle_mode == "all":
            cmd.extend(["-map", "0:s?"])
        elif subtitle_mode == "first":
            cmd.extend(["-map", "0:s:0?"])

        cmd.extend(["-c:v", ffmpeg_encoder])
        cmd.extend(self._ffmpeg_quality_flags(family, quality))
        cmd.extend(self._ffmpeg_upscale_filter(family, resolution))

        # Audio handling
        audio_encoder = effective.get("audio_encoder", "copy")
        cmd.extend(["-c:a", "copy"] if audio_encoder == "copy" else ["-c:a", str(audio_encoder)])

        if subtitle_mode in ("all", "first"):
            cmd.extend(["-c:s", "copy"])

        cmd.append(str(output))
        return cmd

    async def _transcode_file_ffmpeg(
        self,
        source: Path,
        output: Path,
        job_id: int,
        overrides: dict | None = None,
        *,
        preset_snapshot: PresetSnapshot | None = None,
        file_index: int = 0,
        total_files: int = 1,
    ):
        """Transcode a single file using FFmpeg."""
        resolution = await self._get_video_resolution(source)
        effective = await self._resolve_effective_settings(
            resolution, overrides, snapshot=preset_snapshot,
        )
        cmd = self._build_ffmpeg_command(source, output, effective, resolution)

        logger.debug(f"FFmpeg command: {' '.join(cmd)}")

        # Run FFmpeg and parse progress
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            # See HandBrake reader for the buffer-size rationale.
        )

        # Get duration for progress calculation
        duration = await self._get_video_duration(source)

        def _ffmpeg_handler(line: str) -> None:
            # Parse FFmpeg progress: "time=00:01:23.45"
            match = _TIME_PATTERN.search(line)
            if match and duration:
                hours, mins, secs = match.groups()
                current_secs = int(hours) * 3600 + int(mins) * 60 + float(secs)
                file_progress = min(100, (current_secs / duration) * 100)
                # FFmpeg stats line includes "fps=NN" or "fps=NN.N".
                fps_match = _FFMPEG_FPS_PATTERN.search(line)
                fps = float(fps_match.group(1)) if fps_match else None
                # Scale per-file progress to overall job progress so the
                # rate-limiter sees monotonically-increasing values across
                # file boundaries.
                overall = (file_index + file_progress / 100.0) / total_files * 100.0
                # _update_progress is async but the handler interface is sync;
                # schedule the coroutine without blocking the reader.
                self._spawn_progress_task(
                    self._update_progress(job_id, overall, fps=fps)
                )

        try:
            await self._stream_progress_lines(
                process, job_id, line_handler=_ffmpeg_handler,
            )
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()

        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg failed with exit code {process.returncode}")

        if not output.exists():
            raise RuntimeError(f"Output file was not created: {output}")

        logger.info(f"Transcoded: {source.name} -> {output.name}")

    async def _get_video_resolution(self, path: Path) -> Optional[tuple[int, int]]:
        """Get video resolution (width, height) using ffprobe."""
        try:
            result = await asyncio.create_subprocess_exec(
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0:s=x",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()
            parts = stdout.decode().strip().split("x")
            return (int(parts[0]), int(parts[1]))
        except Exception:
            return None

    async def _get_video_duration(self, path: Path) -> Optional[float]:
        """Get video duration in seconds using ffprobe."""
        try:
            result = await asyncio.create_subprocess_exec(
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()
            return float(stdout.decode().strip())
        except Exception:
            return None

    async def _cleanup_source(self, source_path: str):
        """Remove source files after successful transcode."""
        path = Path(source_path)
        loop = asyncio.get_event_loop()

        exists = await loop.run_in_executor(None, path.exists)
        if not exists:
            logger.warning(f"Source already removed: {source_path}")
            return

        is_file = await loop.run_in_executor(None, path.is_file)
        if is_file:
            await loop.run_in_executor(None, path.unlink)
        elif await loop.run_in_executor(None, path.is_dir):
            await async_rmtree(str(path))
