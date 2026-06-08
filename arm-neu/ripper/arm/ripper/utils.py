#!/usr/bin/env python3
"""Collection of utility functions"""
import datetime
import json
import os
import logging
import subprocess
import shutil
import time
import random
import re
import unicodedata
from logging import Logger
from pathlib import Path, PurePath
from math import ceil

import bcrypt


def extract_year(raw: str) -> str:
    """Extract a 4-digit year from strings like '2006-05-19', '2006–2008', '2006–'.

    Returns the first 4-digit sequence found, or the original string if none.
    """
    m = re.search(r"\d{4}", str(raw))
    return m.group(0) if m else raw
import httpx
import requests
import psutil

from netifaces import interfaces, ifaddresses, AF_INET

from arm.enums import SpeedProfile
from arm_contracts.enums import TrackStatus, WebhookEventType

import arm.config.config as cfg
from arm.ripper.ProcessHandler import arm_subprocess
from arm.database import db  # needs to be imported before models
from arm.models.job import Job, JobState
from arm.models.notifications import Notifications
from arm.models.track import Track
from arm.models.user import User
from arm.models.app_state import AppState
from arm.models.system_drives import SystemDrives

NOTIFY_TITLE = "ARM notification"


class RipperException(Exception):
    pass


def _move_to_shared_storage(cfg, raw_basename, job=None):
    """Move raw directory from local scratch to shared storage if configured.

    Delegates to run_rsync_with_side_file so progress is streamed to the
    {LOGPATH}/progress/{job_id}.copy.log file consumed by progress_reader.
    """
    local_raw = cfg.get('LOCAL_RAW_PATH', '')
    shared_raw = cfg.get('SHARED_RAW_PATH', '')
    if not (local_raw and shared_raw and raw_basename):
        return
    src = os.path.join(local_raw, raw_basename)
    dst = os.path.join(shared_raw, raw_basename)
    if not os.path.isdir(src):
        return

    if job:
        database_updater({'status': JobState.COPYING.value}, job)
    os.makedirs(dst, exist_ok=True)

    from arm.ripper.rsync_helper import run_rsync_with_side_file, _redact_rsync
    try:
        run_rsync_with_side_file(
            src, dst,
            job_id=getattr(job, 'job_id', 0),
            stage="scratch-to-media",
            remove_source=True,
        )
    except OSError as e:
        logging.error(f"Failed to move {_redact_rsync(src)} -> {_redact_rsync(dst)}: {e}")
        raise


def _build_webhook_payload(title, body, job, raw_basename):
    """Build the JSON payload for the transcoder webhook.

    Returns a plain dict (the JSON body) but constructs it via the typed
    arm_contracts.WebhookPayload model so any field-shape drift surfaces
    here instead of as a 422 from the transcoder. The transcoder's
    contracts model accepts the same wire shape verbatim.

    Includes pre-rendered naming from ARM's naming engine so the transcoder
    doesn't need its own naming logic - ARM is the single source of truth
    for folder/file naming patterns configured in arm.yaml.
    """
    from arm_contracts import WebhookPayload, WebhookTrackMeta
    from arm.ripper.naming import (
        clean_for_filename, render_all_tracks, render_folder, render_title,
    )

    if job is None:
        # Notification-only path (no job context). Title/body/type only.
        # WebhookPayload requires job_id, so we hand-build the dict here -
        # the typed model is only meaningful for the job-bound transcode
        # webhook the transcoder actually receives.
        return {"title": title, "body": body, "type": WebhookEventType.info.value}

    config_dict = cfg.arm_config if hasattr(cfg, 'arm_config') else None
    # Route through _parse_transcode_overrides so corrupt/legacy rows are
    # dropped with a WARN rather than shipped to the transcoder, which
    # would 422 the webhook (see automatic-ripping-machine-transcoder
    # PR #96 for the webhook parse-boundary check).
    from arm.api.v1.jobs import _parse_transcode_overrides
    overrides_dict = _parse_transcode_overrides(job.transcode_overrides)

    # Resolve the raw share root. SHARED_RAW_PATH wins when local+shared
    # scratch staging is configured; otherwise fall back to RAW_PATH.
    raw_root = (config_dict or {}).get('SHARED_RAW_PATH') or (config_dict or {}).get('RAW_PATH') or ''

    # input_path: job.raw_path relative to the raw share root. Falls
    # back to raw_basename when raw_path / raw_root aren't set, which
    # keeps notification-only style payloads (no real job dir) working.
    input_path = None
    if job.raw_path and raw_root:
        try:
            rel = os.path.relpath(str(job.raw_path), str(raw_root))
            # relpath returns a string starting with '..' when raw_path is
            # outside raw_root; that fails the contract validator. Treat
            # as missing input rather than raising.
            if not rel.startswith('..'):
                input_path = rel
        except ValueError:
            input_path = None
    if input_path is None and raw_basename:
        # No raw_root or relpath escaped: ship the basename as a
        # last-resort relative path. Rare; transcoder will fail
        # _wait_for_stable if the dir doesn't exist under raw_path.
        input_path = raw_basename

    # output_path: job.type_subfolder joined with rendered folder name.
    # render_folder returns the leaf with sanitized segments and may
    # contain '/' for nested dirs ('Title/Season 01').
    type_sub = job.type_subfolder if hasattr(job, 'type_subfolder') else 'unidentified'
    rendered_folder = render_folder(job, config_dict)
    output_path = os.path.join(type_sub, rendered_folder) if rendered_folder else type_sub

    # Pre-rendered per-track names from ARM's naming engine.
    rendered = render_all_tracks(job, config_dict)
    rendered_map = {r["track_number"]: r for r in rendered}
    # Honor user/MAINFEATURE-disabled tracks: a track explicitly disabled
    # (enabled is False) is never transcoded. enabled is None (legacy NULL)
    # or True is included — mirrors _track_to_dict's NULL fold in
    # arm/api/v1/jobs.py. If every track is disabled, fall back to all
    # tracks rather than ship an empty/absent manifest that strands the job.
    candidate_tracks = [t for t in job.tracks if t.enabled is not False]
    if not candidate_tracks:
        logging.warning(
            "Job %s: all tracks disabled — sending full track list to transcoder",
            job.job_id,
        )
        candidate_tracks = list(job.tracks)
    tracks_meta = []
    for track in candidate_tracks:
        r = rendered_map.get(str(track.track_number or ''), {})
        # Prefer episode_name for series tracks - track.title can be stale
        # if the user corrected episodes via the UI after auto-match.
        title_str = (
            getattr(track, 'episode_name', '') or track.title or job.title or ''
        )
        # clean_for_filename is idempotent; render_track_title already
        # sanitizes custom_filename but raw pattern output needs it here.
        rendered_title = r.get("rendered_title", '')
        track_title_name = clean_for_filename(rendered_title) if rendered_title else ''

        # Per-track output_path: pick the type subdir from THIS track's
        # video_type (multi-title discs can mix movie + series tracks),
        # then join with the track's rendered folder. Shares the
        # job-level resolver so unclassified tracks land in
        # UNIDENTIFIED_SUBDIR for operator triage.
        from arm.models.job import resolve_type_subfolder
        track_video_type = str(track.video_type or job.video_type or '')
        track_type_sub = resolve_type_subfolder(track_video_type, job.disctype)
        track_rendered_folder = r.get("rendered_folder", '')
        track_output_path = (
            os.path.join(track_type_sub, track_rendered_folder)
            if track_rendered_folder else track_type_sub
        )

        tracks_meta.append(WebhookTrackMeta(
            track_number=str(track.track_number or ''),
            title=str(title_str),
            year=str(track.year or job.year or ''),
            video_type=track_video_type,
            filename=str(track.filename or ''),
            has_custom_title=bool(track.title) or bool(getattr(track, 'custom_filename', None)),
            output_path=track_output_path,
            title_name=track_title_name,
            episode_number=str(getattr(track, 'episode_number', '') or ''),
            episode_name=str(getattr(track, 'episode_name', '') or ''),
        ))

    payload = WebhookPayload(
        title=title,
        body=body,
        type=WebhookEventType.info,
        input_path=input_path,
        output_path=output_path,
        job_id=str(job.job_id),  # WebhookPayload coerces str -> int.
        video_type=str(job.video_type or ''),
        year=str(job.year or ''),
        disctype=str(job.disctype or ''),
        status=str(job.status or ''),
        poster_url=str(job.media_metadata.poster_url or ''),
        title_name=clean_for_filename(render_title(job, config_dict)),
        config_overrides=overrides_dict,  # Pydantic coerces dict -> TranscodeJobConfig.
        multi_title=True if getattr(job, 'multi_title', False) else None,
        tracks=tracks_meta if tracks_meta else None,
    )
    return payload.model_dump(exclude_none=True, mode="json")


