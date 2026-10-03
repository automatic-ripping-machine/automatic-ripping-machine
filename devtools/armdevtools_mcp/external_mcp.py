"""
External MCP server federation for devapi_mcp (host-side).

Spawns configured external MCP servers (jcodemunch, jdocmunch, git, pyright)
over stdio and exposes their tools through the devapi MCP via generic
passthrough. Integration is conditional on the servers existing: a server
that is not installed reports status ``not-installed`` - never a hard failure.

Design notes:

- Module-level imports are stdlib ONLY so importing the module stays
  instant at devapi_mcp startup. The mcp SDK is imported lazily inside the
  async session functions.
- Every call spawns a fresh server process (per-call spawn). External
  server-side session state therefore does not persist between calls, and
  spawn cost (2-10s for the munch servers) is mitigated by the 30s tool-list
  cache and per-server spawn locks. Persistent sessions with an idle TTL are
  a possible v2.
- All public functions are synchronous and return the devapi envelope
  (``{"success": ..., "errors": [...]}``); they never raise. This matches the
  ``call_tool_internal`` contract in devapi_mcp.py, which runs handlers in a
  worker thread and logs genuine failures to devapi_errors.log.
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

from armdevtools_mcp.host_tools import REPO_ROOT as _REPO_ROOT
from armdevtools_mcp.telemetry import _MAX_ERROR_CHARS, _MAX_RESULT_CHARS, failure, truncate

_CONFIG_PATH = Path(__file__).parent / "external_mcp.json"

_TOOL_LIST_TTL = 30.0        # seconds, per server
_PROBE_TTL = 60.0            # seconds, per server
_MIN_CALL_TIMEOUT = 1
_MAX_CALL_TIMEOUT = 600
_HANDSHAKE_GRACE_S = 15      # extra on top of a call timeout for spawn+initialize

_config_cache: list[dict] | None = None
_probe_cache: dict[str, tuple[float, dict]] = {}
_tool_cache: dict[str, tuple[float, dict]] = {}
_server_locks: dict[str, threading.Lock] = {}
_CACHE_LOCK = threading.Lock()

log = logging.getLogger("external_mcp")


def _load_config() -> list[dict]:
    """Parse external_mcp.json next to this module (cached). Broken or missing file -> []."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    try:
        raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        servers = raw.get("servers", [])
        if not isinstance(servers, list):
            raise ValueError("'servers' must be a list")
        _config_cache = [s for s in servers if isinstance(s, dict) and s.get("name")]
        return _config_cache
    except Exception as error:  # noqa: BLE001 - config problems must not crash the server
        log.warning("external_mcp config unreadable (%s): %s", _CONFIG_PATH, error)
        _config_cache = []
        return _config_cache


def _get_server(name: str) -> dict:
    """Return one configured server dict; raise KeyError with a helpful message."""
    configured = ", ".join(s.get("name", "?") for s in _load_config()) or "none"
    for server in _load_config():
        if server.get("name") != name:
            continue
        if not server.get("enabled", True):
            raise KeyError(
                f"external MCP server '{name}' is disabled in {_CONFIG_PATH.name}"
                f" (configured servers: {configured})"
            )
        return server
    raise KeyError(f"unknown external MCP server '{name}' (configured: {configured})")


def _lock_for(name: str) -> threading.Lock:
    """Per-server lock serializing spawns/calls against the same server."""
    with _CACHE_LOCK:
        lock = _server_locks.get(name)
        if lock is None:
            lock = _server_locks[name] = threading.Lock()
        return lock


def _cached_tool_list(name: str) -> dict | None:
    with _CACHE_LOCK:
        cached = _tool_cache.get(name)
        if cached and time.monotonic() - cached[0] < _TOOL_LIST_TTL:
            return cached[1]
    return None


def _cached_tool_count(name: str) -> int | None:
    cached = _cached_tool_list(name)
    if cached is None:
        return None
    tools = cached.get("tools")
    return len(tools) if isinstance(tools, list) else None


