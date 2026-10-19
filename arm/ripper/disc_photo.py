#!/usr/bin/env python3
"""
Pure helpers for the disc camera feature.

The camera daemon (arm/camera) writes ``<devname>_<YYYYmmdd-HHMMSS>.jpg`` files into
``DISC_PHOTO_PATH`` whenever a drive tray closes, and ``<devname>_<YYYYmmdd-HHMMSS>.barcode``
files when a case was scanned before the close. These functions pick the right photo or barcode
for a job, find stale files, turn OCR output into title search candidates and look a UPC up.

This module deliberately has no ARM, Flask or database imports so it can be unit tested on
its own. The database aware wrappers live in ``arm.ripper.utils``.
"""
import datetime
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

PHOTO_FILENAME_RE = re.compile(r"^(?P<dev>sr\d+)_(?P<stamp>\d{8}-\d{6})\.jpe?g$", re.IGNORECASE)
BARCODE_FILENAME_RE = re.compile(r"^(?P<dev>sr\d+)_(?P<stamp>\d{8}-\d{6})\.barcode$", re.IGNORECASE)
BARCODE_USED_SUFFIX = ".used"
"""Appended to a barcode file once a job has taken its code, so a later disc cannot inherit it."""
BARCODE_ANY_FILENAME_RE = re.compile(r"^(?P<dev>sr\d+)_(?P<stamp>\d{8}-\d{6})\.barcode(\.used)?$", re.IGNORECASE)
PHOTO_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"
COPY_FILENAME = "disc.jpg"
BARCODE_COPY_FILENAME = "disc.barcode"
"""The scanned case barcode, kept next to the rip as one line of text."""
BARCODE_RE = re.compile(r"^[0-9A-Za-z\-]{4,32}$")
UPC_LOOKUP_URL = "https://api.upcitemdb.com/prod/trial/lookup"

# Words and phrases printed on almost every disc label that never help a title search.
_OCR_BOILERPLATE = re.compile(
    r"\b("
    r"dvd(\s*video)?|blu[- ]?ray(\s*disc)?|bd|disc\s*\d*|disk\s*\d*|side\s*[ab12]|"
    r"wide\s*screen|full\s*screen|special\s+edition|collector'?s\s+edition|director'?s\s+cut|"
    r"extended\s+(edition|cut)|anniversary\s+edition|limited\s+edition|unrated|rated\s+\w+|"
    r"region\s*\d|ntsc|pal|dolby(\s+digital)?|dts(\s*-?\s*hd)?|surround|stereo|mono|"
    r"ultra\s*hd|uhd|4k|1080p|720p|hd|hdr|"
    r"feature\s+film|bonus\s+features|special\s+features|deleted\s+scenes|"
    r"all\s+rights\s+reserved|copyright|home\s+entertainment|home\s+video|"
    r"not\s+for\s+(re)?sale|for\s+sale\s+or\s+rental|rental|"
    r"20th\s+century\s+fox|twentieth\s+century\s+fox|warner\s+bros\.?|universal\s+(pictures|studios)|"
    r"paramount(\s+pictures)?|sony\s+pictures|columbia\s+pictures|walt\s+disney(\s+pictures)?|"
    r"lionsgate|lions\s+gate|mgm|dreamworks|new\s+line\s+cinema|touchstone\s+pictures|"
    r"criterion\s+collection|hbo\s+video|bbc\s+video|"
    r"entertainment|pictures|studios?|productions?|films?|distribution|inc|llc|ltd|corp(oration)?|company|"
    r"digital\s+copy|digital\s+hd|includes\s+digital|estimating\s+resolution(\s+as)?"
    r")\b",
    re.IGNORECASE,
)
# Lines carrying a copyright notice name the studio, not the film
_COPYRIGHT_RE = re.compile(r"(©|\(c\)|\bcopyright\b|\ball\s+rights\s+reserved\b)", re.IGNORECASE)
_URL_RE = re.compile(r"(https?://\S+|www\.\S+|\S+\.(com|net|org|co\.uk)\b)", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19[0-9]{2}|20[0-9]{2})\b")
_KEEP_CHARS_RE = re.compile(r"[^0-9A-Za-z &'’:\-!?.,]")
_SPACES_RE = re.compile(r"\s+")
MIN_CANDIDATE_WORDS = 2
MIN_CANDIDATE_LETTERS = 6
"""An OCR line is only searched online when it has this many words, or this many letters."""


def photo_devname(filename: str) -> Optional[str]:
    """Return the drive kernel name (``sr0``) encoded in a disc photo filename, or ``None``."""
    match = PHOTO_FILENAME_RE.match(os.path.basename(filename))
    return match.group("dev").lower() if match else None


