"""Shared helpers for /api/v1 import endpoints (folder + ISO).

Both create-job endpoints share identical request shapes (title, year,
video_type, imdb_id, poster_url, multi_title, season, disc_number,
disc_total) and identical ORM-population logic. This module centralises
that logic so the endpoint bodies stay focused on their own pre/post
validation steps.
"""
from typing import Any


def apply_request_metadata_to_job(job: Any, req: Any) -> None:
    """Populate optional metadata fields on a Job from a create-request.

    Required fields (title, video_type, multi_title) are always set.
    Optional fields (year, imdb_id, poster_url, season, disc_number,
    disc_total) are only assigned when present, matching the historic
    behaviour of the inline blocks in folder.py and iso.py.

    Args:
        job: SQLAlchemy Job model instance (mutated in place).
        req: Pydantic create-job request (FolderCreateRequest or
             IsoCreateRequest); must expose the canonical attribute set.
    """
    job.title = req.title
    job.title_auto = req.title
    if req.year:
        job.year = req.year
        job.year_auto = req.year
    job.video_type = req.video_type
    if req.imdb_id:
        job.imdb_id = req.imdb_id
    if req.poster_url:
        from arm_contracts import MediaMetadata
        job.set_metadata_auto(MediaMetadata(poster_url=req.poster_url))
    job.multi_title = req.multi_title
    if req.season is not None:
        job.season = str(req.season)
        job.season_manual = str(req.season)
    if req.disc_number is not None:
        job.disc_number = req.disc_number
    if req.disc_total is not None:
        job.disc_total = req.disc_total