def transcoder_notify(cfg, title, body, job=None) -> bool:
    """Send a webhook notification to the arm-transcoder service.

    If LOCAL_RAW_PATH and SHARED_RAW_PATH are both set, moves the job's
    raw directory from local to shared storage before notifying.

    Returns:
        bool: True if the webhook was delivered with an HTTP 2xx response.
            False on any failure: missing job, missing TRANSCODER_URL,
            auth failure (401/403), any non-2xx status, or transport
            exception. Specific failure causes are logged internally so
            operators can diagnose from the ripper logs; the boolean
            lets callers branch on outcome without re-catching exceptions.
    """
    if job is None or getattr(job, 'job_id', None) is None:
        return False

    transcoder_url = cfg.get('TRANSCODER_URL', '')
    if not transcoder_url:
        return False

    raw_basename = os.path.basename(str(job.raw_path)) if job.raw_path else ''
    _move_to_shared_storage(cfg, raw_basename, job)

    # Update job.raw_path to shared location after move
    shared_raw = cfg.get('SHARED_RAW_PATH', '')
    if shared_raw and raw_basename:
        new_raw_path = os.path.join(shared_raw, raw_basename)
        if os.path.isdir(new_raw_path):
            job.raw_path = new_raw_path
            db.session.commit()

    payload = _build_webhook_payload(title, body, job, raw_basename)
    # X-Api-Version pins the webhook contract. Transcoders on v2 accept this
    # header (and still accept unversioned requests for back-compat). Older
    # transcoders that only speak v1 must reject v2 explicitly so payload
    # shape mismatches fail loudly instead of silently dropping fields.
    headers = {
        "Content-Type": "application/json",
        "X-Api-Version": "2",
    }
    secret = cfg.get('TRANSCODER_WEBHOOK_SECRET', '')
    if secret:
        headers["X-Webhook-Secret"] = secret

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(transcoder_url, json=payload, headers=headers)
        if resp.status_code in (401, 403):
            logging.error(
                f"Transcoder webhook auth failed (HTTP {resp.status_code}). "
                "Check TRANSCODER_WEBHOOK_SECRET matches WEBHOOK_SECRET on the transcoder."
            )
            return False
        if 200 <= resp.status_code < 300:
            logging.info(f"Transcoder webhook sent (HTTP {resp.status_code})")
            return True
        logging.error(
            f"Transcoder webhook failed (HTTP {resp.status_code})"
        )
        return False
    except Exception as e:
        logging.error(f"Failed sending transcoder webhook: {e}")
        return False


def notify_entry(job):
    """
    Notify On Entry\n
    :param job:
    :return: None
    """
    from datetime import datetime as _dt, timezone
    from uuid import uuid4
    from arm_contracts import JobStartedEvent
    from arm_contracts.enums import Disctype
    from arm.notifications import publish_event

    # Always write a history row so the UI's notification pane reflects
    # the new job, independent of any channel dispatch.
    notification = Notifications(f"New Job: {job.job_id} has started. Disctype: {job.disctype}",
                                 f"New job has started to rip - {job.label},"
                                 f"{job.disctype} at {datetime.datetime.now()}")
    database_adder(notification)

    # Preserve historical behaviour: an unrecognised disctype is a hard
    # stop. The closed set is dvd/bluray/bluray4k/music/data; anything
    # else (including 'unknown') is treated as a ripper failure.
    if job.disctype not in ("dvd", "bluray", "bluray4k", "music", "data"):
        raise RipperException("Could not determine disc type")

    publish_event(JobStartedEvent(
        event_id=uuid4(),
        occurred_at=_dt.now(timezone.utc),
        job_id=job.job_id,
        job_title=job.title or "",
        job_disc_type=Disctype(job.disctype),
        job_imdb_id=job.imdb_id,
        drive_mount=getattr(job, "devpath", None),
    ))


def sleep_check_process(process_str, max_processes, sleep=(20, 120, 10)):
    """
    New function to check for max_transcode from job.config and force obey limits\n
    :param str process_str: The process string from arm.yaml
    :param int max_processes: The user defined limit for maximum transcodes
    :param (tuple, int) sleep: tuple: (min sleep time, max sleep time, step) or sleep time as int.
    :return bool: when we have space in the transcode queue
    """
    if max_processes <= 0:
        return False  # sleep limit disabled
    if isinstance(sleep, int):
        sleep = (sleep, sleep + 1, 1)
    if not isinstance(sleep, tuple):
        raise TypeError(sleep)
    loop_count = max_processes + 1
    logging.info(f"Starting sleep check of {process_str}")
    while loop_count >= max_processes:
        # The process might disappear during loops, so we need to query the
        # name upfront.
        loop_count = sum(
            1 for proc in psutil.process_iter(['name'])
            if proc.info.get('name') == process_str
        )
        if max_processes > loop_count:
            break
        # Try to make each check at different times
        random_time = random.randrange(*sleep)
        logging.debug(f"{loop_count} processes running. Sleeping for {random_time}s.")
        time.sleep(random_time)
    logging.info(f"Exiting sleep check of {process_str}")
    return True


