"""Metadata search/detail response and update-request shapes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SearchResultSchema(BaseModel):
    title: str
    year: str
    imdb_id: str | None = None
    media_type: str
    poster_url: str | None = None


class MediaDetailSchema(SearchResultSchema):
    """Full detail for a single title (distinct from JobDetailSchema)."""
    plot: str | None = None
    background_url: str | None = None


class MusicSearchResultSchema(BaseModel):
    title: str
    artist: str
    year: str
    release_id: str
    media_type: str = "music"
    poster_url: str | None = None
    track_count: int | None = None
    country: str | None = None
    release_type: str | None = None
    format: str | None = None
    label: str | None = None


class MusicTrackSchema(BaseModel):
    """A single track in a MusicBrainz release.

    Field names mirror what arm-neu emits (proxied from MusicBrainz):
    `number` and `title` are required; `length_ms` and `disc_number`
    are optional.
    """
    number: str
    title: str
    length_ms: int | None = None
    disc_number: int | None = None


class MusicDetailSchema(MusicSearchResultSchema):
    catalog_number: str | None = None
    barcode: str | None = None
    status: str | None = None
    disc_count: int | None = None
    tracks: list[MusicTrackSchema]


class MusicSearchResponse(BaseModel):
    """`GET /metadata/music/search` upstream envelope."""
    results: list[MusicSearchResultSchema]
    total: int = 0
    offset: int = 0


class SearchResponse(BaseModel):
    """`GET /metadata/search` upstream envelope."""
    results: list[SearchResultSchema]
    total: int = 0


class TitleUpdateRequest(BaseModel):
    title: str | None = None
    year: str | None = None
    video_type: str | None = None
    imdb_id: str | None = None
    poster_url: str | None = None
    path: str | None = None
    disctype: str | None = None
    label: str | None = None
    artist: str | None = None
    album: str | None = None
    season: str | None = None
    episode: str | None = None


class TrackTitleUpdateRequest(BaseModel):
    """Per-track title override for multi-title discs.

    Upstream arm-neu accepts the full title-detail set (title + year +
    video_type + imdb_id + poster_url) so the frontend can apply a
    metadata search result directly to a single track.
    """
    title: str | None = None
    year: str | None = None
    video_type: str | None = None
    imdb_id: str | None = None
    poster_url: str | None = None


class JobConfigUpdateRequest(BaseModel):
    RIPMETHOD: str | None = None
    DISCTYPE: str | None = None
    MAINFEATURE: bool | None = None
    MINLENGTH: int | None = None
    MAXLENGTH: int | None = None
    AUDIO_FORMAT: str | None = None
    SKIP_TRANSCODE: bool | None = None


class NamingPreviewRequest(BaseModel):
    pattern: str
    variables: dict[str, str] = {}


class NamingPreviewResponse(BaseModel):
    rendered: str
