"""
Devtools service - running the v3 dev loop: tests, lint and coverage.

Tests run against the MySQL test database (arm-db-test), matching v3's
test_ui conftest, which refuses to run against anything but arm_testing.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from config import config as cfg

# Environment the test suite requires (test_ui/conftest.py enforces arm_testing)
_TEST_ENV = {"FLASK_ENV": "testing", "MYSQL_IP": "arm-db-test"}

_INTEGRITY_MANIFEST = Path(cfg.arm_config.get("LOGPATH", "/arm/logs/")).expanduser() / "devtools" / "test_integrity.json"

_TEST_ROOTS = ("test_ui", "test_ripper")


def _run_subprocess(command: list[str], timeout: int = 600) -> dict[str, Any]:
    """
    Run a command in the ARM install directory, capturing output.

    Args:
        command: argv list
        timeout: seconds before the command is killed

    Returns:
        dict: returncode, stdout tail, stderr tail and duration
    """
    import os

    cwd = str(cfg.arm_config.get("INSTALLPATH", "/opt/arm/")).rstrip("/")
    start = time.time()
    try:
        result = subprocess.run(
            command, cwd=cwd, env={**os.environ, **_TEST_ENV},
            capture_output=True, text=True, timeout=timeout,
        )
        returncode = result.returncode
        stdout = result.stdout or ""
        stderr = result.stderr or ""
    except subprocess.TimeoutExpired as error:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"timed out after {timeout}s: {error}",
            "duration": round(time.time() - start, 1),
            "error": f"timed out after {timeout}s",
        }
    except FileNotFoundError as error:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"No such file or directory: {error.filename}",
            "duration": round(time.time() - start, 1),
            "error": f"binary not found: {error.filename}",
        }
    return {
        "returncode": returncode,
        "stdout": stdout[-20000:],
        "stderr": stderr[-5000:],
        "duration": round(time.time() - start, 1),
        "success": returncode == 0,
    }


def _install_path() -> str:
    return str(cfg.arm_config.get("INSTALLPATH", "/opt/arm/")).rstrip("/")


def run_tests(paths: list[str] | None = None, verbose: bool = True, maxfail: int = 1) -> dict[str, Any]:
    """
    Run the pytest suite (defaults to test_ui) against arm-db-test.

    Args:
        paths: test files or dirs relative to the install path; default ["test_ui"]
        verbose: include per-test output
        maxfail: stop after this many failures

    Returns:
        dict: test run result
    """
    paths = paths or ["test_ui"]
    command = ["python3", "-m", "pytest", *paths, f"--maxfail={maxfail}"]
    if verbose:
        command.append("-v")
    result = _run_subprocess(command)
    result["command"] = " ".join(command)
    result["paths"] = paths
    return result


def find_tests_for_module(module_name: str) -> dict[str, Any]:
    """
    Find the test files covering a module.

    Heuristic: test files whose name contains the module's leaf name, plus
    a curated map for the main modules.

    Args:
        module_name: e.g. ui.devtools.routes, models.job

    Returns:
        dict: matching test files
    """
    curated = {
        "devtools": ["test_ui/test_bp_devtools.py"],
        "ui.devtools.routes": ["test_ui/test_bp_devtools.py"],
        "ui.devtools.services": ["test_ui/test_bp_devtools.py"],
        "arm.ui.devtools": ["test_ui/test_bp_devtools.py"],
        "models.job": ["test_ui/test_model_job.py"],
        "models.config": ["test_ui/test_model_config.py"],
        "models.track": ["test_ui/test_model_job.py"],
        "models.user": ["test_ui/test_model_user.py"],
        "models.notifications": ["test_ui/test_model_notifications.py"],
        "models.system_drives": ["test_ui/test_model_system_drives.py"],
        "models.system_info": ["test_ui/test_model_system_info.py"],
        "models.ui_settings": ["test_ui/test_model_ui_settings.py"],
    }
    if module_name in curated:
        return {"module": module_name, "tests": curated[module_name]}
    leaf = Path(str(module_name)).name
    if leaf in curated:
        return {"module": module_name, "tests": curated[leaf]}
    # Content-search candidates: the dotted module and its two-segment prefix
    parts = [p for p in module_name.split(".") if p]
    candidates = [".".join(parts[:i]) for i in range(len(parts), 1, -1)]
    matches = []
    install = Path(_install_path())
    for root in _TEST_ROOTS:
        test_root = install / root
        if not test_root.is_dir():
            continue
        for test_file in sorted(test_root.glob("test_*.py")):
            if leaf in test_file.name:
                matches.append(f"{root}/{test_file.name}")
                continue
            try:
                content = test_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(c in content for c in candidates):
                matches.append(f"{root}/{test_file.name}")
    return {"module": module_name, "tests": sorted(set(matches))}


def run_tests_for_file(test_path: str, verbose: bool = True) -> dict[str, Any]:
    """
    Run the test file covering a module or one explicit test file.

    Args:
        test_path: e.g. test_ui/test_bp_devtools.py
        verbose: include per-test output

    Returns:
        dict: test run result
    """
    if not test_path.startswith(tuple(f"{root}/" for root in _TEST_ROOTS)):
        raise ValueError(f"test_path must be under {_TEST_ROOTS}, got '{test_path}'")
    return run_tests(paths=[test_path], verbose=verbose, maxfail=1)


def run_linter(paths: list[str] | None = None) -> dict[str, Any]:
    """
    Run flake8 against ARM code with v3's setup.cfg configuration.

    Args:
        paths: files or dirs to lint; default ["arm", "test_ui", "test_ripper", "devtools"]

    Returns:
        dict: lint result
    """
    paths = paths or ["arm", "test_ui", "test_ripper", "devtools"]
    command = ["python3", "-m", "flake8", *paths]
    result = _run_subprocess(command, timeout=300)
    result["command"] = " ".join(command)
    if "No module named flake8" in result.get("stderr", ""):
        result["error"] = "flake8 not installed - run: pip3 install flake8"
    return result


def run_coverage(paths: list[str] | None = None) -> dict[str, Any]:
    """
    Run pytest with coverage over the UI package.

    Args:
        paths: test files or dirs; default ["test_ui"]

    Returns:
        dict: coverage run result
    """
    paths = paths or ["test_ui"]
    # The packages are flat in this checkout (ui, models, config), so the
    # coverage target is the `ui` package, not `arm.ui`.
    command = ["python3", "-m", "pytest", *paths, "--cov=ui", "--cov-report=term-missing"]
    result = _run_subprocess(command, timeout=600)
    result["command"] = " ".join(command)
    stderr = result.get("stderr", "")
    if (result["returncode"] == -1 and "No module named" in stderr) or \
            "unrecognized arguments: --cov" in stderr:
        result["error"] = "pytest-cov not installed - run: pip3 install pytest-cov"
    return result


def check_test_integrity() -> dict[str, Any]:
    """
    Verify the test suite has not been modified since the last snapshot.

    The manifest is a sha256 per test file, stored under the log path so it
    survives container restarts.

    Returns:
        dict: changed/new/removed test files
    """
    current = {}
    install = Path(_install_path())
    for root in _TEST_ROOTS:
        test_root = install / root
        if not test_root.is_dir():
            continue
        for test_file in sorted(test_root.glob("test_*.py")):
            relative = f"{root}/{test_file.name}"
            current[relative] = hashlib.sha256(test_file.read_bytes()).hexdigest()

    previous = {}
    if _INTEGRITY_MANIFEST.is_file():
        previous = json.loads(_INTEGRITY_MANIFEST.read_text(encoding="utf-8"))

    changed = [path for path in current if path in previous and previous[path] != current[path]]
    added = [path for path in current if path not in previous]
    removed = [path for path in previous if path not in current]

    _INTEGRITY_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _INTEGRITY_MANIFEST.write_text(json.dumps(current, indent=2), encoding="utf-8")

    return {
        "files": len(current),
        "changed": changed,
        "added": added,
        "removed": removed,
        "clean": not (changed or added or removed),
        "manifest": str(_INTEGRITY_MANIFEST),
    }
