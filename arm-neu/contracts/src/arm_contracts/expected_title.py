"""ExpectedTitle: a metadata-derived expected title attached to a Job.

Producer is arm-neu's `_job_to_dict` (arm/api/v1/jobs.py); arm-ui consumes
via `backend/models/schemas.py`. Frontend mirror lives at
`frontend/src/lib/types/arm.ts:ExpectedTitle`.

Generic across single-feature movies (1 row), TV (N rows per episode),
and anthology / multi-feature discs (N rows per work). `runtime_seconds`
nullable because some metadata responses lack runtime data.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ExpectedTitle(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    source: Literal["omdb", "tmdb", "tvdb", "manual"]
    title: str | None = None
    season: int | None = None
    episode_number: int | None = None
    external_id: str | None = None
    runtime_seconds: int | None = None
