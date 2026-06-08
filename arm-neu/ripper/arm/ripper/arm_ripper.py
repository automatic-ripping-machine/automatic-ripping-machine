""" Main file for running DVDs/Blu-rays/CDs/data ?
It would help clear up main and make things easier to find
"""
import logging
from collections import Counter
from datetime import datetime, timezone
from importlib.util import find_spec
from pathlib import Path
from uuid import uuid4
import sys

# If the arm module can't be found, add the folder this file is in to PYTHONPATH
# This is a bad workaround for non-existent packaging
if find_spec("arm") is None:
    sys.path.append(str(Path(__file__).parents[2]))

from arm.ripper import utils, makemkv  # noqa E402
from arm.database import db  # noqa E402
import arm.constants as constants  # noqa E402
from arm.models.job import JobState  # noqa E402
from arm.notifications import publish_event  # noqa E402
from arm_contracts import (  # noqa E402
    JobRipCompleteEvent,
    JobTranscodeCompleteEvent,
    JobFailedEvent,
)
from arm.ripper._notify_helpers import (  # noqa E402,F401
    job_disc_type as _job_disc_type,
    rip_duration_seconds as _rip_duration_seconds,
)


def _publish_job_failed(job, phase: str) -> None:
    """Publish a ``job.failed`` event for the current FAILURE state.

    Truncates ``job.errors`` to 200 chars to match the contracts'
    expectation of a one-line summary suitable for a notification body.
    """
    publish_event(JobFailedEvent(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        job_id=job.job_id,
        job_title=job.title or "",
        job_disc_type=_job_disc_type(job),
        job_imdb_id=job.imdb_id,
        phase=phase,
        error_message=(job.errors or "unknown failure")[:200],
        error_code=None,
    ))


def _post_rip_handoff(job):
    """Single source of truth for post-rip job status.

    Handles all four terminal outcomes:
      A. SKIP_TRANSCODE=true (per-job or global) -> finalize locally, SUCCESS
      B. No TRANSCODER_URL configured -> finalize locally, SUCCESS
      C. Handoff succeeds -> TRANSCODE_WAITING (transcoder callback sets final)
      D. Handoff fails -> FAILURE (not TRANSCODE_WAITING - failed handoff should
         not look like a pending one)

    Decision precedence for skip:
      1. Per-job config.SKIP_TRANSCODE (if not None)
      2. Global SKIP_TRANSCODE (default False)

    Always publishes JobRipCompleteEvent when the handoff didn't fail.
    """
    import arm.config.config as cfg
    from arm.ripper.naming import finalize_output

    transcoder_url = cfg.arm_config.get('TRANSCODER_URL', '')

    # Determine skip_transcode value: per-job override > global config
    if job.config.SKIP_TRANSCODE is not None:
        skip = job.config.SKIP_TRANSCODE
    else:
        skip = cfg.arm_config.get('SKIP_TRANSCODE', False)

    if not transcoder_url or skip:
        reason = "SKIP_TRANSCODE is enabled" if skip else "No transcoder configured"
        logging.info("%s - finalizing output locally", reason)
        finalize_output(job)
        job.status = JobState.SUCCESS.value
        db.session.commit()
    else:
        # Hand off to transcoder. transcoder_notify returns False on any
        # transport failure, non-2xx response, or auth failure - it logs
        # the specific cause internally. Status is TRANSCODE_WAITING on
        # success; FAILURE on handoff failure (not TRANSCODE_WAITING -
        # a failed handoff should not look like a pending one).
        if utils.transcoder_notify(
            cfg.arm_config, constants.NOTIFY_TITLE,
            f"{job.title} rip complete.", job,
        ):
            job.status = JobState.TRANSCODE_WAITING.value
        else:
            job.status = JobState.FAILURE.value
            job.errors = "Transcoder handoff failed (see transcoder logs)"
        db.session.commit()
        if job.status == JobState.FAILURE.value:
            # Handoff itself failed even though the rip succeeded — surface
            # this as a rip-phase failure rather than letting it look like
            # a clean rip-complete.
            _publish_job_failed(job, phase="rip")

    # The rip itself is done — emit job.rip_complete unconditionally
    # (channels decide what to do via subscribed_events). We still skip
    # publishing on a failed handoff so subscribers don't get a
    # "complete" message right before a "failed" message for the same
    # phase.
    if job.status != JobState.FAILURE.value:
        publish_event(JobRipCompleteEvent(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            job_id=job.job_id,
            job_title=job.title or "",
            job_disc_type=_job_disc_type(job),
            job_imdb_id=job.imdb_id,
            rip_duration_seconds=_rip_duration_seconds(job),
            track_count=job.tracks.count(),
        ))