def scan_emby():
    """Trigger a media scan on Emby"""

    if cfg.arm_config["EMBY_REFRESH"]:
        logging.info("Sending Emby library scan request")
        url = f"http://{cfg.arm_config['EMBY_SERVER']}:{cfg.arm_config['EMBY_PORT']}/Library/Refresh?api_key={cfg.arm_config['EMBY_API_KEY']}"  # noqa: E501
        try:
            req = requests.post(url)
            if req.status_code > 299:
                req.raise_for_status()
            logging.info("Emby Library Scan request successful")
        except requests.exceptions.HTTPError:
            logging.error(f"Emby Library Scan request failed with status code: {req.status_code}")
    else:
        logging.info("EMBY_REFRESH config parameter is false.  Skipping emby scan.")


def delete_raw_files(dir_list):
    """
    Delete the raw folders from arm after job has finished
    :param list dir_list: Python list containing strings of the folders to be deleted

    """
    if cfg.arm_config["DELRAWFILES"]:
        for raw_folder in dir_list:
            try:
                logging.info(f"Removing raw path - {raw_folder}")
                shutil.rmtree(raw_folder)
            except UnboundLocalError as error:
                logging.debug(f"No raw files found to delete in {raw_folder}- {error}")
            except OSError as error:
                logging.debug(f"No raw files found to delete in {raw_folder} - {error}")
            except TypeError as error:
                logging.debug(f"No raw files found to delete in {raw_folder} - {error}")


def make_dir(path: str, exist_ok: bool = True) -> bool:
    """
    Make a directory\n
    :param path: Path to directory
    :param exist_ok: If ``True``, simply returns ``False`` in case the
        directory exists. If ``False``, raises a ``RipperException`` in that case.
    :return: ``True`` if the directory was created, ``False`` if it already existed
    :raises: ``RipperException``
    """
    try:
        os.makedirs(path)
        logging.debug(f"Created directory: {path}")
        return True
    except FileExistsError as err:
        if exist_ok:
            return False
        else:
            raise RipperException(f"Folder exists: {path}") from err
    except OSError as err:
        raise RipperException(f"Could not create folder: {path}") from err


def find_file(filename, search_path):
    """
    Check to see if file exists by searching a directory recursively\n
    :param filename: filename to look for
    :param search_path: path to search recursively
    :return bool:
    """
    for dirpath, dirnames, filenames in os.walk(search_path):
        if filename in filenames:
            return True
    return False


def _update_music_tracks(job, ripped, status):
    """Bulk-update ripped/status on all tracks for a music job.

    `status` must be a member-value of TrackStatus (validated at the DB
    layer via db.Enum).
    """
    try:
        Track.query.filter_by(job_id=job.job_id).update(
            {"ripped": ripped, "status": status}
        )
        db.session.commit()
    except Exception as exc:
        logging.debug("Could not update music tracks: %s", exc)
        db.session.rollback()


# ── abcde / cdparanoia output classification ────────────────────────────────

# Patterns that indicate errors (rip/encode/move failures, device errors)
_ABCDE_ERROR_PATTERNS = [
    re.compile(r'^\[ERROR\]'),                          # abcde log error prefix
    re.compile(r'The following commands failed to run'), # end-of-run error summary
    re.compile(r'returned code \d+:'),                   # individual command failure
    re.compile(r'Permission denied'),                    # filesystem permission
    re.compile(r'CDROM drive unavailable'),               # drive gone
    re.compile(r'CDROM has not been defined'),            # no device configured
    re.compile(r'CD could not be read'),                  # cd-discid failure
    re.compile(r'Unable to open disc'),                   # cdparanoia can't open
    re.compile(r'Unable to open cdrom'),                  # cdparanoia variant
    re.compile(r'Unable to read any data'),               # cdparanoia total failure
    re.compile(r'CDROMREADTOCHDR:'),                      # cd-discid ioctl error
    re.compile(r'Input/output error'),                    # generic I/O error
    re.compile(r'No medium found'),                       # no disc in drive
    re.compile(r'HEH! The file .* disappeared'),          # file vanished mid-pipeline
    re.compile(r'Segmentation fault'),                    # process crash
    re.compile(r'^\d{3}: '),                              # cdparanoia numbered error (001-405)
]

# Patterns that indicate warnings (non-fatal issues, degraded rip quality)
_ABCDE_WARNING_PATTERNS = [
    re.compile(r'^\[WARNING\]'),                          # abcde log warning prefix
    re.compile(r'Not cleaning up'),                       # errors prevented cleanup
    re.compile(r'something went wrong while querying'),   # CDDB/MusicBrainz partial failure
    re.compile(r'still considered experimental'),          # CUE sheet warning
    re.compile(r'problem with the CD reading'),            # partial read failure
]

# Patterns that are debug-level (noisy progress, not useful in production logs)
_ABCDE_DEBUG_PATTERNS = [
    re.compile(r'^cdparanoia III'),                       # cdparanoia version banner
    re.compile(r'^Ripping from sector'),                  # cdparanoia sector range
    re.compile(r'^\s+to sector'),                         # cdparanoia sector range cont.
    re.compile(r'^outputting to'),                        # cdparanoia output path
    re.compile(r'^[.+!\-eV :;\^()|D08X]+$'),             # cdparanoia progress bar symbols
    re.compile(r'^\s*$'),                                  # blank/whitespace only
    re.compile(r'^Done\.$'),                               # cdparanoia "Done."
]

# Phase markers for per-track progress tracking
_PHASE_GRABBING = re.compile(r'Grabbing track (\d+):')
_PHASE_ENCODING = re.compile(r'Encoding track (\d+) of')
_PHASE_TAGGING = re.compile(r'Tagging track (\d+) of')
_PHASE_NORMALIZING = re.compile(r'Normalizing track (\d+) of')


def _classify_abcde_line(line):
    """Classify an abcde/cdparanoia output line.

    Returns: 'error', 'warning', 'debug', or 'info'.
    """
    for pattern in _ABCDE_ERROR_PATTERNS:
        if pattern.search(line):
            return 'error'
    for pattern in _ABCDE_WARNING_PATTERNS:
        if pattern.search(line):
            return 'warning'
    for pattern in _ABCDE_DEBUG_PATTERNS:
        if pattern.search(line):
            return 'debug'
    return 'info'


