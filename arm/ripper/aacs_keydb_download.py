#!/usr/bin/env python3

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

import arm.config.config as cfg

KEYDB_CFG_TMP = "KEYDB.cfg.tmp"


def ensure_libaacs_installed() -> None:
    """Warn if libaacs does not appear to be installed (best-effort check)."""
    try:
        result = subprocess.run(
            ["ldconfig", "--print-cache"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
        )
    except FileNotFoundError:
        return

    if "libaacs" not in result.stdout:
        print("[!] The library libaacs seem to not be install on your system.")
        print("\t-> Check with your package manager to install it.")


def resolve_target_directory() -> Path:
    """Resolve the target directory for KEYDB.cfg."""
    uid = os.getuid() if hasattr(os, "getuid") else None
    if uid is not None and uid != 0:
        home = Path(os.path.expanduser("~"))
        return home / ".config" / "aacs"
    return Path("/etc/xdg/aacs")


def ensure_directory(path: Path) -> None:
    """Ensure the target directory exists."""
    if not path.is_dir():
        print(f'[!] Directory "{path}" is missing!')
        print(f'[+] Creating "{path}"…')
        path.mkdir(parents=True, exist_ok=True)


def fetch_page(url: str) -> str:
    """Fetch page content from URL."""
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_last_update(page_content: str) -> str | None:
    """Extract last update date string from page content."""
    match = re.search(r"LastUpdate:\s*([^<\n\r]+)", page_content)
    if not match:
        return None
    return match.group(1).strip()


def parse_links(page_content: str) -> list[str]:
    """Extract fv_download links from page content."""
    return re.findall(r'http://[^"]*fv_download\.php\?lang=[^"]*', page_content)


def parse_date_to_timestamp(date_str: str) -> int:
    """Convert date string (YYYY-MM-DD) to Unix timestamp."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.timestamp())


def load_local_update(target: Path) -> str:
    """Load local last update date or default to epoch."""
    last_update_file = target / "lastupdate.txt"
    if last_update_file.is_file():
        content = last_update_file.read_text(encoding="utf-8").strip()
        if content:
            print(f"[*] The last update of the local database is {content}.")
            return content
    return "1970-01-01"


def append_keys_from_links(links: list[str], target: Path) -> None:
    """Download and merge keydb.cfg from all provided HTML-discovered links."""
    if not links:
        return

    print("[+] Get the list of zip file links from the website…")
    tempdir = Path(tempfile.mkdtemp())
    try:
        for link in links:
            print(f"[+] Downloading the file\n\t-> {link}…")
            zip_path = tempdir / "keydb.zip"
            with urllib.request.urlopen(link) as response, zip_path.open("wb") as out:
                shutil.copyfileobj(response, out)

            print(f"[+] Unzip the file\n\t-> {zip_path}…")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tempdir)

            keydb_cfg = tempdir / "keydb.cfg"
            if keydb_cfg.is_file():
                print(
                    "[+] Add the content of the KEYDB file to the local KEYDB.cfg…"
                )
                with keydb_cfg.open("r", encoding="utf-8", errors="replace") as src, (
                    target / KEYDB_CFG_TMP
                ).open("a", encoding="utf-8") as dst:
                    shutil.copyfileobj(src, dst)

            for child in tempdir.iterdir():
                if child.is_file():
                    try:
                        child.unlink()
                    except OSError:
                        pass
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def append_keys_from_sources(sources: Iterable[str], target: Path) -> None:
    """Download or read KEYDB data from direct sources (URLs or local paths)."""
    sources_list = [s for s in sources if s]
    if not sources_list:
        return

    tempdir = Path(tempfile.mkdtemp())
    try:
        for source in sources_list:
            is_url = source.startswith(("http://", "https://"))
            if is_url:
                print(f"[+] Downloading additional source\n\t-> {source}…")
                tmp_path = tempdir / "extra_source"
                with urllib.request.urlopen(source) as response, tmp_path.open(
                    "wb"
                ) as out:
                    shutil.copyfileobj(response, out)
                candidate_path = tmp_path
            else:
                candidate_path = Path(source)
                if not candidate_path.is_file():
                    print(f"[!] Additional source does not exist, skipping: {source}")
                    continue

            if zipfile.is_zipfile(candidate_path):
                print(f"[+] Unzip the file\n\t-> {candidate_path}…")
                with zipfile.ZipFile(candidate_path, "r") as zf:
                    zf.extractall(tempdir)
                keydb_cfg = tempdir / "keydb.cfg"
                if not keydb_cfg.is_file():
                    print(
                        f"[!] No keydb.cfg found in archive from source, skipping: {source}"
                    )
                    continue
                print(
                    "[+] Add the content of the KEYDB file to the local KEYDB.cfg…"
                )
                with keydb_cfg.open("r", encoding="utf-8", errors="replace") as src, (
                    target / KEYDB_CFG_TMP
                ).open("a", encoding="utf-8") as dst:
                    shutil.copyfileobj(src, dst)
            else:
                print(f"[+] Treating {candidate_path} as a plain KEYDB.cfg source…")
                with candidate_path.open(
                    "r", encoding="utf-8", errors="replace"
                ) as src, (target / KEYDB_CFG_TMP).open(
                    "a", encoding="utf-8"
                ) as dst:
                    shutil.copyfileobj(src, dst)
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def get_primary_database_url() -> str:
    """Get the primary AACS database URL from config or default."""
    value = cfg.arm_config.get("AACS_KEYDB_PRIMARY_URL")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "http://fvonline-db.bplaced.net/"


def get_aacs_keydb_enabled() -> bool:
    """Return True if AACS KEYDB auto-update is enabled in config."""
    value = cfg.arm_config.get("AACS_KEYDB_ENABLED", False)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return False


def get_min_refetch_hours() -> int:
    """Return minimum hours between fetch attempts from config."""
    value = cfg.arm_config.get("AACS_KEYDB_MIN_REFETCH_HOURS", 24)
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return max(0, int(value.strip()))
    return 24


def _last_fetch_file(target: Path) -> Path:
    """Path to file storing last successful KEYDB fetch timestamp."""
    return target / "last_keydb_fetch.txt"


def _is_within_refetch_period(target: Path, min_hours: int) -> bool:
    """Return True if we fetched within the last min_hours (skip this run)."""
    if min_hours <= 0:
        return False
    path = _last_fetch_file(target)
    if not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8").strip()
        last_ts = float(content)
    except (ValueError, OSError):
        return False
    return (time.time() - last_ts) < (min_hours * 3600)


def _write_last_fetch_time(target: Path) -> None:
    """Record current time as last successful KEYDB fetch."""
    try:
        _last_fetch_file(target).write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass


def get_extra_sources_from_config() -> list[str]:
    """Get additional KEYDB sources from config (comma-separated string)."""
    raw_value = cfg.arm_config.get("AACS_KEYDB_EXTRA_SOURCES", "")
    if not isinstance(raw_value, str):
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def try_download_keydb() -> int:

    if not get_aacs_keydb_enabled():
        return 0

    ensure_libaacs_installed()

    target = resolve_target_directory()
    ensure_directory(target)

    print(f"[*] We will use the directory:\n\t-> {target}")

    min_refetch_hours = get_min_refetch_hours()
    if _is_within_refetch_period(target, min_refetch_hours):
        print("[*] Skipping KEYDB update (within minimum refetch period).")
        return 0

    extra_sources = get_extra_sources_from_config()

    if extra_sources:
        print("[*] Using configured AACS KEYDB sources from arm.yaml; skipping primary site.")
        append_keys_from_sources(extra_sources, target)
        keydb_cfg = target / "KEYDB.cfg"
        if keydb_cfg.is_file():
            print("[+] Delete the actual KEYDB.cfg…")
        print("[+] Rename the temporary KEYDB.cfg file…")
        tmp_keydb = target / KEYDB_CFG_TMP
        if tmp_keydb.is_file():
            tmp_keydb.replace(keydb_cfg)
            _write_last_fetch_time(target)
        print("[*] All is done!")
        return 0

    database_website = get_primary_database_url()

    print(
        f"[+] Get the database last update on the website:\n\t-> {database_website}"
    )

    try:
        page_content = fetch_page(database_website)
    except Exception as exc:  # pragma: no cover - network failure path
        print(
            f"[!] Unable to reach the primary database website ({database_website}): {exc}"
        )
        return 1

    last_update = parse_last_update(page_content)
    if not last_update:
        print("[!] Unable to determine last update from the website.")
        return 1

    print(f"[*] The last update of the Web database is {last_update}.")

    local_update = load_local_update(target)

    last_update_unix = parse_date_to_timestamp(last_update)
    local_update_unix = parse_date_to_timestamp(local_update)

    if last_update_unix > local_update_unix:
        links = parse_links(page_content)
        append_keys_from_links(links, target)

        keydb_cfg = target / "KEYDB.cfg"
        if keydb_cfg.is_file():
            print("[+] Delete the actual KEYDB.cfg…")

        print("[+] Rename the temporary KEYDB.cfg file…")
        tmp_keydb = target / KEYDB_CFG_TMP
        if tmp_keydb.is_file():
            tmp_keydb.replace(keydb_cfg)
            _write_last_fetch_time(target)
    else:
        print("[*] Local database is up to date.")

    print("[*] All is done!")
    return 0


if __name__ == "__main__":
    sys.exit(try_download_keydb())