def photo_timestamp(filename: str) -> Optional[datetime.datetime]:
    """Return the capture time encoded in a disc photo filename, or ``None``."""
    match = PHOTO_FILENAME_RE.match(os.path.basename(filename))
    if not match:
        return None
    try:
        return datetime.datetime.strptime(match.group("stamp"), PHOTO_TIMESTAMP_FORMAT)
    except ValueError:
        return None


def _daemon_files(photo_dir, pattern=PHOTO_FILENAME_RE) -> Iterable[Path]:
    folder = Path(photo_dir)
    if not folder.is_dir():
        return []
    return (p for p in folder.iterdir() if p.is_file() and pattern.match(p.name))


def _photo_files(photo_dir) -> Iterable[Path]:
    return _daemon_files(photo_dir, PHOTO_FILENAME_RE)


def _find_daemon_file(photo_dir, devname: str, before: datetime.datetime, max_age_seconds: int,
                      grace_seconds: int, pattern) -> Optional[str]:
    """Newest file matching ``pattern`` for ``devname`` written in the window before ``before``."""
    devname = os.path.basename(str(devname)).lower()
    if not devname:
        return None
    window_start = (before - datetime.timedelta(seconds=max_age_seconds)).timestamp()
    window_end = (before + datetime.timedelta(seconds=grace_seconds)).timestamp()
    best: Optional[Tuple[float, str]] = None
    for photo in _daemon_files(photo_dir, pattern):
        match = pattern.match(photo.name)
        if match.group("dev").lower() != devname:
            continue
        try:
            mtime = photo.stat().st_mtime
        except OSError:
            continue
        if mtime < window_start or mtime > window_end:
            continue
        if best is None or mtime > best[0]:
            best = (mtime, photo.name)
    return best[1] if best else None


def find_disc_photo(photo_dir, devname: str, before: datetime.datetime,
                    max_age_seconds: int, grace_seconds: int = 5) -> Optional[str]:
    """
    Pick the photo the camera daemon took for ``devname`` just before a job started.

    :param photo_dir: folder the daemon writes into (``DISC_PHOTO_PATH``)
    :param devname: kernel name of the drive, ``sr0`` (a full ``/dev/sr0`` path is accepted)
    :param before: the job start time; photos newer than this (plus ``grace_seconds``) are ignored
    :param max_age_seconds: how far before ``before`` a photo may have been taken
    :param grace_seconds: tolerance for a photo written a moment after the job row was created
    :return: the photo filename (no directory) or ``None``
    """
    return _find_daemon_file(photo_dir, devname, before, max_age_seconds, grace_seconds, PHOTO_FILENAME_RE)


