"""Folder import rip pipeline.

Parallel entry point to arm_ripper.rip_visual_media() — orchestrates the
MakeMKV rip pipeline for folder-based imports (no physical drive).
"""
import logging
import os

import arm.config.config as cfg
from arm.database import db
from arm.models.job import JobState
from arm.models.track import Track
from arm.ripper import utils
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
    try:
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

        # 4. Pre-scan tracks
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