def check_empty_rip(job) -> bool:
    """Return True and stage a structured job.errors message if no tracks were ripped."""
    tracks = list(job.tracks)
    if not tracks:
        return False
    if any(t.ripped for t in tracks):
        return False
    reasons = Counter(t.skip_reason or "unknown" for t in tracks)
    breakdown = ", ".join(f"{n} {reason}" for reason, n in reasons.most_common())
    job.errors = (
        f"All {len(tracks)} tracks were filtered or unprocessed: {breakdown}. "
        f"Check MINLENGTH (current: {job.config.MINLENGTH}s) and "
        f"MAXLENGTH ({job.config.MAXLENGTH}s)."
    )
    return True


def rip_visual_media(have_dupes, job, logfile, protection):
    """
    Main ripping function for dvd and Blu-rays, movies or series.

    Pipeline: rip with MakeMKV -> persist paths to DB -> notify -> done.
    Transcoding is handled by the external transcoder service.

    :param have_dupes: Does this disc already exist in the database
    :param job: Current job
    :param logfile: Current logfile
    :param protection: Does the disc have 99 track protection
    :return: None
    """
    # Compute final path for DB/webhook metadata
    final_directory = job.build_final_path()

    # Check folders for already ripped jobs -> creates folder (handles collisions)
    final_directory = utils.check_for_dupe_folder(have_dupes, final_directory, job)

    # Persist path to DB
    utils.database_updater({'path': final_directory}, job)
    # Save poster image from disc if enabled
    utils.save_disc_poster(final_directory, job)

    logging.info("************* Ripping disc with MakeMKV *************")
    job.status = JobState.VIDEO_RIPPING.value
    db.session.commit()
    try:
        makemkv_out_path = makemkv.makemkv(job)
    except makemkv.UpdateKeyRunTimeError as key_error:
        raise utils.RipperException(
            "MakeMKV key update failed — cannot decrypt discs. "
            "Check network access to forum.makemkv.com or set "
            "MAKEMKV_PERMA_KEY in arm.yaml."
        ) from key_error
    except Exception as mkv_error:
        raise utils.RipperException(f"Error while running MakeMKV: {mkv_error}") from mkv_error

    # Persist raw_path to DB — this is the actual directory on disk
    utils.database_updater({'raw_path': makemkv_out_path}, job)

    if check_empty_rip(job):
        job.status = JobState.FAILURE.value
        db.session.commit()
        logging.warning("Empty rip detected: %s", job.errors)
        _publish_job_failed(job, phase="rip")
        notify_exit(job)
        return

    _post_rip_handoff(job)
    logging.info("************* Ripping with MakeMKV completed *************")

    # Report errors if any
    notify_exit(job)
    logging.info("************* ARM processing complete *************")


def notify_exit(job):
    """Publish ``job.transcode_complete`` at the end of ARM's local pipeline.

    Channels filter on subscribed_events, so the legacy
    ``NOTIFY_TRANSCODE`` per-job guard is gone — operators choose
    visibility per channel now.

    Errors are intentionally NOT branched on here: when the rip or
    transcode genuinely failed, a ``job.failed`` event was already
    published at the FAILURE-state-set site, and that event carries
    the structured error narrative. Emitting both lets subscribers
    correlate, while keeping this site type-agnostic.
    """
    if job.errors:
        # Log so the historical "processing completed with errors" line
        # survives in the ARM log, even though the channel-facing event
        # is uniform.
        logging.info(
            "Processing completed with errors for job %s: %s",
            job.job_id, job.errors,
        )
    publish_event(JobTranscodeCompleteEvent(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        job_id=job.job_id,
        job_title=job.title or "",
        job_disc_type=_job_disc_type(job),
        job_imdb_id=job.imdb_id,
        transcode_duration_seconds=_rip_duration_seconds(job),
        output_path=str(job.path or ""),
    ))