def read_barcode_file(path) -> Optional[str]:
    """The code stored in a ``.barcode`` file, or ``None`` when it is missing or implausible."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            code = handle.read().strip()
    except OSError:
        return None
    return code if BARCODE_RE.match(code) else None


def find_disc_barcode(photo_dir, devname: str, before: datetime.datetime,
                      max_age_seconds: int, grace_seconds: int = 5) -> Optional[Tuple[str, str]]:
    """
    Pick the barcode the daemon paired with ``devname``'s last tray close before a job started.

    Same window rules as :func:`find_disc_photo`.

    :return: ``(filename, code)`` or ``None``
    """
    filename = _find_daemon_file(photo_dir, devname, before, max_age_seconds, grace_seconds, BARCODE_FILENAME_RE)
    if not filename:
        return None
    code = read_barcode_file(os.path.join(photo_dir, filename))
    return (filename, code) if code else None


def consume_barcode_file(path) -> Optional[str]:
    """
    Mark a barcode file as used by renaming it to ``*.barcode.used``.

    The daemon's file stays in the window for DISC_PHOTO_MAX_AGE, so without this a disc
    ejected and swapped within that time would be given the previous case's code.

    :return: the new path, or ``None`` when the rename failed
    """
    used = f"{path}{BARCODE_USED_SUFFIX}"
    try:
        os.replace(path, used)
    except OSError:
        return None
    return used


def write_barcode_sidecar(final_directory, code) -> Optional[str]:
    """
    Write the scanned case barcode next to the finished rip as ``disc.barcode``: the code and a
    newline, nothing else, so it stays trivially machine readable. Keeping it with the rip means
    the code survives a lost database and is there even when the online lookup was rate limited
    or found nothing.

    :param final_directory: folder the finished rip lives in
    :param code: the UPC/EAN as scanned
    :return: the file written, or None when there was no plausible code to write
    """
    code = (code or "").strip()
    if not BARCODE_RE.match(code):
        return None
    os.makedirs(final_directory, exist_ok=True)
    destination = os.path.join(final_directory, BARCODE_COPY_FILENAME)
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write(code + "\n")
    return destination


def barcode_forms(code) -> List[str]:
    """
    The scanned code plus its other UPC-A / EAN-13 spelling.

    A 12 digit UPC-A is the same number as the 13 digit EAN-13 with a leading zero; scanners
    and databases such as MusicBrainz disagree on which one they store, so look up both.
    """
    code = str(code or "").strip()
    if not code:
        return []
    forms = [code]
    if code.isdigit():
        if len(code) == 12:
            forms.append("0" + code)
        elif len(code) == 13 and code.startswith("0"):
            forms.append(code[1:])
    return forms


def find_orphan_photos(photo_dir, referenced: Set[str], older_than_days: int,
                       now: Optional[datetime.datetime] = None) -> List[Path]:
    """
    Photos older than ``older_than_days`` that no job references, plus old barcode files.

    Empty-tray closes and ejects make the daemon write photos no job will ever claim, so the
    ripper prunes them on each run. Barcode files are copied into the job row when attached (and
    renamed ``*.used``), so every one of them is an orphan once it is old enough.
    """
    now = now or datetime.datetime.now()
    cutoff = (now - datetime.timedelta(days=older_than_days)).timestamp()
    referenced = {os.path.basename(r) for r in referenced if r}
    orphans = []
    candidates = list(_photo_files(photo_dir)) + list(_daemon_files(photo_dir, BARCODE_ANY_FILENAME_RE))
    for photo in candidates:
        if photo.name in referenced:
            continue
        try:
            if photo.stat().st_mtime < cutoff:
                orphans.append(photo)
        except OSError:
            continue
    return sorted(orphans)


def clean_ocr_text(text: Optional[str], max_candidates: int = 3) -> Tuple[List[str], Optional[str]]:
    """
    Turn raw tesseract output into title search candidates.

    Lines are cleaned of label boilerplate (format, studio, region text, URLs), lines that are
    mostly OCR noise or too short to be a safe search (``MIN_CANDIDATE_WORDS`` /
    ``MIN_CANDIDATE_LETTERS``) are dropped, and the survivors are ranked longest-first so the
    biggest text on the label, which is normally the title, is tried first. The most common four digit
    year on the label is returned as a year hint.

    :return: ``(candidates, year)`` where ``candidates`` may be empty and ``year`` may be ``None``
    """
    if not text:
        return [], None
    years: List[str] = []
    cleaned: List[str] = []
    for raw_line in text.splitlines():
        line = _URL_RE.sub(" ", raw_line)
        years.extend(_YEAR_RE.findall(line))
        if _COPYRIGHT_RE.search(line):
            continue
        line = _OCR_BOILERPLATE.sub(" ", line)
        line = _YEAR_RE.sub(" ", line)
        line = _KEEP_CHARS_RE.sub(" ", line)
        line = _SPACES_RE.sub(" ", line).strip(" -:.,!?'’&")
        alpha = sum(ch.isalpha() for ch in line)
        # A lone short word ("FOX", "NEW", a misread fragment) matches some title online and
        # would retitle the rip, so require two words or a reasonably long one
        if alpha < MIN_CANDIDATE_LETTERS and len(line.split()) < MIN_CANDIDATE_WORDS:
            continue
        # Mostly symbols or digits is OCR noise, not a title
        if alpha / max(len(line.replace(" ", "")), 1) < 0.6:
            continue
        if line.lower() not in (c.lower() for c in cleaned):
            cleaned.append(line)
    # Longest first; stable sort keeps label order for equal lengths
    cleaned.sort(key=lambda s: -sum(ch.isalpha() for ch in s))
    year = max(set(years), key=years.count) if years else None
    return cleaned[:max_candidates], year


_BRACKETS_RE = re.compile(r"[\(\[][^\)\]]*[\)\]]")
# Packaging words that UPC databases put in product titles but never belong in a title search
_UPC_BOILERPLATE = re.compile(
    r"\b("
    r"\d+\s*-?\s*disc\s+set|\d+\s*-?\s*discs?|combo\s+pack|steelbook|slipcover|digibook|"
    r"box\s*set|the\s+complete\s+(series|collection|first|second|third|\w+\s+season)|complete\s+series|"
    r"season\s+(one|two|three|four|five|six|seven|eight|nine|ten|\d+)|"
    r"brand\s+new|sealed|pre-?owned|factory\s+sealed|"
    r"english|french|spanish|german|italian|japanese|subtitled|dubbed|"
    r"disney(\s+pixar)?|pixar|marvel|lucasfilm"
    r")\b",
    re.IGNORECASE,
)
_TRAILING_FORMAT_RE = re.compile(
    r"\s*[-:,/]?\s*(dvd|blu[- ]?ray|4k\s*(uhd|ultra\s*hd)?|uhd|hd[- ]?dvd|vhs)(\s*\+\s*\w+)*\s*$", re.IGNORECASE)


def clean_upc_title(title: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Turn a UPC database product title into a title search and a year hint.

    Product titles look like ``"Inception (Blu-ray + DVD, 2010)"`` or ``"Pulp Fiction [DVD]"``:
    bracketed chunks carry the format and sometimes the year, the rest is the title with the odd
    marketing word. Years are harvested from everywhere, then the brackets and label boilerplate
    are stripped.

    :return: ``(title, year)``; ``title`` is ``None`` when nothing usable is left
    """
    if not title:
        return None, None
    text = unicodedata.normalize("NFKD", str(title))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    # Years in product titles sit in the brackets ("(DVD, 2010)"); a bare number in the title
    # itself ("Blade Runner 2049") is usually part of the title, so only a trailing one counts.
    years = [y for chunk in _BRACKETS_RE.findall(text) for y in _YEAR_RE.findall(chunk) if _plausible_year(y)]
    text = _BRACKETS_RE.sub(" ", text)
    text = _URL_RE.sub(" ", text)
    text = _TRAILING_FORMAT_RE.sub(" ", text)
    text = _UPC_BOILERPLATE.sub(" ", text)
    text = _OCR_BOILERPLATE.sub(" ", text)
    text = _SPACES_RE.sub(" ", text).strip()
    trailing = re.search(r"\s(19[0-9]{2}|20[0-9]{2})$", text)
    if trailing and _plausible_year(trailing.group(1)):
        if not years:
            years = [trailing.group(1)]
        text = text[:trailing.start()]
    text = _KEEP_CHARS_RE.sub(" ", text)
    text = _SPACES_RE.sub(" ", text).strip(" -:.,!?'\u2019&/")
    if sum(ch.isalpha() for ch in text) < 2:
        return None, None
    year = max(set(years), key=years.count) if years else None
    return text, year


