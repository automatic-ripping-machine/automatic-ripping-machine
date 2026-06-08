"""Shared background-thread body for folder + ISO import endpoints.

Both folder and ISO import endpoints kick off a daemon thread that:
  1. Loads the Job by id.
  2. Creates a logfile + attaches a file handler.
  3. Runs MakeMKV prep + prescan to populate tracks.
  4. Auto-disables tracks shorter than MINLENGTH (MakeMKV silently skips
     them anyway, and leaving them enabled produces a misleading UI).
  5. Transitions the job to MANUAL_PAUSED so the user can review tracks.
  6. Cleans up the scoped DB session to prevent connection-pool exhaustion.

Previously this body was duplicated byte-for-byte (modulo log strings)
between arm.api.v1.folder and arm.api.v1.iso. SonarCloud flagged the
duplication; centralising here keeps the two endpoints DRY.
"""
import logging

from arm_contracts.enums import SkipReason

import arm.config.config as cfg
from arm.database import db
from arm.models.job import Job, JobState

log = logging.getLogger(__name__)


def auto_disable_short_tracks(job, minlength: int) -> int:
    """Disable tracks below `minlength` seconds and tag with skip_reason.

    Sets both process=False (the rip-time gate) and enabled=False
    (the UI-checkbox state), and tags skip_reason=too_short so the
    review widget renders the row as filtered. Returns the count
    disabled.
    """
    disabled_count = 0
    for track in job.tracks:
        if track.length is not None and track.length < minlength:
            track.process = False
            track.enabled = False
            track.skip_reason = SkipReason.too_short.value
            disabled_count += 1
    return disabled_count


def prescan_and_wait(job_id: int) -> None:
    """Background: prescan tracks with MakeMKV, then move job to MANUAL_PAUSED.

    Designed to run in a daemon thread. Must clean up the scoped DB
    session on exit to prevent connection-pool exhaustion. On failure
    the job still transitions to MANUAL_PAUSED with the error stored in
    `job.errors` so the UI can surface it without leaving the job stuck.
    """
    from arm.ripper.makemkv import prep_mkv, prescan_track_info

    # Daemon thread - use higher commit retry timeout
    db.session.commit_timeout = 90
    _file_handler = None
    try:
        job = Job.query.get(job_id)
        if not job:
            log.error("Prescan: job %s not found", job_id)
            return

        # Set logfile and create file handler so prescan output is captured
        from arm.ripper.logger import log_filename, create_file_handler
        import logging as _logging
        log_file = log_filename(job_id)
        job.logfile = log_file
        db.session.commit()
        try:
            _file_handler = create_file_handler(log_file)
            _log_level = cfg.arm_config.get("LOGLEVEL", "INFO")
            _file_handler.setLevel(_log_level)
            _root = _logging.getLogger()
            _root.addHandler(_file_handler)
            _root.setLevel(_log_level)
        except OSError:
            _file_handler = None
            log.warning("Could not create log file handler for %s", log_file)

        try:
            prep_mkv()
            prescan_track_info(job)

            minlength = int(cfg.arm_config.get("MINLENGTH", 120))
            disabled_count = auto_disable_short_tracks(job, minlength)
            if disabled_count:
                log.info(
                    "Auto-disabled %d tracks shorter than %ds",
                    disabled_count, minlength,
                )

            job.status = JobState.MANUAL_PAUSED.value
            db.session.commit()
            log.info(
                "Prescan complete for job %s - %d tracks found, waiting for review",
                job_id, len(list(job.tracks)),
            )
        except Exception as exc:
            log.error("Prescan failed for job %s: %s", job_id, exc)
            try:
                job.status = JobState.MANUAL_PAUSED.value
                job.errors = f"Prescan failed: {exc}"
                db.session.commit()
            except Exception:
                log.exception(
                    "Failed to update job %s status after prescan error",
                    job_id,
                )
    finally:
        # Clean up file handler if we created one
        if _file_handler is not None:
            import logging as _logging
            _logging.getLogger().removeHandler(_file_handler)
            _file_handler.close()
        # Release the scoped session for this thread to prevent pool exhaustion
        db.session.remove()
