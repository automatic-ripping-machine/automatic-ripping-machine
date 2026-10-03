"""
Devtools service - read-only media probing via ffprobe.

Ported from the v2 media_probe_service. v2 built its digests on
arm.ripper.source_facts so they compared directly against persisted source
facts; v3 has no source_facts module, so the digest here is built straight
from ffprobe's JSON output. Read-only: never touches the database, config,
resolver state, or files.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from typing import Any

_PROBE_TIMEOUT_SECONDS = 60
_MEDIA_EXTENSIONS = {".mkv", ".mp4", ".m4v", ".avi", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wav"}


def _run_ffprobe(source_path: str) -> dict[str, Any] | None:
    """Run ffprobe as JSON and return the raw dict, or None on failure."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        logging.warning("media-probe skipped for %s: ffprobe not on PATH", source_path)
        return None
    command = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        "-show_chapters",
        source_path,
    ]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=_PROBE_TIMEOUT_SECONDS,
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        logging.warning("media-probe failed for %s: %s", source_path, type(error).__name__)
        return None
    if completed.returncode != 0:
        logging.warning("media-probe failed for %s: %s", source_path, completed.stderr.strip()[:200])
        return None
    try:
        parsed = json.loads(completed.stdout)
    except ValueError:
        logging.warning("media-probe returned invalid JSON for %s", source_path)
        return None
    return parsed if isinstance(parsed, dict) else None


def _stream_digest(stream: dict[str, Any]) -> dict[str, Any]:
    """Reduce one raw ffprobe stream entry to the fields an agent cares about."""
    disposition = {key: True for key, value in (stream.get("disposition") or {}).items() if value}
    return {
        "index": stream.get("index"),
        "codec_type": stream.get("codec_type"),
        "codec_name": stream.get("codec_name"),
        "profile": stream.get("profile"),
        "width": stream.get("width"),
        "height": stream.get("height"),
        "avg_frame_rate": stream.get("avg_frame_rate"),
        "r_frame_rate": stream.get("r_frame_rate"),
        "duration": stream.get("duration"),
        "channels": stream.get("channels"),
        "channel_layout": stream.get("channel_layout"),
        "language": (stream.get("tags") or {}).get("language"),
        "title": (stream.get("tags") or {}).get("title"),
        "disposition": disposition,
    }


def _probe_file(source_path: str) -> dict[str, Any]:
    raw = _run_ffprobe(source_path)
    if raw is None:
        return {"file": source_path, "error": "probe_failed"}
    format_info = raw.get("format") or {}
    streams = [s for s in (raw.get("streams") or []) if isinstance(s, dict)]
    chapters = [c for c in (raw.get("chapters") or []) if isinstance(c, dict)]
    return {
        "file": source_path,
        "format": {
            "format_name": format_info.get("format_name"),
            "format_long_name": format_info.get("format_long_name"),
            "duration": format_info.get("duration"),
            "size": format_info.get("size"),
            "bit_rate": format_info.get("bit_rate"),
        },
        "video": [_stream_digest(s) for s in streams if s.get("codec_type") == "video"],
        "audio": [_stream_digest(s) for s in streams if s.get("codec_type") == "audio"],
        "subtitle": [_stream_digest(s) for s in streams if s.get("codec_type") == "subtitle"],
        "chapters": [
            {
                "start": chapter.get("start_time"),
                "end": chapter.get("end_time"),
                "title": (chapter.get("tags") or {}).get("title"),
            }
            for chapter in chapters
        ],
    }


def probe_media_file(*, job_id: int | None = None, path: str | None = None) -> dict[str, Any]:
    """
    ffprobe digests for a job's completed output files, or one explicit path.

    Args:
        job_id: probe every media file under the job's final destination
        path: probe exactly this file

    Returns:
        dict: files with per-file digests; error entries when probing fails
    """
    if path:
        return {"files": [_probe_file(path)]}
    if job_id is None:
        raise ValueError("job_id or path required")

    from ui.devtools.services.completion_service import list_job_outputs

    outputs = list_job_outputs(job_id)
    files = [
        file
        for directory in outputs["directories"]
        for file in directory["files"]
        if os.path.splitext(file)[1].lower() in _MEDIA_EXTENSIONS
    ]
    return {"job_id": job_id, "final_path": outputs["final_path"], "files": [_probe_file(file) for file in files]}
