"""ISO file import scanning + filename metadata extraction.

Scope is intentionally narrow: this module only does cheap filesystem-side
work - validate the path is a real .iso under INGRESS_PATH and parse the
filename for a title/year suggestion. Disc-type detection, stream count
and volume label come from MakeMKV's info pass (`prescan_iso_disc_type`
in arm.ripper.makemkv) so that ISOs use the same identification path that
physical discs and folder imports already share.
"""
import logging
import os
import re

from arm.common.path_safety import safe_join

log = logging.getLogger(__name__)


def validate_iso_path(path: str, ingress_root: str) -> str:
    """Validate that `path` is an .iso file under `ingress_root`.

    Confines the user-controlled `path` to `ingress_root` via
    :func:`arm.common.path_safety.safe_join` and returns the validated
    absolute path. Callers should use the returned value for filesystem
    access.

    Raises:
        ValueError: extension is not .iso, or path resolves outside ingress.
        FileNotFoundError: path does not exist.
    """
    if not path.lower().endswith(".iso"):
        raise ValueError(f"Not an ISO file (expected .iso extension): {path}")
    # Route the user input through the confinement helper. safe_join raises
    # ValueError when `path` resolves outside the trusted ingress root.
    real_path = safe_join(ingress_root, path)
    if not os.path.isfile(real_path):
        raise FileNotFoundError(f"ISO file does not exist: {path}")
    return real_path


def extract_metadata(iso_path: str) -> dict:
    """Extract size + filename-derived label/title/year from an ISO.

    Disc type and stream count are NOT extracted here - those come from
    MakeMKV's prescan info pass.
    """
    stat = os.stat(iso_path)
    filename = os.path.basename(iso_path)
    label = re.sub(r"\.iso$", "", filename, flags=re.IGNORECASE)
    title, year = _parse_title_year(label)
    return {
        "iso_size": stat.st_size,
        "label": label,
        "title_suggestion": title,
        "year_suggestion": year,
    }


def _parse_title_year(label: str) -> tuple[str, str | None]:
    """Pull a title and optional year out of an ISO basename (sans extension).

    Mirrors arm.ripper.folder_scan._parse_title_year so folder + ISO imports
    surface the same wizard suggestions for equivalent labels.
    """
    # "Title (2024)" - split on the literal parenthesised year.
    paren_idx = label.rfind("(")
    if paren_idx > 0:
        maybe_year = label[paren_idx + 1: paren_idx + 5]
        if maybe_year.isdigit() and len(maybe_year) == 4:
            return label[:paren_idx].strip(), maybe_year

    # "Title 2024" - find last standalone 4-digit year.
    parts = label.split()
    for i in range(len(parts) - 1, -1, -1):
        if len(parts[i]) == 4 and parts[i].isdigit() and int(parts[i]) >= 1900:
            title = " ".join(parts[:i]).strip()
            if title:
                return title, parts[i]

    clean = re.sub(r"[_.]", " ", label).strip()
    return clean, None
