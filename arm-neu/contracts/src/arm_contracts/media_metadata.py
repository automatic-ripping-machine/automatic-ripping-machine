"""MediaMetadata contract: editorial metadata for a Job, fetched from
OMDb / TMDb / TVDB / MusicBrainz.

Producer side: arm-neu's metadata service has one adapter per provider.
Each adapter normalizes provider-specific shapes (OMDb's '120 min'
runtime string, TMDb's nested release_dates certifications, etc.)
into the canonical types declared here. The pydantic validator rejects
un-normalized values so producer bugs surface at adapter time, not at
consumer time.

Consumer side: arm-neu's naming engine reads tokens from this; the API
serializer ships it on Job responses; arm-ui's pattern editor reads
PATTERN_TOKENS for autocomplete. The transcoder webhook does NOT
include this - the transcoder transcodes by output_path + title_name
which arm-neu pre-renders.

Storage: arm-neu stores two columns on Job:
  - media_metadata_auto:    JSON of MediaMetadata, written by adapters
  - media_metadata_manual:  JSON of partial MediaMetadata, UI overrides
A read property merges manual-over-auto field-by-field.

Forward compatibility: adding a new field is a single change here +
optional PATTERN_TOKENS entry. Auto-bump bot lands the new contracts
SHA in all consumers; no consumer migrations.
"""
from __future__ import annotations

from datetime import date
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field

from arm_contracts.enums import VideoType


class MediaMetadata(BaseModel):
    """Editorial metadata for a Job. Every field optional - providers
    populate different subsets, manual overrides may set any subset.
    """

    model_config = ConfigDict(extra="ignore")

    # Identity
    title: str | None = Field(None, max_length=500)
    year: str | None = Field(None, max_length=4, pattern=r"^\d{4}$|^$")
    video_type: VideoType | None = None
    imdb_id: str | None = Field(None, max_length=15, pattern=r"^tt\d+$|^$")
    tvdb_id: int | None = None

    # Visual
    poster_url: str | None = Field(None, max_length=1000)

    # Editorial
    plot: str | None = Field(None, max_length=4000)
    tagline: str | None = Field(None, max_length=500)
    runtime_seconds: int | None = Field(None, ge=0)

    # Lists (CSV-parsed at adapter time, stored as list[str])
    genres: list[str] = Field(default_factory=list)
    directors: list[str] = Field(default_factory=list)
    writers: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)

    # Categorical
    mpaa_rating: str | None = Field(None, max_length=20)
    released_date: date | None = None
    language: str | None = Field(None, max_length=10)
    country: str | None = Field(None, max_length=100)
    production_company: str | None = Field(None, max_length=200)
    network: str | None = Field(None, max_length=200)
    imdb_rating: float | None = Field(None, ge=0.0, le=10.0)

    # Series
    season: str | None = Field(None, max_length=10)

    # Audio
    artist: str | None = Field(None, max_length=500)
    album: str | None = Field(None, max_length=500)
    album_artist: str | None = Field(None, max_length=500)


# ----------------------------------------------------------------------
# Pattern-token derivation
# ----------------------------------------------------------------------

# PATTERN_TOKENS is the single source of truth for the naming engine's
# token vocabulary AND the UI pattern-editor's autocomplete list.
#
# Each entry maps a {token} alias to:
#   - field_name: which MediaMetadata attribute to read
#   - description: shown in the UI dropdown
#   - accessor: callable applied to the field value to render a string
#               (handles list-to-primary, runtime-seconds-to-minutes,
#               date-to-isoformat, enum-to-value)
#
# Aliases that don't map to MediaMetadata fields (label, disc_number,
# disc_total) live in the engine, not here - those are physical-disc
# properties, not editorial metadata.

_FIRST_OR_EMPTY: Callable[[list[str]], str] = lambda lst: lst[0] if lst else ""

PATTERN_TOKENS: dict[str, tuple[str, str, Callable[[object], str]]] = {
    "title":         ("title",         "Movie/series/album title",      lambda v: str(v)),
    "show":          ("title",         "Show name (alias for {title})", lambda v: str(v)),
    "year":          ("year",          "Release year (4 digits)",       lambda v: str(v)),
    "video_type":    ("video_type",    "movie, series, or music",       lambda v: v.value),
    "imdb_id":       ("imdb_id",       "IMDb ID (e.g. tt0111161)",      lambda v: str(v)),
    "runtime_minutes": ("runtime_seconds", "Runtime in minutes",
                                       lambda v: str(v // 60)),
    "genre":         ("genres",        "Primary genre",                 _FIRST_OR_EMPTY),
    "director":      ("directors",     "Primary director",              _FIRST_OR_EMPTY),
    "writer":        ("writers",       "Primary writer",                _FIRST_OR_EMPTY),
    "rating":        ("mpaa_rating",   "MPAA / content rating",         lambda v: str(v)),
    "released":      ("released_date", "Release date (ISO YYYY-MM-DD)", lambda v: v.isoformat()),
    "language":      ("language",      "Primary language code",         lambda v: str(v)),
    "network":       ("network",       "TV network",                    lambda v: str(v)),
    "season":        ("season",        "Season number (zero-padded)",   lambda v: str(v).zfill(2)),
    "artist":        ("artist",        "Music artist",                  lambda v: str(v)),
    "album":         ("album",         "Music album",                   lambda v: str(v)),
    "album_artist":  ("album_artist",  "Album artist (compilations)",   lambda v: str(v)),
}
