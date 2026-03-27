"""Folder import rip pipeline.

Parallel entry point to arm_ripper.rip_visual_media() — orchestrates the
MakeMKV rip pipeline for folder-based imports (no physical drive).
"""
import logging
import os

import structlog

import arm.config.config as cfg
from arm.database import db
from arm.models.job import JobState
from arm.models.track import Track
from arm.ripper import utils
from arm.ripper.logger import create_file_handler, log_filename
from arm.ripper.makemkv import (
    _reconcile_filenames,
    prep_mkv,
    prescan_track_info,
    setup_rawpath,
)

log = logging.getLogger(__name__)

# MakeMKV's default --minlength when not explicitly passed (120 seconds).
# Titles shorter than this are skipped during rip.
MAKEMKV_DEFAULT_MINLENGTH = 120


def _build_title_map_from_tracks(job, rawpath):
    """Build output-index -> original-title-id map using prescan track data.

    MakeMKV processes titles in ascending order by title number and
    skips those shorter than its minlength threshold (default 120s).
    The output files are numbered sequentially (_t00, _t01, ...).
    By filtering prescan tracks with the same threshold, we can pair
    them positionally with the output files.

    Falls back to threshold search if the default doesn't match.

    Returns dict mapping output_index -> original_track_number.
    """
    if not rawpath or not os.path.isdir(rawpath):
        return {}

    output_files = sorted(
        f for f in os.listdir(rawpath)
        if os.path.isfile(os.path.join(rawpath, f)) and f.endswith(".mkv")
    )
    if not output_files:
        return {}

    num_output = len(output_files)

    # Get all prescan tracks sorted by track number (ascending)
    tracks = sorted(job.tracks, key=lambda t: int(t.track_number)
                    if t.track_number and str(t.track_number).isdigit() else 0)

    if not tracks:
        return {}

    # If count matches directly, no titles were skipped - identity map
    if len(tracks) == num_output:
        return {i: int(t.track_number) for i, t in enumerate(tracks)}

    # Try MakeMKV's default minlength threshold first (120s).
    # Tracks >= minlength are kept; shorter ones are skipped.
    minlength = MAKEMKV_DEFAULT_MINLENGTH
    qualifying = [t for t in tracks if t.length and t.length >= minlength]
    if len(qualifying) == num_output:
        title_map = {i: int(t.track_number) for i, t in enumerate(qualifying)}
        log.info(
            "Title map: %d output files matched %d tracks with length >= %ds (default minlength)",
            num_output, len(qualifying), minlength,
        )
        return title_map

    # Fallback: search for the threshold that matches the output count.
    # This handles cases where MakeMKV uses a different threshold.
    lengths = sorted(set(t.length for t in tracks if t.length is not None))
    for cutoff in lengths:
        qualifying = [t for t in tracks if t.length and t.length >= cutoff]
        if len(qualifying) == num_output:
            title_map = {i: int(t.track_number) for i, t in enumerate(qualifying)}
            log.info(
                "Title map: %d output files matched %d tracks with length >= %ds",
                num_output, len(qualifying), cutoff,
            )
            return title_map

    log.warning(
        "Title map: could not find threshold matching %d output files "
        "from %d prescan tracks - falling back to pattern matching",
        num_output, len(tracks),
    )
    return {}


