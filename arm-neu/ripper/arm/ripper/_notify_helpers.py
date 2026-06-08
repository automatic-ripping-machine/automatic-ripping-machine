"""Shared helpers for the notifications producer sites in the ripper.

These were originally private to ``arm_ripper`` (added in N17) but the
manual-wait and duplicate-disc paths (N18) need the same Disctype
mapping from ``makemkv.py`` and ``utils.py``. Extracting once here
avoids three near-identical copies.

This module is intentionally tiny — anything more interesting belongs
in ``arm.notifications`` rather than the ripper package.
"""
from datetime import datetime, timezone

from arm_contracts.enums import Disctype


def rip_duration_seconds(job) -> int:
    """Wall-clock seconds from ``job.start_time`` to now.

    ``job.start_time`` is a naive ``datetime`` in the DB; we treat it
    as UTC for the subtraction. Returns 0 if ``start_time`` is missing
    (defensive — the rip pipeline always sets it on entry).
    """
    if not job.start_time:
        return 0
    start = job.start_time.replace(tzinfo=timezone.utc)
    return int((datetime.now(timezone.utc) - start).total_seconds())


def job_disc_type(job) -> Disctype:
    """Map the ripper's string ``job.disctype`` column onto the contracts enum.

    A missing / empty / unrecognised value collapses to
    ``Disctype.unknown`` so the publish never blows up on an
    event-level required field; the upstream guard in
    ``notify_entry`` already rejects unknown discs before they reach
    the happy path.
    """
    if not job.disctype:
        return Disctype.unknown
    try:
        return Disctype(job.disctype)
    except ValueError:
        return Disctype.unknown
