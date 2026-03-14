#!/usr/bin/env python3
"""Identification of dvd/bluray

Phases:
  1. Mount + detect disc type (filesystem-based, always reliable)
  2. Resolve label from all sources (pyudev → blkid → lsdvd → XML)
  3. Disc-specific ID (CRC64 for DVD, XML for Blu-ray)
  4. Search metadata APIs (OMDB/TMDB) if Phase 3 didn't fully identify
  5. Last resort — use cleaned label as title
  Finally: Unmount
"""

import fcntl
import os
import logging
import subprocess
import time
import re
import datetime
import unicodedata
import json
from ast import literal_eval

import pydvdid
import xmltodict
import arm.config.config as cfg
from arm.models import Job

from arm.ripper import utils
from arm.ripper.ProcessHandler import arm_subprocess
from arm.ripper.utils import RipperException
from arm.database import db

# flake8: noqa: W605


def _find_mountpoint(devpath: str) -> str | None:
    """Find an existing, readable mountpoint for *devpath* (quiet — no error logging)."""
    result = subprocess.run(
        ["findmnt", "--json", devpath],
        capture_output=True, text=True,
    )
    if result.returncode == 0 and result.stdout:
        for fs in json.loads(result.stdout).get("filesystems", []):
            if os.access(fs["target"], os.R_OK):
                return fs["target"]
    return None


def _drive_status(devpath: str) -> int:
    """Return raw CDROM_DRIVE_STATUS ioctl value, or -1 on error.

    Values:
      0 = CDS_NO_INFO, 1 = CDS_NO_DISC, 2 = CDS_TRAY_OPEN,
      3 = CDS_DRIVE_NOT_READY, 4 = CDS_DISC_OK, -1 = OS error
    """
    try:
        fd = os.open(devpath, os.O_RDONLY | os.O_NONBLOCK)
        try:
            return fcntl.ioctl(fd, 0x5326, 0)  # CDROM_DRIVE_STATUS
        finally:
            os.close(fd)
    except OSError:
        return -1


def _drive_has_disc(devpath: str) -> bool:
    """Quick check — returns False only if tray is open or no disc.

    USB optical drives (e.g. Pioneer BDR-S12JX) report NOT_READY (3) for
    30-60s during spin-up.  Only NO_DISC and TRAY_OPEN are definitive
    ejection indicators.
    """
    return _drive_status(devpath) not in (-1, 1, 2)


def find_mount(devpath: str) -> str | None:
    """
    Find existing, readable mountpoint for ``devpath`` by calling ``findmnt``.

    Logs errors via :func:`arm_subprocess` — use :func:`_find_mountpoint` when
    error logging is not desired (e.g. inside a retry loop).

    :return: Absolute path of mountpoint as ``str`` if any, else ``None``
    """
    if output := arm_subprocess(["findmnt", "--json", devpath]):
        mountpoints = json.loads(output)
        for mountpoint in mountpoints["filesystems"]:
            if os.access(mountpoint["target"], os.R_OK):
                return mountpoint["target"]
    return None


def _wait_for_drive_ready(devpath: str, timeout: int = 120) -> bool:
    """Poll drive until DISC_OK or timeout.

    USB optical drives can take 30-60s+ to spin up after disc insertion
    or tray close.  Calling ``mount`` while the drive reports NOT_READY
    causes the mount syscall to block for minutes.  Polling first avoids
    this and gives clear log output about what the drive is doing.

    :return: ``True`` if drive reached DISC_OK, ``False`` if ejected/timeout
    """
    _STATUS_NAMES = {0: "NO_INFO", 1: "NO_DISC", 2: "TRAY_OPEN",
                     3: "DRIVE_NOT_READY", 4: "DISC_OK", -1: "OS_ERROR"}
    poll_interval = 3
    elapsed = 0
    last_status = None

    while elapsed < timeout:
        status = _drive_status(devpath)
        if status == 4:  # CDS_DISC_OK
            if elapsed > 0:
                logging.info(f"Drive {devpath} ready after {elapsed}s")
            return True
        if status in (1, 2):  # NO_DISC or TRAY_OPEN — bail
            logging.error(f"Disc ejected from {devpath} (status={_STATUS_NAMES.get(status)})")
            return False
        # Log state changes (not every poll)
        if status != last_status:
            logging.info(
                f"Waiting for drive {devpath} to be ready "
                f"(status={_STATUS_NAMES.get(status, status)}, {elapsed}s/{timeout}s)"
            )
            last_status = status
        time.sleep(poll_interval)
        elapsed += poll_interval

    logging.error(
        f"Drive {devpath} not ready after {timeout}s "
        f"(last status={_STATUS_NAMES.get(last_status, last_status)})"
    )
    return False