def _stream_abcde_output(proc, job):
    """Read abcde stdout/stderr line by line, log through structlog, track progress.

    Each line is classified by severity and logged as a structured JSON entry.
    Returns a list of error lines found in the output (for post-rip checking).

    Raises TimeoutError if no output is received within the configured
    CD_RIP_TIMEOUT (default 600 seconds / 10 minutes).  This catches
    cdparanoia hangs on bad sectors that would otherwise block forever.
    """
    import select

    timeout = int(cfg.arm_config.get("CD_RIP_TIMEOUT", 600))

    # Check if select() is usable (real file descriptor required — not available
    # with mock objects in tests, or if timeout is disabled).
    use_select = timeout > 0
    if use_select:
        try:
            fd = proc.stdout.fileno()
            if not isinstance(fd, int):
                use_select = False
        except (AttributeError, TypeError, OSError, ValueError):
            use_select = False

    seen_grabbing: set[int] = set()
    seen_encoding: set[int] = set()
    seen_tagging: set[int] = set()
    error_lines: list[str] = []
    last_phase_update = 0

    # When select is available, use readline with timeout.
    # Otherwise fall back to simple iteration (tests use mock iterators).
    if use_select:
        def _next_line():
            ready, _, _ = select.select([proc.stdout], [], [], timeout)
            if not ready:
                logging.error(
                    "CD rip stalled — no output for %d seconds. Killing abcde.", timeout
                )
                proc.kill()
                proc.wait()
                raise TimeoutError(
                    f"CD rip timed out after {timeout}s of no output (cdparanoia hang?)"
                )
            return proc.stdout.readline()
    else:
        _iter = iter(proc.stdout)

        def _next_line():
            return next(_iter, '')

    while True:
        raw_line = _next_line()
        if not raw_line:
            break  # EOF — process exited

        line = raw_line.rstrip('\n\r')
        if not line:
            continue

        level = _classify_abcde_line(line)

        if level == 'error':
            logging.error(line)
            error_lines.append(line)
        elif level == 'warning':
            logging.warning(line)
        elif level == 'debug':
            logging.debug(line)
        else:
            logging.info(line)

        # Track progress from abcde phase markers
        m = _PHASE_GRABBING.match(line)
        if m:
            seen_grabbing.add(int(m.group(1)))
        m = _PHASE_ENCODING.match(line)
        if m:
            seen_encoding.add(int(m.group(1)))
        m = _PHASE_TAGGING.match(line)
        if m:
            seen_tagging.add(int(m.group(1)))

        # Throttle DB updates to avoid hammering SQLite
        now = time.time()
        if now - last_phase_update > 3:
            _apply_track_phases(job, seen_grabbing, seen_encoding, seen_tagging)
            last_phase_update = now

    # Final phase update after process exits
    _apply_track_phases(job, seen_grabbing, seen_encoding, seen_tagging)
    return error_lines


def _apply_track_phases(job, grabbing, encoding, tagging):
    """Set per-track ripped/status based on the abcde phases observed so far."""
    try:
        tracks = Track.query.filter_by(job_id=job.job_id).all()
        changed = False
        for t in tracks:
            try:
                tn = int(t.track_number)
            except (ValueError, TypeError):
                continue
            if tn in tagging:
                if t.status != TrackStatus.success.value:
                    t.ripped = True
                    t.status = TrackStatus.success.value
                    changed = True
            elif tn in encoding:
                if t.status != TrackStatus.encoding.value:
                    t.status = TrackStatus.encoding.value
                    changed = True
            elif tn in grabbing:
                if t.status != TrackStatus.ripping.value:
                    t.status = TrackStatus.ripping.value
                    changed = True
        if changed:
            db.session.commit()
    except Exception as exc:
        logging.debug("Could not update track phases: %s", exc)
        db.session.rollback()


# cdparanoia flags keyed by RIP_SPEED_PROFILE. Keys MUST stay in lockstep
# with arm.enums.SpeedProfile members; the dict-comprehension form below
# would catch a rename via KeyError, but the explicit literal is easier
# for grep + faster to read.
_SPEED_PROFILES = {
    SpeedProfile.safe.value: "",       # full paranoia, slowest, best for scratched discs
    SpeedProfile.fast.value: "-Y",     # disable extra paranoia, ~2-4x faster
    SpeedProfile.fastest.value: "-Z",  # no error correction, pristine discs only
}


def _build_custom_abcde_config(base_config, disc_number=None,
                               disc_folder_pattern=None, speed_profile=None):
    """Create a temporary abcde config with per-job overrides.

    Supports two optional customizations applied to the base config:

    * **disc_number** — injects a disc subfolder into OUTPUTFORMAT after the
      album component so multi-disc sets get per-disc subfolders.
      *disc_folder_pattern* controls the folder name (default ``Disc {num}``).
    * **speed_profile** — appends a ``CDPARANOIAOPTS`` line with the
      cdparanoia flags for the chosen speed profile (safe/fast/fastest).
    """
    import tempfile

    try:
        with open(base_config, "r", errors="replace") as f:
            content = f.read()
    except OSError:
        logging.warning("Could not read abcde config %s for overrides", base_config)
        return None

    # --- Disc subfolder injection ---
    if disc_number:
        pattern = disc_folder_pattern or "Disc {num}"
        disc_dir = pattern.replace("{num}", str(disc_number))

        def _inject_disc(match):
            fmt = match.group(1)
            if "${ALBUMFILE}/" in fmt:
                fmt = fmt.replace("${ALBUMFILE}/", "${ALBUMFILE}/" + disc_dir + "/")
            else:
                fmt = disc_dir + "/" + fmt
            return "OUTPUTFORMAT='" + fmt + "'"

        def _inject_va_disc(match):
            fmt = match.group(1)
            if "${ALBUMFILE}/" in fmt:
                fmt = fmt.replace("${ALBUMFILE}/", "${ALBUMFILE}/" + disc_dir + "/")
            else:
                fmt = disc_dir + "/" + fmt
            return "VAOUTPUTFORMAT='" + fmt + "'"

        content = re.sub(r"^OUTPUTFORMAT='([^']+)'", _inject_disc, content, count=1, flags=re.MULTILINE)
        content = re.sub(r"^VAOUTPUTFORMAT='([^']+)'", _inject_va_disc, content, count=1, flags=re.MULTILINE)

    # --- Speed profile (cdparanoia opts) ---
    if speed_profile and speed_profile in _SPEED_PROFILES:
        opts = _SPEED_PROFILES[speed_profile]
        if opts:
            # Remove any existing CDPARANOIAOPTS line, then append ours
            content = re.sub(r"^#?CDPARANOIAOPTS=.*$", "", content, flags=re.MULTILINE)
            content = content.rstrip() + f'\nCDPARANOIAOPTS="{opts}"\n'
            logging.info("CD rip speed profile: %s (CDPARANOIAOPTS=%s)", speed_profile, opts)

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".conf", prefix="abcde_custom_", delete=False)
    tmp.write(content)
    tmp.close()
    logging.info("Created custom abcde config: %s", tmp.name)
    return tmp.name