def _plausible_year(year: str) -> bool:
    """A release year: not in the future."""
    try:
        return 1900 <= int(year) <= datetime.datetime.now().year + 1
    except (TypeError, ValueError):
        return False


def is_video_product(item: dict) -> bool:
    """
    True unless the UPC database says the product is clearly not a film or TV release.

    The category string looks like ``"Media > Movies & TV > DVDs"``; items without one are
    given the benefit of the doubt.
    """
    category = str(item.get("category") or "")
    if not category:
        return True
    return bool(re.search(r"(movie|tv|television|video|dvd|blu|media)", category, re.IGNORECASE))


def parse_upc_response(payload: dict) -> List[dict]:
    """
    Reduce an upcitemdb lookup response to ``[{"title": ..., "year": ..., "raw": ...}, ...]``.

    Only items that look like video products are kept; the first result is the best match.
    """
    if not isinstance(payload, dict) or str(payload.get("code", "")).upper() not in ("OK", ""):
        return []
    results = []
    for item in payload.get("items") or []:
        if not isinstance(item, dict) or not is_video_product(item):
            continue
        title, year = clean_upc_title(item.get("title"))
        if not title:
            continue
        results.append({"title": title, "year": year, "raw": str(item.get("title") or "")})
    return results


def lookup_upc(code: str, timeout: int = 15, url: str = UPC_LOOKUP_URL, user_agent: str = "arm") -> List[dict]:
    """
    Look a UPC/EAN up on upcitemdb.com (free trial endpoint, no key, about 100 calls a day).

    :return: cleaned candidates from :func:`parse_upc_response`; empty on any failure
    """
    import requests  # pylint: disable=import-outside-toplevel  # keeps this module importable without it

    if not code or not BARCODE_RE.match(str(code)):
        return []
    try:
        response = requests.get(url, params={"upc": str(code)}, timeout=timeout,
                                headers={"User-Agent": user_agent, "Accept": "application/json"})
    except requests.RequestException as error:
        logging.warning(f"UPC lookup for {code} failed: {error}")
        return []
    if response.status_code == 429:
        logging.warning("UPC lookup rate limit reached (upcitemdb trial allows about 100 lookups a day)")
        return []
    if response.status_code == 404:
        logging.info(f"UPC {code} is not in the upcitemdb database")
        return []
    if response.status_code != 200:
        logging.warning(f"UPC lookup for {code} returned HTTP {response.status_code}")
        return []
    try:
        payload = response.json()
    except ValueError:
        logging.warning(f"UPC lookup for {code} returned something that is not JSON")
        return []
    return parse_upc_response(payload)
