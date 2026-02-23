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

import os
import logging
import subprocess
import urllib
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
from arm.database import db

# flake8: noqa: W605
from arm.ui import utils as ui_utils


def find_mount(devpath: str) -> str | None:
    """
    Find existing, readable mountpoint for ``devpath`` by calling ``findmnt``

    :return: Absolute path of mountpoint as ``str`` if any, else ``None``
    """
    if output := arm_subprocess(["findmnt", "--json", devpath]):
        mountpoints = json.loads(output)
        for mountpoint in mountpoints["filesystems"]:
            if os.access(mountpoint["target"], os.R_OK):
                return mountpoint["target"]
    return None


def check_mount(job: Job) -> bool:
    """
    Check if there is a suitable mount for ``job``, if not, try to mount

    :return: ``True`` if mount exists now, ``False`` otherwise
    """
    if mountpoint := find_mount(job.devpath):
        logging.info(f"Found disc {job.devpath} mounted at {mountpoint}")
        job.mountpoint = mountpoint
    else:
        logging.info(f"Trying to mount disc at {job.devpath}...")
        # Mount the specific device; fstab provides the mountpoint and options.
        # Note: "mount --all" requires root even with fstab "users" option,
        # so we mount the single device directly instead.
        arm_subprocess(["mount", job.devpath])
        if mountpoint := find_mount(job.devpath):
            logging.info(f"Successfully mounted disc to {mountpoint}")
            job.mountpoint = mountpoint
        else:
            logging.error("Disc was not and could not be mounted. Rip might fail.")
            return False
    return True


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

    mounted = check_mount(job)

    try:
        # Phase 1: Mount + detect disc type
        if mounted:
            job.get_disc_type(utils.find_file("HVDVD_TS", job.mountpoint))

        if job.disctype in ["dvd", "bluray", "bluray4k"]:

            logging.info("Disc identified as video")

            if cfg.arm_config["GET_VIDEO_TITLE"]:
                # Phase 2: Resolve label from all sources
                resolve_disc_label(job)

                # Phase 3: Disc-specific identification
                if job.disctype == "dvd":
                    identify_dvd(job)
                elif job.disctype in ("bluray", "bluray4k"):
                    identify_bluray(job)

                # Phase 4: Search metadata APIs if not yet identified
                if not job.hasnicetitle:
                    _search_metadata(job)

                # Phase 5: Last resort — use cleaned label as title
                if job.title is None or job.title == "None" or job.title == "":
                    _apply_label_as_title(job)

                logging.info(f"Disc title Post ident -  title:{job.title} "
                             f"year:{job.year} video_type:{job.video_type} "
                             f"disctype: {job.disctype}")
                logging.debug(f"identify.job.end ---- \n\r{job.pretty_table()}")
    finally:
        # Always unmount after identification, even on error (#1664)
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
        urlstring = f"https://1337server.pythonanywhere.com/api/v1/?mode=s&crc64={crc64}"
        logging.debug(urlstring)
        dvd_info_xml = urllib.request.urlopen(urlstring).read()
        arm_api_json = json.loads(dvd_info_xml)
        logging.debug(f"dvd xml - {arm_api_json}")
        logging.debug(f"results = {arm_api_json['results']}")
        if arm_api_json['success']:
            logging.info("Found crc64 id from online API")
            logging.info(f"title is {arm_api_json['results']['0']['title']}")
            args = {
                'title': arm_api_json['results']['0']['title'],
                'title_auto': arm_api_json['results']['0']['title'],
                'year': arm_api_json['results']['0']['year'],
                'year_auto': arm_api_json['results']['0']['year'],
                'imdb_id': arm_api_json['results']['0']['imdb_id'],
                'imdb_id_auto': arm_api_json['results']['0']['imdb_id'],
                'video_type': arm_api_json['results']['0']['video_type'],
                'video_type_auto': arm_api_json['results']['0']['video_type'],
                'poster_url': arm_api_json['results']['0']['poster_img'],
                'poster_url_auto': arm_api_json['results']['0']['poster_img'],
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
    return utils.database_updater(args, job)


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
    search_results = None
    if cfg.arm_config['METADATA_PROVIDER'].lower() == "tmdb":
        logging.debug("provider tmdb")
        search_results = ui_utils.tmdb_search(title, year)
    elif cfg.arm_config['METADATA_PROVIDER'].lower() == "omdb":
        logging.debug("provider omdb")
        search_results = ui_utils.call_omdb_api(str(title), str(year))
    else:
        logging.debug(cfg.arm_config['METADATA_PROVIDER'])
        logging.debug("unknown provider - doing nothing, saying nothing. Getting Kryten")

    if search_results is not None:
        if update_job(job, search_results) is None:
            # Matcher wasn't confident — treat as no results so the
            # retry loop continues with simplified queries
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
