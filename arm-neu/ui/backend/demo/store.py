"""Mutable in-memory dataset for demo mode (per-process; resets on restart)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DemoStore:
    jobs: list[dict] = field(default_factory=list)
    tracks: dict[int, list[dict]] = field(default_factory=dict)  # job_id -> tracks
    job_config: dict = field(default_factory=dict)
    drives: list[dict] = field(default_factory=list)
    notifications: list[dict] = field(default_factory=list)
    channels: list[dict] = field(default_factory=list)
    dispatches: list[dict] = field(default_factory=list)
    transcode_jobs: list[dict] = field(default_factory=list)
    presets: list[dict] = field(default_factory=list)
    config: dict = field(default_factory=dict)
    system_info: dict = field(default_factory=dict)
    system_stats: dict = field(default_factory=dict)
    job_stats: dict = field(default_factory=dict)
    setup_status: dict = field(default_factory=dict)
    ripping_enabled: dict = field(default_factory=dict)
    transcoder_health: dict = field(default_factory=dict)
    transcoder_stats: dict = field(default_factory=dict)
    transcoder_config: dict = field(default_factory=dict)
    handbrake_presets: dict = field(default_factory=dict)
    log_files: list[dict] = field(default_factory=list)
    log_entries: list[dict] = field(default_factory=list)
    file_roots: list[dict] = field(default_factory=list)
    file_tree: dict[str, list[dict]] = field(default_factory=dict)
    movie_search: list[dict] = field(default_factory=list)
    media_detail: dict = field(default_factory=dict)
    music_search: list[dict] = field(default_factory=list)
    music_detail: dict = field(default_factory=dict)

    def job(self, job_id: int) -> dict | None:
        return next((j for j in self.jobs if j["job_id"] == job_id), None)

    def tracks_for(self, job_id: int) -> list[dict]:
        return self.tracks.get(job_id, [])

    def channel(self, channel_id: int) -> dict | None:
        return next((c for c in self.channels if c["id"] == channel_id), None)
