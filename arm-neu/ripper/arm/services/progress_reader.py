"""Read realtime rip progress from MakeMKV PRGV/PRGC/PRGT progress files
and abcde music progress from job logs.

MakeMKV writes real-time PRGV/PRGC messages to a dedicated progress file
at {LOGPATH}/progress/{job_id}.log via the ``--progress=`` flag.  This is
separate from the main job log which only receives this data after the
subprocess completes (stdout is buffered).

Ported from arm-ui's backend/services/progress.py so the BFF can read
this data over HTTP instead of needing the LOGPATH bind mount.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import arm.config.config as cfg


def _safe_log_path(*parts: str) -> Path | None:
    """Resolve a path under LOGPATH, refusing anything that escapes it."""
    root = Path(cfg.arm_config["LOGPATH"]).resolve()
    candidate = (root / Path(*parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _parse_progress_lines(lines: list[str]):
    """Scan MakeMKV progress lines and return (last_prgv, last_prgc, last_prgt)."""
    last_prgv = None
    last_prgc = None
    last_prgt = None
    for line in lines:
        if line.startswith("PRGT:"):
            m = re.match(r'PRGT:\d+,\d+,"([^"]+)"', line)
            if m:
                last_prgt = m.group(1)
        elif line.startswith("PRGV:"):
            m = re.match(r"PRGV:(\d+),(\d+),(\d+)", line)
            if m:
                last_prgv = m
        elif line.startswith("PRGC:"):
            m = re.match(r'PRGC:\d+,(\d+),"([^"]+)"', line)
            if m:
                last_prgc = m
    return last_prgv, last_prgc, last_prgt


def get_rip_progress(job_id: int) -> dict[str, Any]:
    """Parse MakeMKV progress from a job's progress file.

    Returns ``{progress: float|None, stage: str|None, tracks_ripped: int|None}``.
    """
    result: dict[str, Any] = {"progress": None, "stage": None, "tracks_ripped": None}

    path = _safe_log_path("progress", f"{job_id}.log")
    if path is None or not path.is_file():
        return result

    try:
        with open(path, "rb") as f:
            data = f.read().decode("utf-8", errors="replace")
    except OSError:
        return result

    last_prgv, last_prgc, last_prgt = _parse_progress_lines(data.splitlines())

    # PRGC tracks per-title state; PRGT tracks overall operation. Between
    # titles in a folder rip MakeMKV briefly emits non-"Saving" PRGT messages
    # (e.g. "Analyzing seamless segments") while PRGC stays on "Saving to MKV
    # file" - prefer PRGC so the percentage doesn't flicker to indeterminate.
    is_rip_phase = (
        (last_prgc and last_prgc.group(2) == "Saving to MKV file")
        or (last_prgt and "Saving" in last_prgt)
    )

    if last_prgv:
        total = int(last_prgv.group(2))
        maximum = int(last_prgv.group(3))
        if maximum > 0:
            if is_rip_phase:
                result["progress"] = round(total / maximum * 100, 1)
            else:
                result["stage"] = last_prgt

    if last_prgc:
        index = int(last_prgc.group(1))
        name = last_prgc.group(2)
        result["stage"] = f"Title {index + 1}: {name}"
        # During the "Saving to MKV file" phase, titles before the current
        # index are complete. Used as a real-time ripped count so the UI
        # can show progress before FILE_ADDED marks them in the DB.
        if name == "Saving to MKV file":
            result["tracks_ripped"] = index

    return result


def get_music_progress(logfile: str | None, total_tracks: int) -> dict[str, Any]:
    """Parse abcde progress from the job's main log file.

    Returns ``{progress: float|None, stage: str|None, tracks_ripped: int|None,
    tracks_total: int|None}``.
    """
    result: dict[str, Any] = {
        "progress": None,
        "stage": None,
        "tracks_ripped": None,
        "tracks_total": None,
    }

    if not logfile:
        return result

    path = _safe_log_path(logfile)
    if path is None or not path.is_file():
        return result

    try:
        with open(path, "r", errors="replace") as f:
            content = f.read()
    except OSError:
        return result

    grabbing = {int(m.group(1)) for m in re.finditer(r"Grabbing track (\d+):", content)}
    encoding = {int(m.group(1)) for m in re.finditer(r"Encoding track (\d+) of", content)}
    tagging = {int(m.group(1)) for m in re.finditer(r"Tagging track (\d+) of", content)}

    all_seen = grabbing | encoding | tagging
    if not all_seen:
        return result

    total = total_tracks or len(all_seen)
    # Encoding completes before tagging starts; using its count avoids the
    # 1-track overcount you get from "Tagging track N" being logged at the
    # START of tagging.
    completed = len(encoding)
    current_track = max(all_seen)

    if tagging:
        phase = "tagging"
    elif encoding:
        phase = "encoding"
    else:
        phase = "ripping"

    result["stage"] = f"{completed}/{total} - {phase} track {current_track}"
    result["tracks_ripped"] = completed
    result["tracks_total"] = total
    if total > 0:
        result["progress"] = round(completed / total * 100, 1)

    return result


def get_copy_progress(
    job_id: int,
    stage: str | None = None,
) -> dict[str, Any]:
    """Tail-read the copy-progress side-file for a job.

    Side-file format (one line per event):
        stage,progress_pct,files_transferred,current_file

    Args:
        job_id: Numeric job identifier.
        stage: If provided, return the latest entry for that stage only.
               If None, return the latest entry across all stages.

    Returns:
        ``{progress: float|None, stage: str|None, files_transferred: int|None,
        current_file: str|None}``. Returns the no-data shape when the file
        does not exist or contains no valid entries.

    Fail-soft: garbage lines are skipped without raising. Symmetric to
    get_rip_progress and get_music_progress in this module.
    """
    result: dict[str, Any] = {
        "progress": None, "stage": None,
        "files_transferred": None, "current_file": None,
    }
    path = _safe_log_path("progress", f"{job_id}.copy.log")
    if path is None or not path.is_file():
        return result
    try:
        with open(path, "r", errors="replace") as f:
            content = f.read()
    except OSError:
        return result

    latest: dict[str, Any] | None = None
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(",", 3)
        if len(parts) != 4:
            continue
        line_stage, pct_str, files_str, current_file = parts
        if stage is not None and line_stage != stage:
            continue
        try:
            pct = float(pct_str)
        except ValueError:
            continue
        try:
            files = int(files_str) if files_str else None
        except ValueError:
            files = None
        latest = {
            "progress": pct,
            "stage": line_stage,
            "files_transferred": files,
            "current_file": current_file or None,
        }
    return latest if latest is not None else result