def rip_folder(job):
    """Run the folder import rip pipeline.

    Steps:
      1. Validate source folder exists and has valid disc structure
      2. Set status to VIDEO_RIPPING, call prep_mkv()
      3. Setup raw output path
      4. Pre-scan tracks
      5. Rip (mainfeature or all tracks)
      6. Reconcile filenames
      7. Notify transcoder if configured
      8. Set status to TRANSCODE_WAITING on success, FAILURE on error
      9. No eject step (no physical drive)
    """
    file_handler = None
    try:
        # 0. Set up per-job log file so the UI can display rip progress
        log_file = log_filename(job.job_id)
        job.logfile = log_file
        db.session.commit()

        root_logger = logging.getLogger()
        log_level = cfg.arm_config.get("LOGLEVEL", "INFO")
        file_handler = create_file_handler(log_file)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
        root_logger.setLevel(log_level)
        log.info("Starting folder import rip for job %s: %s", job.job_id, job.source_path)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            job_id=job.job_id,
            source_type="folder",
            source_path=job.source_path,
        )

        # 1. Validate source folder
        source = job.source_path
        if not source or not os.path.isdir(source):
            raise FileNotFoundError(f"Source folder does not exist: {source}")

        from arm.ripper.folder_scan import detect_disc_type
        detect_disc_type(source)

        # 2. Set status and prepare MakeMKV
        job.status = JobState.VIDEO_RIPPING.value
        db.session.commit()
        prep_mkv()

        # 3. Setup raw output path
        rawpath = setup_rawpath(job, job.build_raw_path())
        job.raw_path = rawpath
        db.session.commit()

        # 4. Pre-scan tracks (skip if already scanned during job creation)
        db.session.expire(job, ['tracks'])
        existing_tracks = list(job.tracks)
        if existing_tracks:
            log.info("Skipping prescan — %d tracks already exist from review", len(existing_tracks))
        else:
            prescan_track_info(job)

        # 5. Rip — always use "all" mode for folder imports.
        # MakeMKV's per-track numbering from file: sources doesn't match
        # the prescan track numbers, so single-track extraction fails.
        import collections
        import shlex
        from arm.ripper.makemkv import run, OutputType, progress_log

        cmd = ["mkv"]
        cmd += shlex.split(job.config.MKV_ARGS or "")
        cmd += [
            f"--progress={progress_log(job)}",
            job.makemkv_source,
            "all",
            rawpath,
        ]
        log.info("Ripping all tracks from folder source: %s", job.source_path)
        collections.deque(run(cmd, OutputType.MSG), maxlen=0)

        # 6. Build deterministic title map from prescan track data.
        # MakeMKV processes titles in ascending order and skips short ones.
        # The output files _t00.._tNN map positionally to the prescan
        # tracks that MakeMKV actually kept, sorted by track number.
        # We know from the DB which tracks exist and their lengths, and
        # from disk which output files were produced.
        title_map = _build_title_map_from_tracks(job, rawpath)
        if title_map:
            log.info("Title map from prescan: %s", title_map)

        # 7. Reconcile filenames using deterministic title_map.
        _reconcile_filenames(job, rawpath, title_map=title_map)

        # Mark tracks as ripped only if their file actually exists on disk
        # (after reconciliation so filenames are corrected).
        actual_files = set(os.listdir(rawpath)) if os.path.isdir(rawpath) else set()
        for track in job.tracks:
            if track.filename and track.filename in actual_files:
                track.ripped = True
            else:
                track.ripped = False
        db.session.commit()
        log.info("Ripped %d of %d tracks to %s",
                 sum(1 for t in job.tracks if t.ripped),
                 len(list(job.tracks)), rawpath)

        # 7. Notify transcoder if configured
        transcoder_url = cfg.arm_config.get("TRANSCODER_URL", "")
        if transcoder_url:
            utils.transcoder_notify(
                cfg.arm_config,
                "ARM Notification",
                f"{job.title} folder import rip complete.",
                job,
            )

        # 8. Set status to TRANSCODE_WAITING
        job.status = JobState.TRANSCODE_WAITING.value
        db.session.commit()
        log.info("Folder import rip complete for job %s", job.job_id)

    except Exception as exc:
        log.error("Folder import rip failed for job %s: %s", getattr(job, "job_id", "?"), exc)
        try:
            job.status = JobState.FAILURE.value
            job.errors = str(exc)
            db.session.commit()
        except Exception:
            log.exception("Failed to update job status to FAILURE")
        raise
    finally:
        # Clean up the per-job file handler and structlog context
        if file_handler:
            logging.getLogger().removeHandler(file_handler)
            file_handler.close()
        structlog.contextvars.clear_contextvars()
        # Release scoped session to prevent DB connection pool exhaustion
        # (this function runs in a daemon thread)
        db.session.remove()
