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
    process_single_tracks,
    rip_mainfeature,
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

        # 5. Rip
        mainfeature = bool(
            int(getattr(job.config, "MAINFEATURE", 0) or 0)
        )
        if mainfeature:
            # Find the best track for mainfeature rip
            best = (
                Track.query.filter_by(job_id=job.job_id)
                .order_by(
                    Track.chapters.desc(),
                    Track.length.desc(),
                    Track.filesize.desc(),
                    Track.track_number.asc(),
                )
                .first()
            )
            if best:
                rip_mainfeature(job, best, rawpath)
            else:
                log.warning("MAINFEATURE enabled but no tracks found, falling back to all tracks")
                process_single_tracks(job, rawpath, "auto")
        else:
            process_single_tracks(job, rawpath, "auto")

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
