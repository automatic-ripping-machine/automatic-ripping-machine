"""Run a user-configured bash script with job context as env vars.

The script receives:
- Title as ``$1`` (first positional)
- Body as ``$2`` (second positional)
- All ``env_vars`` from the caller (typically ``ARM_*`` derived from
  the event payload)

Non-zero exit, missing file, and timeout are all terminal failures —
re-running won't fix any of them. The 30-second default timeout
prevents a hung script from pinning a dispatcher worker slot.
"""
import logging
import os
import subprocess

log = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 30


def send_bash(
    *,
    script_path: str,
    title: str,
    body: str,
    env_vars: dict[str, str],
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
) -> tuple[bool, str | None]:
    """Run the script with title/body as args and env_vars as environment.

    :returns: ``(True, None)`` on zero-exit success, ``(False, error)``
        otherwise. All failures are terminal — never retry a bash
        script that returned non-zero, timed out, or doesn't exist.
    """
    if not os.path.isfile(script_path):
        return False, f"bash script not found: {script_path} terminal=true"
    if not os.access(script_path, os.X_OK):
        return False, f"bash script not executable: {script_path} terminal=true"

    env = os.environ.copy()
    env.update(env_vars)

    try:
        result = subprocess.run(  # NOSONAR python:S4721,python:S6350 - argv-list invocation (no shell=True); script_path is an operator-configured channel, which is privileged admin functionality by design
            ["/usr/bin/env", "bash", script_path, title, body],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return False, (
            f"bash script timeout after {timeout_seconds}s: "
            f"{script_path} terminal=true"
        )

    if result.returncode == 0:
        return True, None

    return False, (
        f"bash script exit code {result.returncode}: "
        f"{(result.stderr or '')[:200]} terminal=true"
    )