def _probe(server: dict) -> dict:
    """
    Cheap availability probe, cached _PROBE_TTL seconds.

    Resolves the command on PATH; missing -> status 'not-installed'. Otherwise
    runs ``<command> -V`` (falling back to ``--version``, which click-based
    servers like mcp-server-git expose) and takes the last whitespace token of
    stdout as the version.
    """
    name = server["name"]
    with _CACHE_LOCK:
        cached = _probe_cache.get(name)
        if cached and time.monotonic() - cached[0] < _PROBE_TTL:
            return cached[1]
    command = server.get("command") or ""
    resolved = shutil.which(command) if command else None
    if resolved is None:
        result = {"status": "not-installed", "version": None, "resolved_path": None, "detail": None}
    else:
        version = None
        detail = None
        launch_failed = True
        for flag in ("-V", "--version"):
            try:
                proc = subprocess.run(
                    [resolved, flag],
                    capture_output=True,
                    text=True,
                    timeout=server.get("version_timeout_s", 10),
                )
                launch_failed = False
            except Exception as error:  # noqa: BLE001
                detail = str(error)
                continue
            out = (proc.stdout or "").strip()
            if proc.returncode == 0 and out:
                version = out.split()[-1]
                break
            detail = (proc.stderr or "").strip() or f"exit code {proc.returncode}"
        # CLIs without a version flag (mcp-server-git, jons-mcp-pyright) exit 2
        # printing usage - the binary ran, so the server IS installed; the
        # version just stays unknown.
        if launch_failed:
            result = {"status": "error", "version": None, "resolved_path": resolved, "detail": detail}
        else:
            result = {"status": "installed", "version": version, "resolved_path": resolved, "detail": None}
    with _CACHE_LOCK:
        _probe_cache[name] = (time.monotonic(), result)
    return result


def list_servers() -> dict:
    """List every configured external MCP server with availability status."""
    servers = []
    for server in _load_config():
        probe = _probe(server)
        servers.append(
            {
                "name": server.get("name"),
                "description": server.get("description"),
                "enabled": server.get("enabled", True),
                "command": server.get("command"),
                "resolved_path": probe.get("resolved_path"),
                "version": probe.get("version"),
                "status": probe.get("status"),
                "probe_detail": probe.get("detail"),
                "cached_tool_count": _cached_tool_count(server["name"]),
                "deny_patterns": server.get("deny_patterns") or [],
            }
        )
    return {
        "success": True,
        "servers": servers,
        "note": (
            "availability probes cached for 60s; 'not-installed' is expected on "
            "machines without the tools (see external_mcp.json next to the server)"
        ),
    }


def list_server_tools(server_name: str) -> dict:
    """List one external server's tools (name, description, inputSchema)."""
    try:
        server = _get_server(server_name)
    except KeyError as error:
        return failure(str(error))
    cached = _cached_tool_list(server_name)
    if cached is not None:
        return cached
    probe = _probe(server)
    if probe["status"] != "installed":
        return failure(f"server '{server_name}' is {probe['status']}; install it first", probe=probe)
    with _lock_for(server_name):
        cached = _cached_tool_list(server_name)
        if cached is not None:
            return cached
        try:
            payload = _run_async(_handshake_and_list(server, probe))
        except Exception as error:  # noqa: BLE001
            return {"success": False, "errors": [str(error)]}
    with _CACHE_LOCK:
        _tool_cache[server_name] = (time.monotonic(), payload)
    return payload


def call_external_tool(
    server_name: str,
    tool: str,
    arguments: dict | None = None,
    timeout: int | None = None,
) -> dict:
    """Call one tool on an external MCP server and return its result envelope."""
    try:
        server = _get_server(server_name)
    except KeyError as error:
        return failure(str(error))
    arguments = arguments or {}
    deny = [p for p in (server.get("deny_patterns") or []) if p and p.lower() in tool.lower()]
    if deny:
        return {
            "success": False,
            "errors": [
                f"tool '{tool}' on server '{server_name}' matches deny pattern '{deny[0]}'"
                " - refused before any process started"
            ],
        }
    call_timeout = min(
        max(int(timeout if timeout is not None else server.get("default_call_timeout_s", 120)), _MIN_CALL_TIMEOUT),
        _MAX_CALL_TIMEOUT,
    )
    probe = _probe(server)
    if probe["status"] != "installed":
        return failure(f"server '{server_name}' is {probe['status']}; install it first", probe=probe)
    started = time.monotonic()
    # Each call spawns its own server process, so there is no shared state to
    # serialize - concurrent calls to the same server run independently.
    try:
        result = _run_async(_session_call(server, probe, tool, arguments, call_timeout))
    except Exception as error:  # noqa: BLE001
        return {"success": False, "errors": [str(error)]}
    result["duration"] = round(time.monotonic() - started, 2)
    result.setdefault("note", "fresh server process per call")
    return result