def rip_music(job, logfile):
    """
    Rip music CD using abcde config\n
    :param job: job object
    :param logfile: location of logfile\n
    :return: Bool on success or fail
    """

    abcfile = cfg.arm_config["ABCDE_CONFIG_FILE"]
    tmp_config = None
    if job.disctype == "music":
        logging.info("Disc identified as music")
        logpath = os.path.join(job.config.LOGPATH, logfile)

        # Audio output format (e.g. flac, mp3, vorbis)
        audio_fmt = getattr(job.config, "AUDIO_FORMAT", None) or cfg.arm_config.get("AUDIO_FORMAT", "")
        fmt_flag = f" -o {audio_fmt}" if audio_fmt else ""

        # Determine if we need a custom abcde config
        disc_num = getattr(job, "disc_number", None) or 0
        disc_tot = getattr(job, "disc_total", None) or 0

        multi_disc_enabled = getattr(job.config, "MUSIC_MULTI_DISC_SUBFOLDERS", None)
        if multi_disc_enabled is None:
            multi_disc_enabled = cfg.arm_config.get("MUSIC_MULTI_DISC_SUBFOLDERS", True)

        need_disc = bool(multi_disc_enabled) \
            and isinstance(disc_num, int) and isinstance(disc_tot, int) \
            and disc_num > 0 and disc_tot > 1

        disc_folder_pattern = getattr(job.config, "MUSIC_DISC_FOLDER_PATTERN", None) \
            or cfg.arm_config.get("MUSIC_DISC_FOLDER_PATTERN", "Disc {num}")

        speed = getattr(job.config, "RIP_SPEED_PROFILE", None) \
            or cfg.arm_config.get("RIP_SPEED_PROFILE", "safe")
        need_speed = speed in _SPEED_PROFILES and speed != "safe"

        if (need_disc or need_speed) and os.path.isfile(abcfile):
            tmp_config = _build_custom_abcde_config(
                abcfile,
                disc_number=disc_num if need_disc else None,
                disc_folder_pattern=disc_folder_pattern if need_disc else None,
                speed_profile=speed if need_speed else None,
            )

        config_to_use = tmp_config or (abcfile if os.path.isfile(abcfile) else None)

        # Clean up any stale abcde workdirs from crashed rips — prevents
        # abcde from resuming partial/corrupt data instead of starting fresh.
        import glob
        for stale in glob.glob('/home/arm/abcde.*'):
            if os.path.isdir(stale):
                logging.info("Removing stale abcde workdir: %s", stale)
                import shutil
                shutil.rmtree(stale, ignore_errors=True)

        # Build command as a list (no shell redirection - we capture stdout/stderr
        # directly and feed it through structured logging).
        cmd = ['abcde', '-d', str(job.devpath)]
        if config_to_use:
            cmd += ['-c', config_to_use]
        if audio_fmt:
            cmd += ['-o', audio_fmt]

        logging.debug("Sending command: %s", cmd)
        args = {"status": JobState.AUDIO_RIPPING.value}
        database_updater(args, job)

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, errors='replace')
            error_lines = _stream_abcde_output(proc, job)
            proc.wait()
            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, cmd)
            # abcde exits 0 even on drive I/O errors — check collected errors
            if error_lines:
                err = "; ".join(error_lines)
                logging.error(err)
                args = {"status": JobState.FAILURE.value, "errors": err}
                database_updater(args, job)
                # Music rip failure: mark per-track status as failed so the
                # UI can render the failure state. Job-level JobState.FAILURE
                # above is the source of truth at the job level.
                _update_music_tracks(job, ripped=False, status=TrackStatus.failed.value)
                return False
            logging.info("abcde call successful")
            _update_music_tracks(job, ripped=True, status=TrackStatus.success.value)
            args = {"status": JobState.IDLE.value}
            database_updater(args, job)
            return True
        except TimeoutError as te:
            err = str(te)
            args = {"status": JobState.FAILURE.value, "errors": err}
            database_updater(args, job)
            # Music rip failure: mark per-track status as failed.
            _update_music_tracks(job, ripped=False, status=TrackStatus.failed.value)
            logging.error(err)
        except subprocess.CalledProcessError as ab_error:
            err = f"Call to abcde failed with code: {ab_error.returncode}"
            args = {"status": JobState.FAILURE.value, "errors": err}
            database_updater(args, job)
            # Music rip failure: same rationale as the TimeoutError branch.
            _update_music_tracks(job, ripped=False, status=TrackStatus.failed.value)
            logging.error(err)
        finally:
            if tmp_config:
                try:
                    os.unlink(tmp_config)
                except OSError:
                    pass
    return False


def rip_data(job):
    """
    Rip data disc using dd on the command line\n
    :param job: Current job
    :return: True/False for success/fail
    """
    success = False
    if job.label == "" or job.label is None:
        job.label = "data-disc"
    # get filesystem in order
    raw_path = os.path.join(job.config.RAW_PATH, str(job.label))
    type_sub_folder = job.type_subfolder if hasattr(job, 'type_subfolder') else "unidentified"
    final_path = os.path.join(job.config.COMPLETED_PATH, type_sub_folder)
    final_file_name = str(job.label)

    if (make_dir(raw_path)) is False:
        random_time = str(round(time.time() * 100))
        raw_path = os.path.join(job.config.RAW_PATH, str(job.label) + "_" + random_time)
        final_file_name = f"{job.label}_{random_time}"
        make_dir(raw_path, False)

    final_path = os.path.join(final_path, final_file_name)
    incomplete_filename = os.path.join(raw_path, final_file_name + ".part")
    make_dir(final_path)
    logging.info(f"Ripping data disc to: {incomplete_filename}")
    # Added from pull 366
    cmd = f'dd if="{job.devpath}" of="{incomplete_filename}" {cfg.arm_config["DATA_RIP_PARAMETERS"]} 2>> ' \
          f'{os.path.join(job.config.LOGPATH, job.logfile)}'
    logging.debug(f"Sending command: {cmd}")
    try:
        subprocess.check_output(cmd, shell=True).decode("utf-8")
        full_final_file = os.path.join(final_path, f"{final_file_name}.iso")
        if os.path.isfile(full_final_file):
            unique_name = f"{final_file_name}_{job.job_id}.iso"
            full_final_file = os.path.join(final_path, unique_name)
            logging.warning(f"Completed ISO already exists — using unique name: {unique_name}")
        logging.info(f"Moving data-disc from '{incomplete_filename}' to '{full_final_file}'")
        try:
            shutil.move(incomplete_filename, full_final_file)
        except Exception as error:
            logging.error(f"Unable to move '{incomplete_filename}' to '{final_path}' - Error: {error}")
        logging.info("Data rip call successful")
        database_updater({'path': full_final_file}, job)
        success = True
    except subprocess.CalledProcessError as dd_error:
        err = f"Data rip failed with code: {dd_error.returncode}({dd_error.output})"
        logging.error(err)
        os.unlink(incomplete_filename)
        args = {"status": JobState.FAILURE.value, "errors": err}
        database_updater(args, job)
    try:
        logging.info(f"Trying to remove raw_path: '{raw_path}'")
        shutil.rmtree(raw_path)
    except OSError as error:
        logging.error(f"Error: {error.filename} - {error.strerror}.")
    return success


