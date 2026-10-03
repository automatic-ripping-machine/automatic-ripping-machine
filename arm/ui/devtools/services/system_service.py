"""
Devtools service - host system information.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import psutil

from config import config as cfg

_TOOLS = {
    "handbrake": "HandBrakeCLI",
    "makemkv": "makemkvcon",
    "ffmpeg": "ffmpeg",
    "abcde": "abcde",
    "python": "python3",
}


def get_tool_versions() -> dict[str, Any]:
    """
    Report the installed version of each ARM media tool.

    Returns:
        dict: tool name to first version output line
    """
    versions = {}
    for name, binary in _TOOLS.items():
        try:
            result = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=15)
            output = (result.stdout or result.stderr).strip().splitlines()
            versions[name] = output[0] if output else "unknown"
        except FileNotFoundError:
            versions[name] = "not installed"
        except Exception as error:
            versions[name] = f"error: {error}"
    return {"tools": versions}


def check_disk_space() -> dict[str, Any]:
    """
    Report free space on the configured media paths.

    Returns:
        dict: per-path usage, or the error when unavailable
    """
    paths = {}
    for label in ("RAW_PATH", "TRANSCODE_PATH", "COMPLETED_PATH", "LOGPATH"):
        path = str(cfg.arm_config.get(label, "")).strip()
        if not path:
            continue
        try:
            usage = shutil.disk_usage(path)
            paths[label] = {
                "path": path,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent_used": round(usage.used / usage.total * 100, 1),
            }
        except OSError as error:
            paths[label] = {"path": path, "error": str(error)}
    return {"paths": paths}


def get_process_list() -> list[dict[str, Any]]:
    """
    List running ARM-related processes.

    Returns:
        list: pid, name, cmdline and create_time per process
    """
    keywords = ("arm", "makemkv", "handbrake", "ffmpeg", "abcde")
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            cmdline = " ".join(proc.info["cmdline"] or [])
            name = proc.info["name"] or ""
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if any(keyword in cmdline.lower() or keyword in name.lower() for keyword in keywords):
            processes.append({
                "pid": proc.info["pid"],
                "name": name,
                "cmdline": cmdline[:200],
                "create_time": proc.info["create_time"],
            })
    return processes


def get_config_paths() -> dict[str, Any]:
    """
    Check existence of the paths ARM relies on.

    Returns:
        dict: path label to path and exists flag
    """
    paths = {
        "config": "/arm/config/arm.yaml",
        "install": str(cfg.arm_config.get("INSTALLPATH", "/opt/arm/")).rstrip("/"),
        "logs": str(cfg.arm_config.get("LOGPATH", "")),
    }
    return {
        "paths": {
            label: {"path": path, "exists": Path(path).expanduser().exists()}
            for label, path in paths.items()
            if path
        }
    }