def server_health(server_name: str) -> dict:
    """Handshake plus the server's configured health tool (index/environment state)."""
    try:
        server = _get_server(server_name)
    except KeyError as error:
        return failure(str(error))
    probe = _probe(server)
    if probe["status"] != "installed":
        return failure(f"server '{server_name}' is {probe['status']}; install it first", probe=probe)
    with _lock_for(server_name):
        try:
            return _run_async(_health_session(server, probe))
        except Exception as error:  # noqa: BLE001
            return {"success": False, "errors": [str(error)]}


def _run_async(coro: Any) -> Any:
    """Run a coroutine to completion; safe because handlers run in worker threads."""
    return asyncio.run(coro)


def _tail(text: str, limit: int) -> str:
    text = (text or "").strip()
    return truncate(text, limit, tail=True) if text else ""


def _server_params(server: dict, probe: dict) -> Any:
    """Build StdioServerParameters for one server (SDK imported here)."""
    from mcp import StdioServerParameters

    return StdioServerParameters(
        command=probe["resolved_path"],
        args=server.get("args") or [],
        env=server.get("env") or None,
        cwd=str(server.get("cwd") or _REPO_ROOT),
    )


def _format_call_result(server_name: str, tool_name: str, result: Any) -> dict:
    """Convert an MCP CallToolResult into the devapi envelope shape."""
    texts = []
    content_types = []
    for item in result.content or []:
        content_types.append(getattr(item, "type", "?"))
        text = getattr(item, "text", None)
        if text is not None:
            texts.append(text)
    content = "\n".join(texts)
    truncated = len(content) > _MAX_RESULT_CHARS
    content = truncate(content, _MAX_RESULT_CHARS)
    payload: dict[str, Any] = {
        "success": not result.isError,
        "server": server_name,
        "tool": tool_name,
        "isError": result.isError,
        "content": content,
        "content_types": content_types,
        "truncated": truncated,
    }
    if result.isError:
        payload["errors"] = [content[:_MAX_ERROR_CHARS]]
    if result.structuredContent:
        payload["structuredContent"] = _tail(json.dumps(result.structuredContent, default=str), _MAX_RESULT_CHARS)
    return payload


