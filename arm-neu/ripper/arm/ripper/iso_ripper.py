"""ISO file import rip pipeline.

Mirrors `arm.ripper.folder_ripper` but for `iso:{path}` MakeMKV sources.
The post-Job-creation orchestration is shared via `kick_off_import_rip`
from folder_ripper.
"""
import logging

from arm.ripper.folder_ripper import kick_off_import_rip

log = logging.getLogger(__name__)


def rip_iso(job) -> None:
    """Entry point: ISO Job is already persisted, kick off shared import flow.

    Named to mirror `folder_ripper.rip_folder` for consistency.
    """
    log.info(
        "Starting ISO rip pipeline for job %s (%s)",
        getattr(job, "job_id", "?"),
        getattr(job, "source_path", "?"),
    )
    kick_off_import_rip(job)
