#!/usr/bin/env python3
"""
Pure helpers for the disc camera feature.

The camera daemon (arm/camera) writes ``<devname>_<YYYYmmdd-HHMMSS>.jpg`` files into
``DISC_PHOTO_PATH`` whenever a drive tray closes. These functions pick the right photo for a
job, find stale photos and turn OCR output into title search candidates.

This module deliberately has no ARM, Flask or database imports so it can be unit tested on
its own. The database aware wrappers live in ``arm.ripper.utils``.
"""
import datetime
import os
import re
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

PHOTO_FILENAME_RE = re.compile(r"^(?P<dev>sr\d+)_(?P<stamp>\d{8}-\d{6})\.jpe?g$", re.IGNORECASE)
PHOTO_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"
COPY_FILENAME = "disc.jpg"

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


def _photo_files(photo_dir) -> Iterable[Path]:
    folder = Path(photo_dir)
    if not folder.is_dir():
        return []
    return (p for p in folder.iterdir() if p.is_file() and PHOTO_FILENAME_RE.match(p.name))


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
    devname = os.path.basename(str(devname)).lower()
    if not devname:
        return None
    window_start = (before - datetime.timedelta(seconds=max_age_seconds)).timestamp()
    window_end = (before + datetime.timedelta(seconds=grace_seconds)).timestamp()
    best: Optional[Tuple[float, str]] = None
    for photo in _photo_files(photo_dir):
        if photo_devname(photo.name) != devname:
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


def find_orphan_photos(photo_dir, referenced: Set[str], older_than_days: int,
                       now: Optional[datetime.datetime] = None) -> List[Path]:
    """
    Photos older than ``older_than_days`` that no job references.

    Empty-tray closes and ejects make the daemon write photos no job will ever claim, so the
    ripper prunes them on each run.
    """
    now = now or datetime.datetime.now()
    cutoff = (now - datetime.timedelta(days=older_than_days)).timestamp()
    referenced = {os.path.basename(r) for r in referenced if r}
    orphans = []
    for photo in _photo_files(photo_dir):
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
