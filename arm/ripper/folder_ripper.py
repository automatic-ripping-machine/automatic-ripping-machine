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
        file_handler = create_file_handler(log_file)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        if root_logger.level > logging.DEBUG:
            root_logger.setLevel(logging.DEBUG)
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
        # "all" with --minlength lets MakeMKV handle track selection.
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
            f"--minlength={job.config.MINLENGTH}",
        ]
        log.info("Ripping all tracks from folder source: %s", job.source_path)
        collections.deque(run(cmd, OutputType.MSG), maxlen=0)
        for track in job.tracks:
            track.ripped = True
        db.session.commit()

        # 6. Reconcile filenames
        _reconcile_filenames(job, rawpath)

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
