"""Folder structure detection and metadata extraction for folder imports."""
import logging
import os
import re

import xmltodict

logger = logging.getLogger(__name__)


def validate_ingress_path(path: str, ingress_root: str) -> None:
    """Validate that path is under ingress_root after resolving symlinks."""
    real_path = os.path.realpath(path)
    real_root = os.path.realpath(ingress_root)
    if not real_path.startswith(real_root + os.sep) and real_path != real_root:
        raise ValueError(f"Path {path} resolves outside ingress root")
    if not os.path.exists(real_path):
        raise FileNotFoundError(f"Path does not exist: {path}")


def detect_disc_type(folder_path: str) -> str:
    """Detect disc type from folder structure. Returns 'bluray4k', 'bluray', or 'dvd'."""
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    bdmv = os.path.join(folder_path, "BDMV")
    video_ts = os.path.join(folder_path, "VIDEO_TS")
    if os.path.isdir(bdmv):
        uhd_marker = os.path.join(folder_path, "CERTIFICATE", "id.bdmv")
        if os.path.isfile(uhd_marker):
            return "bluray4k"
        return "bluray"
    if os.path.isdir(video_ts):
        return "dvd"
    raise ValueError(f"No disc structure (BDMV or VIDEO_TS) found in {folder_path}")


def extract_metadata(folder_path: str, disc_type: str) -> dict:
    """Extract metadata from a disc folder."""
    label = _extract_label(folder_path, disc_type)
    title_suggestion, year_suggestion = _parse_title_year(label, folder_path)
    folder_size = _calculate_folder_size(folder_path)
    stream_count = _count_streams(folder_path, disc_type)
    return {
        "label": label,
        "title_suggestion": title_suggestion,
        "year_suggestion": year_suggestion,
        "folder_size_bytes": folder_size,
        "stream_count": stream_count,
    }


def scan_folder(folder_path: str, ingress_root: str) -> dict:
    """Top-level scan: validate, detect type, extract metadata."""
    validate_ingress_path(folder_path, ingress_root)
    disc_type = detect_disc_type(folder_path)
    metadata = extract_metadata(folder_path, disc_type)
    return {"disc_type": disc_type, **metadata}


def _extract_label(folder_path: str, disc_type: str) -> str:
    if disc_type in ("bluray", "bluray4k"):
        xml_label = _label_from_bluray_xml(folder_path)
        if xml_label:
            return xml_label
    return os.path.basename(folder_path)


def _label_from_bluray_xml(folder_path: str) -> str | None:
    xml_path = os.path.join(folder_path, "BDMV", "META", "DL", "bdmt_eng.xml")
    if not os.path.isfile(xml_path):
        return None
    try:
        with open(xml_path, "r", encoding="utf-8") as f:
            doc = xmltodict.parse(f.read())
        title = doc["disclib"]["di:discinfo"]["di:title"]["di:name"]
        return str(title).strip()
    except Exception:
        logger.warning("Failed to parse bdmt_eng.xml at %s", xml_path, exc_info=True)
        return None


def _parse_title_year(label: str, folder_path: str) -> tuple[str, str | None]:
    folder_name = os.path.basename(folder_path)
    match = re.search(r"^(.+?)\s*\((\d{4})\)", folder_name)
    if match:
        return match.group(1).strip(), match.group(2)
    match = re.search(r"^(.+?)\s+(\d{4})\b", folder_name)
    if match:
        return match.group(1).strip(), match.group(2)
    clean = re.sub(r"[_.]", " ", label).strip()
    return clean, None


def _calculate_folder_size(folder_path: str) -> int:
    total = 0
    for dirpath, _, filenames in os.walk(folder_path):
        for f in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total


def _count_streams(folder_path: str, disc_type: str) -> int:
    if disc_type in ("bluray", "bluray4k"):
        stream_dir = os.path.join(folder_path, "BDMV", "STREAM")
    elif disc_type == "dvd":
        stream_dir = os.path.join(folder_path, "VIDEO_TS")
    else:
        return 0
    if not os.path.isdir(stream_dir):
        return 0
    return len([f for f in os.listdir(stream_dir) if os.path.isfile(os.path.join(stream_dir, f))])