async def _handshake_and_list(server: dict, probe: dict) -> dict:
    """Spawn the server, initialize, and return its tool list (uncached payload)."""
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    errlog = _errlog()
    handshake_timeout = server.get("handshake_timeout_s", 60)
    try:
        async with asyncio.timeout(handshake_timeout + _HANDSHAKE_GRACE_S):
            async with stdio_client(_server_params(server, probe), errlog=errlog) as (read, write):
                async with ClientSession(read, write) as session:
                    init = await session.initialize()
                    tools = await session.list_tools()
        return {
            "success": True,
            "server": server["name"],
            "server_info": {"name": init.serverInfo.name, "version": init.serverInfo.version},
            "tools": [
                {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
                for t in tools.tools
            ],
        }
    except TimeoutError:
        return {
            "success": False,
            "server": server["name"],
            "errors": [f"handshake timed out after {handshake_timeout}s" + _stderr_suffix(errlog)],
        }
    except Exception as error:  # noqa: BLE001
        if _timeout_in_error(error):
            return {
                "success": False,
                "server": server["name"],
                "errors": [f"handshake timed out after {handshake_timeout}s" + _stderr_suffix(errlog)],
            }
        return {
            "success": False,
            "server": server["name"],
            "errors": [str(error) + _stderr_suffix(errlog)],
        }
    finally:
        errlog.close()


def _timeout_in_error(error: BaseException) -> bool:
    """True when the error is (or wraps) a timeout/cancellation.

    anyio task groups wrap the TimeoutError raised by asyncio.timeout into an
    ExceptionGroup('unhandled errors in a TaskGroup'), so the bare
    ``except TimeoutError`` misses it.
    """
    if isinstance(error, TimeoutError):
        return True
    if isinstance(error, asyncio.CancelledError):
        return True
    # mcp raises its own McpError("Timed out while waiting for response...")
    # from read_timeout_seconds - match duck-typed so mcp stays a lazy import.
    message = str(error).lower()
    if "timed out" in message or "timeout" in message:
        return True
    # ExceptionGroup only exists on py3.11+, so reach .exceptions duck-typed
    # (the devapi MCP must also keep working under the container's py3.10).
    sub_errors = getattr(error, "exceptions", None)
    if sub_errors:
        return any(_timeout_in_error(sub) for sub in sub_errors)
    return False


def _stderr_suffix(errlog: Any) -> str:
    """Drain the child-stderr capture file into an error-message suffix."""
    try:
        errlog.flush()
        errlog.seek(0)
        tail = _tail(errlog.read(), _MAX_ERROR_CHARS)
    except Exception:  # noqa: BLE001 - stderr capture is best-effort
        tail = ""
    return f"; server stderr: {tail}" if tail else ""


def _errlog() -> Any:
    """A real file for child stderr - anyio.open_process needs fileno() (StringIO breaks)."""
    return tempfile.TemporaryFile(mode="w+", encoding="utf-8")


async def _session_call(server: dict, probe: dict, tool_name: str, arguments: dict, timeout_s: int) -> dict:
    """The one place the mcp SDK client is imported. Spawn, call, tear down."""
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    errlog = _errlog()
    try:
        async with asyncio.timeout(timeout_s + _HANDSHAKE_GRACE_S):
            async with stdio_client(_server_params(server, probe), errlog=errlog) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        tool_name,
                        arguments,
                        read_timeout_seconds=timedelta(seconds=timeout_s),
                    )
                    return _format_call_result(server["name"], tool_name, result)
    except TimeoutError:
        return {
            "success": False,
            "server": server["name"],
            "tool": tool_name,
            "errors": [f"call timed out after {timeout_s}s" + _stderr_suffix(errlog)],
        }
    except Exception as error:  # noqa: BLE001
        if _timeout_in_error(error):
            return {
                "success": False,
                "server": server["name"],
                "tool": tool_name,
                "errors": [f"call timed out after {timeout_s}s" + _stderr_suffix(errlog)],
            }
        return {
            "success": False,
            "server": server["name"],
            "tool": tool_name,
            "errors": [str(error) + _stderr_suffix(errlog)],
        }
    finally:
        errlog.close()


async def _health_session(server: dict, probe: dict) -> dict:
    """Spawn once: initialize, count tools, call the configured health tool."""
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    errlog = _errlog()
    started = time.monotonic()
    handshake_timeout = server.get("handshake_timeout_s", 60)
    health_tool = (server.get("health_tools") or [None])[0]
    health_args = server.get("health_tool_args") or {}
    health_timeout = server.get("default_call_timeout_s", 120)
    try:
        async with asyncio.timeout(handshake_timeout + health_timeout + _HANDSHAKE_GRACE_S):
            async with stdio_client(_server_params(server, probe), errlog=errlog) as (read, write):
                async with ClientSession(read, write) as session:
                    init = await session.initialize()
                    tools = await session.list_tools()
                    health_result = None
                    if health_tool:
                        health_result = _format_call_result(
                            server["name"],
                            health_tool,
                            await session.call_tool(
                                health_tool,
                                health_args,
                                read_timeout_seconds=timedelta(seconds=health_timeout),
                            ),
                        )
        healthy = health_result is None or health_result.get("success", False)
        return {
            "success": healthy,
            "server": server["name"],
            "status": "healthy" if healthy else "degraded",
            "version": probe.get("version"),
            "server_info": {"name": init.serverInfo.name, "version": init.serverInfo.version},
            "tool_count": len(tools.tools),
            "health_tool": health_tool,
            "health_result": health_result,
            "duration": round(time.monotonic() - started, 2),
            "note": "fresh server process per call",
        }
    except TimeoutError:
        return {
            "success": False,
            "server": server["name"],
            "errors": ["health check timed out" + _stderr_suffix(errlog)],
        }
    except Exception as error:  # noqa: BLE001
        if _timeout_in_error(error):
            return {
                "success": False,
                "server": server["name"],
                "errors": ["health check timed out" + _stderr_suffix(errlog)],
            }
        return {
            "success": False,
            "server": server["name"],
            "errors": [str(error) + _stderr_suffix(errlog)],
        }
    finally:
        errlog.close()
