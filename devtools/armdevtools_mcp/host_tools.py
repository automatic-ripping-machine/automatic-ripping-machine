"""
Devtools MCP host-side tools (run on the dev machine, not inside ARM).

These supersede the legacy armdocker/armgit CLI for agent use; the CLI
scripts remain available for humans.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from armdevtools_mcp.telemetry import _MAX_ERROR_CHARS, _MAX_RESULT_CHARS, failure


def repo_root() -> Path:
    """ARM checkout root in a source checkout; cwd when installed as a package."""
    candidate = Path(__file__).resolve().parent.parent.parent
    return candidate if (candidate / "docker-compose.yml").is_file() else Path.cwd()


REPO_ROOT = repo_root()


def _services_arg(arguments: dict[str, Any]) -> list[str]:
    """Normalise the services argument: a string or list, defaulting to arm-ui."""
    services = arguments.get("services") or ["arm-ui"]
    return [services] if isinstance(services, str) else services


def _compose_command(dev_override: bool | None = None) -> list[str]:
    """Base `docker compose` command with the checkout's -f file flags."""
    command = ["docker", "compose"]
    for file in _compose_files(dev_override):
        command += ["-f", file]
    return command


def _compose_files(dev_override: bool | None = None) -> list[str]:
    """
    Return the compose files for the checkout.

    Args:
        dev_override: force the dev override on/off; when None, use it only
            when docker-compose.dev.yml exists next to the base file

    Returns:
        list: docker-compose.yml plus the dev override when in use
    """
    base = REPO_ROOT / "docker-compose.yml"
    dev = REPO_ROOT / "docker-compose.dev.yml"
    files = [str(base)]
    if dev_override is None:
        dev_override = dev.is_file()
    if dev_override and dev.is_file():
        files.append(str(dev))
    return files


def _run_host_command(command: list[str], timeout: int = 900) -> dict[str, Any]:
    """Run a command on the dev machine and return its result."""
    start = time.time()
    try:
        result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as error:
        return failure(f"{command[0]} not found on this machine: {error}")
    except subprocess.TimeoutExpired:
        return failure(f"timed out after {timeout}s")
    return {
        "command": " ".join(command),
        "returncode": result.returncode,
        "stdout": (result.stdout or "")[-_MAX_RESULT_CHARS:],
        "stderr": (result.stderr or "")[-_MAX_ERROR_CHARS:],
        "duration": round(time.time() - start, 1),
        "success": result.returncode == 0,
    }


def handle_docker_compose_build(arguments: dict[str, Any]) -> dict[str, Any]:
    """Build and restart the ARM stack (default: the arm-ui service)."""
    services = _services_arg(arguments)
    files = _compose_files(arguments.get("dev_override"))
    command = _compose_command(arguments.get("dev_override"))
    build = _run_host_command(command + ["build", *services], timeout=1800)
    if not build.get("success"):
        build["note"] = "build failed; stack not restarted"
        return build
    up = _run_host_command(command + ["up", "-d", *services], timeout=300)
    up["build"] = {"returncode": build["returncode"], "duration": build["duration"]}
    up["services"] = services
    up["compose_files"] = [Path(file).name for file in files]
    return up


def handle_docker_compose_restart(arguments: dict[str, Any]) -> dict[str, Any]:
    """Restart services in the ARM stack (default: arm-ui)."""
    services = _services_arg(arguments)
    files = _compose_files(arguments.get("dev_override"))
    command = _compose_command(arguments.get("dev_override"))
    result = _run_host_command(command + ["restart", *services], timeout=300)
    result["services"] = services
    result["compose_files"] = [Path(file).name for file in files]
    return result


def handle_run_pr_checks(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Run the checks that used to be armgit.pr_update(): git submodule update,
    flake8 and the test suite (through the container, against arm-db-test).
    """
    results = {}
    # 1. Bring the submodules up to date
    results["submodule_update"] = _run_host_command(["git", "submodule", "update", "--remote"], timeout=300)
    # 2. Lint via the UI container (has flake8 and the live source mounts)
    command = _compose_command(arguments.get("dev_override"))
    lint_command = command + ["run", "--rm", "-w", "/opt/arm", "arm-ui",
                              "python3", "-m", "flake8", "arm", "test_ui", "test_ripper", "devtools"]
    results["flake8"] = _run_host_command(lint_command, timeout=900)
    # 3. Test via the UI container against arm-db-test
    test_command = command + ["run", "--rm", "-w", "/opt/arm",
                              "-e", "FLASK_ENV=testing", "-e", "MYSQL_IP=arm-db-test",
                              "arm-ui", "python3", "-m", "pytest", "test_ui", "--maxfail=1", "-q"]
    results["pytest"] = _run_host_command(test_command, timeout=900)
    results["success"] = all(item.get("success", False) for item in results.values())
    return results