def check_mount(job: Job) -> bool:
    """
    Check if there is a suitable mount for ``job``, if not, try to mount.

    First waits for the drive to report DISC_OK (up to 120s) to avoid
    blocking mount syscalls on USB drives that are still spinning up.
    Then retries mount with increasing delays.

    :return: ``True`` if mount exists now, ``False`` otherwise
    """
    # Wait for drive to be ready before attempting mount.
    # USB drives (Pioneer BDR-S12JX) report NOT_READY for 30-60s after
    # insertion; calling mount during this state blocks for ~5 minutes.
    if not _wait_for_drive_ready(job.devpath, timeout=120):
        return False

    max_attempts = 12  # ~60s total with backoff

    for attempt in range(1, max_attempts + 1):
        # Check for existing mount (quiet — no ERROR log on failure)
        if mountpoint := _find_mountpoint(job.devpath):
            if attempt > 1:
                logging.info(f"Disc {job.devpath} mounted at {mountpoint} (attempt {attempt}/{max_attempts})")
            else:
                logging.info(f"Found disc {job.devpath} already mounted at {mountpoint}")
            job.mountpoint = mountpoint
            return True

        # Try to mount — fstab provides the mountpoint and options.
        # Use subprocess.run directly to avoid ERROR-level log spam from
        # arm_subprocess during expected retries.
        logging.info(f"[{attempt}/{max_attempts}] Attempting to mount {job.devpath}...")
        result = subprocess.run(
            ["mount", job.devpath],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            logging.debug(f"mount {job.devpath}: {result.stderr.strip()}")

        # Check if mount succeeded
        if mountpoint := _find_mountpoint(job.devpath):
            logging.info(f"Successfully mounted disc {job.devpath} to {mountpoint} (attempt {attempt}/{max_attempts})")
            job.mountpoint = mountpoint
            return True

        # Bail out early if the disc was ejected
        if not _drive_has_disc(job.devpath):
            logging.error(f"Disc ejected from {job.devpath} during mount retry. Aborting.")
            return False

        # Wait before retrying (ramps from 3s to 5s per attempt)
        if attempt < max_attempts:
            wait = min(2 + attempt, 5)
            logging.warning(
                f"[{attempt}/{max_attempts}] Mount failed for {job.devpath} "
                f"(drive may still be spinning up). Retrying in {wait}s..."
            )
            time.sleep(wait)

    logging.error(
        f"Disc at {job.devpath} could not be mounted after {max_attempts} "
        f"attempts (~60s). The drive may not be responding. Rip will likely fail."
    )
    return False


# ── Phase 2: Label resolution ──────────────────────────────────────────

def _label_from_blkid(devpath):
    """Read UDF/ISO filesystem label via blkid."""
    output = arm_subprocess(["blkid", "-o", "value", "-s", "LABEL", devpath])
    if output:
        return output.strip() or None
    return None


def _label_from_lsdvd(devpath):
    """Read DVD disc title via lsdvd."""
    output = arm_subprocess(["lsdvd", devpath])
    if output:
        for line in output.splitlines():
            if "Disc Title:" in line:
                _, _, title = line.partition("Disc Title:")
                title = title.strip()
                if title:
                    return title
    return None


def _label_from_bluray_xml(mountpoint):
    """Read Blu-ray title from bdmt_eng.xml."""
    xml_path = os.path.join(mountpoint, 'BDMV', 'META', 'DL', 'bdmt_eng.xml')
    try:
        with open(xml_path, "rb") as xml_file:
            doc = xmltodict.parse(xml_file.read())
        title = doc['disclib']['di:discinfo']['di:title']['di:name']
        if title:
            return str(title).strip()
    except Exception:
        pass
    return None


def resolve_disc_label(job):
    """Resolve disc label from all available sources (Phase 2).

    Tries sources in order: pyudev (already set), blkid, lsdvd (DVD),
    bdmt_eng.xml (Blu-ray).
    """
    if job.label:
        logging.debug(f"Label already set from pyudev: {job.label}")
        return

    label = _label_from_blkid(job.devpath)
    if label:
        logging.info(f"Label recovered from blkid: {label}")
        job.label = label
        return

    if job.disctype in ("dvd", "unknown"):
        label = _label_from_lsdvd(job.devpath)
        if label:
            logging.info(f"Label recovered from lsdvd: {label}")
            job.label = label
            return

    if job.disctype in ("bluray", "bluray4k") and job.mountpoint:
        label = _label_from_bluray_xml(job.mountpoint)
        if label:
            logging.info(f"Label recovered from bdmt_eng.xml: {label}")
            job.label = label
            return

    logging.warning("Could not resolve disc label from any source")


# ── Phase 4: Metadata search ───────────────────────────────────────────

def _search_metadata(job):
    """Search OMDB/TMDB for disc metadata (Phase 4).

    Uses the best available title (from XML, CRC64, or label) to query
    the configured metadata provider via identify_loop().
    """
    title = job.title
    if not title or title == "None":
        title = job.label
    if not title:
        logging.info("No title or label available for metadata search")
        return

    title = re.sub('[_ ]', "+", title.strip())
    # Strip 16x9 aspect ratio markers and SKU suffixes
    title = title.replace("16x9", "")
    title = re.sub(r"SKU\b", "", title)

    year = re.sub(r"\D", "", str(job.year)) if job.year else ""

    logging.debug(f"Searching metadata with title: {title} | Year: {year}")

    try:
        response = metadata_selector(job, title, year)
        identify_loop(job, response, title, year)
    except Exception as error:
        logging.info(f"Metadata search failed: {error}. Continuing...")


# ── Phase 5: Last resort ───────────────────────────────────────────────

def _apply_label_as_title(job):
    """Use cleaned disc label as title when all identification failed (Phase 5)."""
    if not job.label:
        job.title = ""
        job.year = ""
    else:
        cleaned = str(job.label).replace('_', ' ').title()
        job.title = job.title_auto = cleaned
    job.hasnicetitle = False
    db.session.commit()


# ── Main entry point ───────────────────────────────────────────────────

def _identify_video_title(job):
    """Run phases 2-5 of video identification."""
    resolve_disc_label(job)

    if job.disctype == "dvd":
        identify_dvd(job)
    elif job.disctype in ("bluray", "bluray4k"):
        identify_bluray(job)

    if not job.hasnicetitle:
        _search_metadata(job)

    if job.title is None or job.title == "None" or job.title == "":
        _apply_label_as_title(job)

    # Auto-enable multi_title for TV series — episodes are distinct titles
    # and the transcoder uses per-track metadata to name output files.
    if job.video_type == "series" and not job.multi_title:
        job.multi_title = True
        db.session.commit()
        logging.info("Auto-enabled multi_title for TV series disc")

    logging.info(f"Disc title Post ident -  title:{job.title} "
                 f"year:{job.year} video_type:{job.video_type} "
                 f"disctype: {job.disctype}")
    logging.debug(f"identify.job.end ---- \n\r{job.pretty_table()}")


def identify(job):
    """Identify disc attributes.

    Phases:
      1. Mount + detect disc type (filesystem-based)
      2. Resolve label from all sources (pyudev → blkid → lsdvd → XML)
      3. Disc-specific ID (CRC64 for DVD, XML for Blu-ray)
      4. Search metadata APIs (OMDB/TMDB) if not yet fully identified
      5. Last resort — use cleaned label as title
      Finally: Unmount
    """
    logging.debug("Identify Entry point --- job ----")

    # Music CDs are already identified during setup() via MusicBrainz —
    # skip mount/identify since audio CDs have no filesystem and mount hangs.
    if job.disctype == "music":
        logging.info("Disc already identified as music — skipping filesystem identification")
        return

    mounted = check_mount(job)

    if not mounted and job.disctype is None:
        raise RipperException(
            f"Could not mount {job.devpath} — drive may be empty, "
            f"still spinning up, or the device no longer exists"
        )

    try:
        if mounted:
            job.get_disc_type(utils.find_file("HVDVD_TS", job.mountpoint))

        if job.disctype in ["dvd", "bluray", "bluray4k"]:
            logging.info("Disc identified as video")
            if cfg.arm_config["GET_VIDEO_TITLE"]:
                _identify_video_title(job)
    finally:
        result = subprocess.run(["umount", job.devpath],
                                stderr=subprocess.PIPE, text=True)
        if result.returncode != 0 and result.stderr:
            logging.debug(f"umount {job.devpath}: {result.stderr.strip()}")


# ── Disc-specific identification ────────────────────────────────────────

def identify_bluray(job):
    """Get Blu-Ray title by parsing bdmt_eng.xml (Phase 3).

    Returns True if a title was successfully extracted, False otherwise.
    When False, the caller handles fallback via _apply_label_as_title().
    """
    try:
        with open(job.mountpoint + '/BDMV/META/DL/bdmt_eng.xml', "rb") as xml_file:
            doc = xmltodict.parse(xml_file.read())
    except OSError as error:
        logging.error("Disc is a bluray, but bdmt_eng.xml could not be found. "
                      "Disc cannot be identified.  Error "
                      f"number is: {error.errno}")
        return False
    except Exception as error:
        logging.error(f"Disc is a bluray, but bdmt_eng.xml could not be parsed: {error}")
        return False

    try:
        bluray_title = doc['disclib']['di:discinfo']['di:title']['di:name']
        if not bluray_title:
            bluray_title = job.label
    except KeyError:
        bluray_title = job.label
        logging.error("Could not parse title from bdmt_eng.xml file.  Disc cannot be identified.")

    if not bluray_title:
        return False

    bluray_modified_timestamp = os.path.getmtime(job.mountpoint + '/BDMV/META/DL/bdmt_eng.xml')
    bluray_year = (datetime.datetime.fromtimestamp(bluray_modified_timestamp).strftime('%Y'))

    bluray_title = unicodedata.normalize('NFKD', str(bluray_title)).encode('ascii', 'ignore').decode()

    bluray_title = bluray_title.replace(' - Blu-rayTM', '')
    bluray_title = bluray_title.replace(' Blu-rayTM', '')
    bluray_title = bluray_title.replace(' - BLU-RAYTM', '')
    bluray_title = bluray_title.replace(' - BLU-RAY', '')
    bluray_title = bluray_title.replace(' - Blu-ray', '')

    bluray_title = utils.clean_for_filename(bluray_title)

    job.title = job.title_auto = bluray_title
    job.year = job.year_auto = bluray_year
    db.session.commit()

    return True


def identify_dvd(job):
    """Try to identify DVD via CRC64 online database lookup (Phase 3).

    Returns True if CRC64 lookup found a match (hasnicetitle=True),
    False otherwise.  Track 99 detection always runs.
    """
    logging.debug(f"\n\r{job.pretty_table()}")

    try:
        crc64 = pydvdid.compute(str(job.mountpoint))
        logging.info(f"DVD CRC64 hash is: {crc64}")
        job.crc_id = str(crc64)
        from arm.services.metadata_sync import lookup_crc_sync
        crc_result = lookup_crc_sync(str(crc64))
        logging.debug(f"CRC lookup result: {crc_result}")
        if crc_result.get("error"):
            logging.warning(f"CRC lookup error for {crc64}: {crc_result['error']}")
        if crc_result.get("found") and crc_result.get("results"):
            hit = crc_result["results"][0]
            logging.info("Found crc64 id from online API")
            logging.info(f"title is {hit['title']}")
            args = {
                'title': hit['title'],
                'title_auto': hit['title'],
                'year': utils.extract_year(hit['year']),
                'year_auto': utils.extract_year(hit['year']),
                'imdb_id': hit['imdb_id'],
                'imdb_id_auto': hit['imdb_id'],
                'video_type': hit['video_type'],
                'video_type_auto': hit['video_type'],
                'poster_url': hit['poster_url'],
                'poster_url_auto': hit['poster_url'],
                'hasnicetitle': True
            }
            utils.database_updater(args, job)
            _detect_track_99(job)
            return True
    except Exception as error:
        logging.error(f"Pydvdid failed with the error: {error}")

    _detect_track_99(job)
    return False


def _detect_track_99(job):
    """Detect 99-track DVDs (copy protection indicator)."""
    output = arm_subprocess(["lsdvd", "-Oy", job.devpath])
    if output:
        try:
            # literal_eval only accepts literals so we have to adjust the output slightly
            tracks = literal_eval(re.sub(r"^.*\{", "{", output)).get("track", [])
            logging.debug(f"Detected {len(tracks)} tracks")
            if len(tracks) == 99:
                job.has_track_99 = True
                if cfg.arm_config["PREVENT_99"]:
                    raise utils.RipperException("Track 99 found and PREVENT_99 is enabled")
        except (SyntaxError, AttributeError) as e:
            logging.error("Failed to parse lsdvd output", exc_info=e)


# ── Metadata helpers (unchanged) ───────────────────────────────────────

def update_job(job, search_results):
    """
    Score all API results against the disc label and update the job
    with the best confident match.

    Uses arm_matcher to pick the best result instead of blindly
    taking Search[0].

    :param job: job obj
    :param search_results: json returned from metadata provider
    :return: None if no confident match, database_updater result otherwise
    """
    from arm.ripper.arm_matcher import match_disc

    if 'Search' not in search_results:
        return None

    # Use the disc label for matching; fall back to current title if no label
    raw_label = job.label or job.title or ''

    # disc_year from prior identification (bdmt_eng.xml timestamp, CRC64 lookup)
    disc_year = str(job.year_auto) if job.year_auto else None

    # type_hint from prior identification (CRC64 lookup may set video_type_auto)
    type_hint = str(job.video_type_auto) if job.video_type_auto else None

    selection = match_disc(
        raw_label,
        search_results,
        disc_year=disc_year,
        type_hint=type_hint,
    )

    if not selection.hasnicetitle or selection.best is None:
        logging.info(
            "No confident match for label '%s' — top scores: %s",
            raw_label,
            [(m.title, f"{m.score:.3f}") for m in selection.all_scored[:3]],
        )
        return None

    best = selection.best
    title = utils.clean_for_filename(best.title)
    logging.debug(
        "Matcher selected '%s' (%s) with score %.3f (title=%.3f year=%.3f type=%.3f)",
        best.title, best.imdb_id, best.score,
        best.title_score, best.year_score, best.type_score,
    )

    args = {
        'year_auto': str(best.year),
        'year': str(best.year),
        'title_auto': title,
        'title': title,
        'video_type_auto': best.type,
        'video_type': best.type,
        'imdb_id_auto': best.imdb_id,
        'imdb_id': best.imdb_id,
        'poster_url_auto': best.poster_url or '',
        'poster_url': best.poster_url or '',
        'hasnicetitle': True,
    }
    # Persist disc number/season from label parsing (e.g. "Disc 2", "S01D03")
    if selection.label_info:
        if selection.label_info.disc_number is not None:
            args['disc_number'] = selection.label_info.disc_number
        if selection.label_info.season_number is not None:
            args['season_auto'] = str(selection.label_info.season_number)
            args['season'] = str(selection.label_info.season_number)
    return utils.database_updater(args, job)


def _to_matcher_format(normalized: list[dict]) -> list[dict]:
    """Convert normalized search results to OMDb-style dicts for arm_matcher."""
    results = []
    for item in normalized:
        media_type = item.get("media_type", "movie")
        results.append({
            "Title": item.get("title", ""),
            "Year": item.get("year", ""),
            "Type": media_type,
            "imdbID": item.get("imdb_id", ""),
            "Poster": item.get("poster_url") or "N/A",
        })
    return results


def metadata_selector(job, title=None, year=None):
    """
    Used to switch between OMDB or TMDB as the metadata provider\n
    - TMDB returned queries are converted into the OMDB format

    Returns the search results dict when the matcher finds a confident match,
    or None when:
    - The API returned no results
    - The matcher rejected all results (no confident match)

    Returning None lets identify_loop() continue trying with simplified queries.

    :param job: The job class
    :param title: this can either be a search string or movie/show title
    :param year: the year of movie/show release

    :return: json/dict object or None
    """
    from arm.services.metadata_sync import search_sync
    from arm.services.metadata import MetadataConfigError

    logging.debug("metadata_selector: title=%r year=%s", title, year)
    try:
        normalized = search_sync(str(title), str(year) if year else None)
    except MetadataConfigError as e:
        logging.error("Metadata provider not configured: %s", e)
        return None
    except Exception as e:
        logging.warning("Metadata search failed for title=%r year=%s: %s", title, year, e)
        normalized = []

    if not normalized:
        logging.debug("Metadata search returned no results for title=%r year=%s", title, year)
        return None

    # Convert normalized results to OMDb-style format for arm_matcher
    search_results = {"Search": _to_matcher_format(normalized)}
    logging.info("Metadata search returned %d results for title=%r", len(normalized), title)

    if update_job(job, search_results) is None:
        # Matcher wasn't confident — treat as no results so the
        # retry loop continues with simplified queries
        logging.debug("Matcher rejected all %d results for title=%r — will retry", len(normalized), title)
        return None

    return search_results


def identify_loop(job, response, title, year):
    """

    :param job:
    :param response:
    :param title:
    :param year:
    """
    # handle failures
    # this is a little kludgy, but it kind of works...
    logging.debug(f"Response = {response}")
    if response is None:
        # try with year first
        response = try_with_year(job, response, title, year)
        # try submitting without the year
        response = try_without_year(job, response, title)

        if response is None:
            while response is None and title.find("-") > 0:
                title = title.rsplit('-', 1)[0]
                logging.debug(f"Trying title: {title}")
                response = metadata_selector(job, title, year)
                logging.debug(f"response: {response}")

            # if still fail, then try slicing off the last word in a loop
            while response is None and title.count('+') > 0:
                title = title.rsplit('+', 1)[0]
                logging.debug(f"Trying title: {title}")
                response = metadata_selector(job, title, year)
                logging.debug(f"response: {response}")
                if response is None:
                    # Still failing - try the words we have without year
                    logging.debug("Removing year...")
                    response = metadata_selector(job, title)


def try_without_year(job, response, title):
    """

    :param job:
    :param response:
    :param title:
    :return:
    """
    if response is None:
        logging.debug("Removing year...")
        response = metadata_selector(job, title)
        logging.debug(f"response: {response}")
    return response


def try_with_year(job, response, title, year):
    """

    :param job:
    :param response:
    :param title:
    :param year:
    :return:
    """
    # If we have a response don't overwrite it
    if response is not None:
        return response
    if year:
        response = metadata_selector(job, title, str(year))
        logging.debug(f"response: {response}")
    # If we still don't have a response try removing a year off
    if response is None and year:
        # This accounts for when
        # the dvd release date is the year following the movie release date
        logging.debug("Subtracting 1 year...")
        response = metadata_selector(job, title, str(int(year) - 1))
    return response
