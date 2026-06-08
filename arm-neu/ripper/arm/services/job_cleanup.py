"""Orphaned job cleanup — runs once on container startup.

Detects ARM-owned jobs stuck in intermediate states (identifying, ripping,
waiting, etc.) after a container restart and marks them as failed. Transcoder-
owned states (transcoding, waiting_transcode) are left untouched.

Uses the existing clean_old_jobs() for PID-based detection first, then
sweeps for any remaining orphans (e.g. folder imports with no PID).
"""

import logging

from arm.database import db
from arm.models.job import Job, JobState, JOB_STATUS_FINISHED, JOB_STATUS_TRANSCODING
from arm.models.notifications import Notifications
from arm.ripper.utils import clean_old_jobs

logger = logging.getLogger(__name__)

RESTART_ERROR = "ARM restarted \u2014 process lost. Re-insert disc to retry."


def cleanup_orphaned_jobs() -> int:
    """Fail ARM-owned jobs left in intermediate states after a restart.

    Returns the number of jobs cleaned up.
    """
    # Phase 1: PID-based cleanup for jobs that have a PID recorded
    clean_old_jobs()

    # Phase 2: Catch-all for remaining ARM-owned intermediate jobs
    # (covers folder imports with no PID, or jobs where PID was never set)
    skip_states = {s.value for s in JOB_STATUS_FINISHED | JOB_STATUS_TRANSCODING}
    orphans = (
        db.session.query(Job)
        .filter(Job.status.notin_(skip_states))
        .all()
    )

    count = 0
    for job in orphans:
        logger.info(
            "Orphaned job %d (%s) in state '%s' — marking as failed",
            job.job_id, job.title, job.status,
        )
        job.status = JobState.FAILURE.value
        job.errors = RESTART_ERROR
        if job.drive is not None:
            try:
                job.drive.release_current_job()
            except Exception:
                logger.warning("Failed to release drive for job %d", job.job_id, exc_info=True)
        count += 1

    if count:
        db.session.commit()
        logger.info("Cleaned up %d orphaned job(s)", count)

        # Write a summary row to the in-app history feed. The notifications
        # outbox dispatcher only fires on per-job lifecycle events, so this
        # system-level message stays UI-only (intentional — we don't have a
        # contracts event for "ARM restarted, N orphans swept").
        titles = ", ".join(j.title or f"Job {j.job_id}" for j in orphans)
        try:
            db.session.add(Notifications(
                f"ARM Startup: {count} orphaned job(s) cleaned up",
                f"Failed jobs: {titles}",
            ))
            db.session.commit()
        except Exception:
            logger.warning("Could not record orphan cleanup notification", exc_info=True)

    return count