def try_add_default_user():
    """
    Added to fix missmatch from the armui and armripper\n
    This will try to add a default user for the armui
    with the details\n
    Username: admin\n
    Password: password\n
    :return: None
    """
    try:
        username = "admin"
        pass1 = "password".encode('utf-8')
        hashed = bcrypt.gensalt(12)
        database_adder(User(email=username, password=bcrypt.hashpw(pass1, hashed), hashed=hashed))
        perm_file = Path(PurePath(cfg.arm_config['INSTALLPATH'], "installed"))
        write_permission_file = open(perm_file, "w")
        write_permission_file.write("boop!")
        write_permission_file.close()
    except Exception as error:
        #  notify("", str(error), str(error))
        logging.error(error)


def put_track(job, t_no, seconds, aspect, fps, mainfeature, source, filename="",
              chapters=0, filesize=0, title=None):
    """
    Put data into a track instance.\n
    Having this here saves importing the models file everywhere\n

    :param job: instance of job class
    :param str t_no: track number
    :param int seconds: length of track in seconds
    :param str aspect: aspect ratio (ie '16:9')
    :param str fps: frames per second:str (-not a float-)
    :param bool mainfeature: If the file is identified as the mainfeature
    :param str source: Source of information (HandBrake, MakeMKV, abcde)
    :param str filename: filename of track
    :param int chapters: number of chapters in track
    :param int filesize: size of track in bytes
    :param str title: per-track title (e.g. song name from MusicBrainz)
    """

    logging.debug(
        f"Track #{int(t_no):02} Length: {seconds: >4} fps: {float(fps):2.3f} "
        f"aspect: {aspect: >4} Mainfeature: {mainfeature} Source: {source} "
        f"Chapters: {chapters} Size: {filesize}")

    job_track = Track(
        job_id=job.job_id,
        track_number=t_no,
        length=seconds,
        aspect_ratio=aspect,
        fps=fps,
        main_feature=mainfeature,
        source=source,
        basename=job.title,
        filename=filename,
        chapters=chapters,
        filesize=filesize
    )
    if title:
        job_track.title = title
    job_track.ripped = False
    database_adder(job_track)


def mark_prescan_filter_state(job, minlength: int, maxlength: int) -> None:
    """Apply length-based filter to job tracks immediately after pre-scan.

    Before this runs, fresh Track rows have process=None (the
    'not yet decided' default). The serializer at
    arm/api/v1/jobs.py:_track_to_dict treats None as True, so
    every track would render as rippable in the disc-review widget.

    This helper stamps process=False + skip_reason for tracks
    outside the configured length bounds, so the widget's
    isFiltered(track) check (track.process === false) shows them
    as 'skip'. Long-enough tracks keep process=None and render
    rippable. The rip-time filter (process_single_tracks for
    manual mode, the all-tracks loop for auto mode) still runs
    afterward and refines the decision per track.

    No-ops on tracks with length=None (music CDs, unscanned
    folder imports). Caller is responsible for db.session.commit().
    """
    from arm_contracts.enums import SkipReason

    for t in job.tracks:
        if t.length is None:
            continue
        if t.length < minlength:
            t.process = False
            t.skip_reason = SkipReason.too_short.value
        elif t.length > maxlength:
            t.process = False
            t.skip_reason = SkipReason.too_long.value


def arm_setup(arm_log: Logger) -> None:
    """
    Setup arm - Create all the directories we need for arm to run
    check that folders are writeable, and the db file is writeable
    """
    arm_directories = (
        cfg.arm_config['RAW_PATH'],
        cfg.arm_config['COMPLETED_PATH'],
        cfg.arm_config['LOGPATH'],
        os.path.join(cfg.arm_config['LOGPATH'], "progress"),
    )
    # Check if DB file is writeable
    if not os.access(cfg.arm_config['DBFILE'], os.W_OK):
        arm_log.critical(f"Can't write to database file: {cfg.arm_config['DBFILE']}")
    # Check directories for read/write permission -> create if they don't exist
    for folder in arm_directories:
        os.makedirs(folder, exist_ok=True)
        if not os.access(folder, os.R_OK):
            arm_log.error(f"Can't read from folder: {folder}")
        if not os.access(folder, os.W_OK):
            arm_log.critical(f"Can't write to folder: {folder}")


def database_updater(args, job, wait_time=90):
    """Try to commit attribute changes to the database.

    Delegates to :func:`arm.services.files.database_updater` (single
    implementation).  Ripper callers keep a higher default *wait_time*
    because rip processes are more tolerant of delays than API requests.
    """
    from arm.services.files import database_updater as _database_updater
    return _database_updater(args, job, wait_time=wait_time)


def database_adder(obj_class):
    """Add an ORM object to the session and commit.

    Retry on SQLite BUSY is handled by :class:`~arm.database.RetrySession`
    at the session level.  This function remains as a convenience wrapper.

    :param obj_class: Job/Config/Track/ etc
    :return: True if success
    """
    logging.debug(f"Adding {type(obj_class).__name__} to database")
    db.session.add(obj_class)
    db.session.commit()
    logging.debug(f"successfully written {type(obj_class).__name__} to the database")
    return True


def clean_old_jobs():
    """
    Check for running jobs - Update failed jobs that are no longer running\n
    :return: None
    """
    # Exclude terminal states and transcode states (managed by the external transcoder)
    excluded = [
        JobState.FAILURE.value,
        JobState.SUCCESS.value,
        JobState.TRANSCODE_WAITING.value,
        JobState.TRANSCODE_ACTIVE.value,
    ]
    active_jobs = db.session.query(Job).filter(Job.status.notin_(excluded)).all()
    # Clean up abandoned jobs
    for job in active_jobs:
        if job.pid is None:
            logging.info(f"Job #{job.job_id} has no PID (folder rip or pre-scan). Skipping.")
            continue
        if psutil.pid_exists(job.pid):
            job_process = psutil.Process(job.pid)
            if job.pid_hash == hash(job_process):
                logging.info(f"Job #{job.job_id} with PID {job.pid} is currently running.")
        else:
            logging.info(f"Job #{job.job_id} with PID {job.pid} has been abandoned. "
                         f"Updating job status to fail.")
            database_updater({'status': JobState.FAILURE.value}, job)
            if job.drive is not None:
                job.drive.release_current_job()
                db.session.commit()


def check_ip():
    """
        Check if user has set an ip in the config file
        if not gets the most likely ip
        arguments:
        none
        return: the ip of the host or 127.0.0.1
    """
    if cfg.arm_config['WEBSERVER_IP'] != 'x.x.x.x':
        return cfg.arm_config['WEBSERVER_IP']
    # autodetect host IP address
    ip_list = []
    for interface in interfaces():
        inet_links = ifaddresses(interface).get(AF_INET, [])
        for link in inet_links:
            ip_address = link['addr']
            if ip_address != '127.0.0.1' and not ip_address.startswith('172'):
                ip_list.append(ip_address)
    if len(ip_list) > 0:
        return ip_list[0]
    return '127.0.0.1'



def duplicate_run_check(dev_path):
    """
    Kills this run if another run was triggered recently on the same device\n
    Some drives will trigger the udev twice causing 1 disc insert to add 2 jobs\n
    this stops that issue
    :return: None
    """
    # Log running jobs by job status
    running_jobs = (
        db.session.query(Job)
        .filter(
            ~Job.finished,
            Job.devpath == dev_path,
        )
        .all()
    )
    for job in running_jobs:
        logging.info(f"Device {dev_path}: Job ({job.job_id}) status '{job.status}'")
    # check for running jobs by associated drive.
    drive = SystemDrives.query.filter_by(mount=dev_path).first()
    if not drive.processing:
        # Drive is not currently processing — check post-eject grace period.
        # After a rip finishes, the eject triggers udev again. If the previous
        # job finished less than 30s ago, skip this run.
        prev = drive.job_previous
        if prev and prev.stop_time:
            elapsed = (datetime.datetime.now() - prev.stop_time).total_seconds()
            if elapsed < 30:
                raise RipperException(
                    f"Post-eject grace period: previous job on {dev_path} "
                    f"finished {elapsed:.0f}s ago (< 30s)"
                )
        return  # drive is not processing, so we are safe to start another run.
    job = drive.job_current
    logging.critical(f'Drive {dev_path} has an active Job ({job.job_id}): {job.status}.')
    # log time
    job_time = ceil(job.run_time // 60)
    logging.info(f"Job was started {job_time}min ago.")
    if (job_time) < 3:
        logging.info("Job was started less than 3min ago.")
    raise RipperException(f"Job already running on {dev_path}")


def save_disc_poster(final_directory, job):
    """
     Use FFMPeg to convert Large Poster if enabled in config
    :param final_directory: folder to put the poster in
    :param job: Current Job
    :return: None
    """
    if job.disctype != "dvd" or not cfg.arm_config["RIP_POSTER"]:
        return

    result = subprocess.run(
        ["mount", job.devpath],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        logging.error(f"Failed to mount {job.devpath}: {result.stderr.strip()}")
        return

    try:
        ntsc_poster = os.path.join(job.mountpoint, "JACKET_P", "J00___5L.MP2")
        pal_poster = os.path.join(job.mountpoint, "JACKET_P", "J00___6L.MP2")
        poster_out = os.path.join(final_directory, "poster.png")

        if os.path.isfile(ntsc_poster):
            logging.info("Converting NTSC Poster Image")
            subprocess.run(
                ["ffmpeg", "-i", ntsc_poster, poster_out],
                capture_output=True, text=True,
            )
        elif os.path.isfile(pal_poster):
            logging.info("Converting PAL Poster Image")
            subprocess.run(
                ["ffmpeg", "-i", pal_poster, poster_out],
                capture_output=True, text=True,
            )
    finally:
        umount = subprocess.run(
            ["umount", job.devpath],
            capture_output=True, text=True,
        )
        if umount.returncode != 0:
            logging.error(f"Failed to umount {job.devpath}: {umount.stderr.strip()}")



def normalize_series_name(series_name):
    """Normalize series name into a safe, consistent folder name.

    :param series_name: The series title string
    :return: Normalized string safe for filesystem use
    """
    if not series_name:
        return ""
    normalized = unicodedata.normalize('NFKD', series_name)
    normalized = normalized.encode('ASCII', 'ignore').decode('ASCII')
    normalized = re.sub(r'[^\w\-()]', '_', normalized)
    normalized = re.sub(r'_+', '_', normalized)
    return normalized.strip('_')


def get_tv_series_parent_folder(job):
    """Generate parent series folder name for grouping multiple TV discs.

    Returns the series title with year: "Series Title (Year)" or "Series Title".
    Used when GROUP_TV_DISCS_UNDER_SERIES is enabled.

    :param job: Job object
    :return: Parent folder name string
    """
    return job.formatted_title


def get_tv_folder_name(job):
    """Generate TV series folder name based on configuration.

    If USE_DISC_LABEL_FOR_TV is enabled and disc label parsing succeeds:
        Returns: "{normalized_series_name}_{disc_identifier}" e.g. "Breaking_Bad_S1D1"
    Otherwise, falls back to standard naming via formatted_title.

    :param job: Job object containing title, label, year, etc.
    :return: Folder name string (never empty — falls back to formatted_title)
    """
    from arm.ripper.arm_matcher import parse_label

    use_disc_label = getattr(job.config, 'USE_DISC_LABEL_FOR_TV', False) if hasattr(job, 'config') else False

    if not use_disc_label:
        return job.formatted_title

    if job.video_type != "series":
        return job.formatted_title

    series_name = job.title_manual if job.title_manual else job.title
    if not series_name:
        logging.warning("No series title available, falling back to standard naming")
        return job.formatted_title

    label_info = parse_label(job.label)
    disc_id = label_info.disc_identifier
    if disc_id:
        normalized_name = normalize_series_name(series_name)
        folder_name = f"{normalized_name}_{disc_id}"
        logging.info(f"Using disc label-based folder name: '{folder_name}' "
                     f"(from series '{series_name}' and label '{job.label}')")
        return folder_name

    logging.info(f"Could not parse disc identifier from label '{job.label}', "
                 f"falling back to standard naming")
    return job.formatted_title


def _is_empty_failed_rip(path, label):
    """Check if a directory is an empty leftover from a failed rip.

    Returns True if the directory exists, contains no files, and the most
    recent job with the same label is in a failure state (or no successful
    job exists for this label).
    """
    if not os.path.isdir(path):
        return False
    # Check for any files (not just immediate children — recurse)
    for _root, _dirs, files in os.walk(path):
        if files:
            return False
    # Empty folder — check if last job with this label failed
    if label is None:
        return True
    try:
        last_job = (Job.query
                    .filter_by(label=label)
                    .order_by(Job.job_id.desc())
                    .first())
    except Exception:
        # DB not available — be conservative, don't auto-clean
        return False
    if last_job is None:
        return True
    return last_job.status in (JobState.FAILURE.value,)


def check_for_dupe_folder(have_dupes, hb_out_path, job):
    """
    Check if the folder already exists
     if it exists lets make a new one using random numbers
    :param have_dupes: is this title in the local arm database
    :param hb_out_path: path to HandBrake out
    :param job: Current job
    :return: Final media directory path
    """
    if (make_dir(hb_out_path)) is False:
        logging.info(f"Output directory \"{hb_out_path}\" already exists.")
        # If the folder is empty and from a failed rip, clean it up and reuse
        if _is_empty_failed_rip(hb_out_path, job.label):
            import shutil
            logging.info(f"Removing empty folder from failed rip: \"{hb_out_path}\"")
            shutil.rmtree(hb_out_path)
            make_dir(hb_out_path)
        # Only begin ripping if we are allowed to make duplicates
        # Or the successful rip of the disc is not found in our database
        elif cfg.arm_config["ALLOW_DUPLICATES"] or not have_dupes:
            logging.debug(f"Value of ALLOW_DUPLICATES: {cfg.arm_config['ALLOW_DUPLICATES']}")
            logging.debug(f"Value of have_dupes: {have_dupes}")
            suffix = job.stage if job.stage else str(int(time.time()))
            hb_out_path = hb_out_path + "_" + suffix
            # Also clean empty folders from failed rips at the deduped path
            if _is_empty_failed_rip(hb_out_path, job.label):
                import shutil
                logging.info(f"Removing empty folder from failed rip: \"{hb_out_path}\"")
                shutil.rmtree(hb_out_path)
            make_dir(hb_out_path, False)
        else:
            # We aren't allowed to rip dupes, notify and exit
            logging.warning(
                f"Duplicate disc detected: '{job.title}' (label={job.label}, "
                f"crc={job.crc_id}). Skipping — ALLOW_DUPLICATES is false."
            )
            # Lazy imports mirror notify_entry() — utils.py is imported
            # very early in the worker, and arm.notifications pulls in
            # the dispatcher/dependency graph we want loaded only when
            # the producer actually fires.
            from datetime import datetime as _dt, timezone
            from uuid import uuid4
            from arm_contracts import JobDuplicateDetectedEvent
            from arm.notifications import publish_event
            from arm.ripper._notify_helpers import job_disc_type
            # ``check_for_dupe_folder`` only knows that *a* prior job
            # collided (have_dupes=True) — it does not look up the
            # specific prior job's id. Use 0 as a sentinel to keep the
            # producer simple; consumers that need the exact previous
            # job can resolve it from the title/label.
            publish_event(JobDuplicateDetectedEvent(
                event_id=uuid4(),
                occurred_at=_dt.now(timezone.utc),
                job_id=job.job_id,
                job_title=job.title or "",
                job_disc_type=job_disc_type(job),
                job_imdb_id=job.imdb_id,
                existing_job_id=0,
                existing_output_path=None,
            ))
            raise RipperException("Duplicate rips are disabled")
    logging.info(f"Final Output directory \"{hb_out_path}\"")
    return hb_out_path


def _apply_previous_rip(result, job):
    """Apply metadata from a previous successful rip to the current job."""
    title = result['title'] if result['title'] else job.label
    year = extract_year(result['year']) if result['year'] != "" else ""
    poster_url = result['poster_url'] if result['poster_url'] != "" else None
    hasnicetitle = (str(result['hasnicetitle']).lower() == 'true')
    video_type = result['video_type'] if result['hasnicetitle'] != "" else "unknown"
    database_updater({
        "title": title, "year": year, "poster_url": poster_url,
        "hasnicetitle": hasnicetitle, "video_type": video_type,
    }, job)


def job_dupe_check(job):
    """
    function for checking the database to look for jobs that have completed
    successfully with the same label
    :param job: The job obj, so we can use the crc/title etc.
    :return: True/False, dict/None
    """
    logging.debug(f"Trying to find jobs with matching Label={job.label}")
    if job.label is None:
        logging.info("Disc title 'None' not searched in database")
        return False

    previous_rips = Job.query.filter_by(label=job.label, status=JobState.SUCCESS.value)
    results = [
        {str(k): str(v) for k, v in j.get_d().items()}
        for j in previous_rips
    ]

    if not results:
        logging.info("We have no previous rips/jobs matching this label")
        return False

    logging.debug(f"we have {len(results)} jobs")
    if len(results) != 1:
        logging.debug(f"Skipping - There are too many results [{len(results)}]")
        return False

    _apply_previous_rip(results[0], job)
    return True


def is_ripping_paused():
    """Check whether global ripping is paused via AppState.

    Uses a direct engine connection to bypass the session's open
    transaction, which may hold a stale SQLite read snapshot.
    """
    try:
        with db.engine.connect() as conn:
            row = conn.execute(
                db.text("SELECT ripping_paused FROM app_state WHERE id = 1")
            ).first()
            return bool(row[0]) if row else False
    except Exception:
        return False


def _poll_manual_wait(job):
    """Poll loop for manual wait. Returns when the job should proceed."""
    sleep_time = 0
    while True:
        time.sleep(5)
        sleep_time += 5
        db.session.refresh(job)

        if job.status != JobState.MANUAL_PAUSED.value:
            logging.info("Job status changed externally (cancelled). Aborting wait.")
            raise RipperException("Job was cancelled during manual wait.")

        paused_now = is_ripping_paused()
        job_paused = getattr(job, 'manual_pause', False) or False

        if job.manual_start:
            logging.info("Manual start triggered by user.")
            return

        if job_paused:
            continue

        if job.title_manual and not paused_now:
            logging.info("Manual override found.  Overriding auto identification values.")
            database_updater({"hasnicetitle": True, "updated": True}, job)
            return

        if not paused_now and sleep_time >= job.config.MANUAL_WAIT_TIME:
            logging.info("Manual wait time expired. Proceeding.")
            return


def check_for_wait(job):
    """
    Wait if we have waiting for user input updates\n\n
    :param job: Current Job
    :return: None
    """
    globally_paused = is_ripping_paused()
    if not (job.config.MANUAL_WAIT or globally_paused):
        return

    if globally_paused:
        logging.info("Global ripping paused. Waiting for manual start.")
    else:
        logging.info(f"Waiting {job.config.MANUAL_WAIT_TIME} seconds for manual override.")
    import datetime
    database_updater({"status": JobState.MANUAL_PAUSED.value,
                      "wait_start_time": datetime.datetime.now()}, job)
    _poll_manual_wait(job)
    database_updater({"status": JobState.IDLE.value, "manual_start": False}, job)


def get_drive_mode(devpath: str) -> str:
    """
    Retrieve the drive mode for a specified device path.

    This function queries the database for a drive associated with the provided
    device path (`devpath`). If a drive is found, it returns the drive's mode;
    otherwise, it defaults to 'auto'.

    Parameters:
        devpath (str): The device path used to identify the drive in the database.

    Returns:
        str: The drive mode associated with the specified device path if found;
             otherwise, returns 'auto'.
    """
    drive = SystemDrives.query.filter_by(mount=devpath).first()
    if drive:
        mode = drive.drive_mode
    else:
        mode = 'auto'
    return mode
