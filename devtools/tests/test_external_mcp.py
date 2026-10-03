"""
Host-side tests for devtools/armdevtools_mcp/external_mcp.py.

Run with the ARM venv (which has mcp + pytest):

    .venv/bin/python -m pytest devtools/tests/test_external_mcp.py -v

Fake-server tests spawn a tiny inline MCP server under sys.executable and never
depend on the real uv tools. Real-handshake tests skip when the binary is not
installed - integration is deliberately conditional on existence.
"""
import json
import os
import shutil
import sys
import time

import pytest

pytest.importorskip("mcp", reason="mcp SDK not installed")

from armdevtools_mcp import external_mcp  # noqa: E402 - after importorskip


FAKE_SERVER_SOURCE = '''\
import asyncio
import json
import os
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

server = Server("fake-external")


@server.list_tools()
async def list_tools():
    return [
        Tool(name="echo", description="Echo arguments back as JSON", inputSchema={"type": "object"}),
        Tool(name="explode", description="Always returns an error", inputSchema={"type": "object"}),
        Tool(name="big_output", description="200k chars of output", inputSchema={"type": "object"}),
        Tool(name="slow", description="Sleeps 30s then returns", inputSchema={"type": "object"}),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "echo":
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(arguments))])
    if name == "explode":
        return CallToolResult(content=[TextContent(type="text", text="kaboom")], isError=True)
    if name == "big_output":
        return CallToolResult(content=[TextContent(type="text", text="x" * 200000)])
    if name == "slow":
        await asyncio.sleep(30)
        return CallToolResult(content=[TextContent(type="text", text="finally")])
    raise ValueError(f"unknown tool {name}")


async def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)
    marker = os.environ.get("FAKE_MARKER")
    if marker:
        with open(marker, "a", encoding="utf-8") as fh:
            fh.write("spawned\\n")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
'''


@pytest.fixture
def fake_server(tmp_path, monkeypatch):
    """Configure external_mcp to use a fake stdio MCP server under sys.executable."""
    script = tmp_path / "fake_server.py"
    script.write_text(FAKE_SERVER_SOURCE, encoding="utf-8")
    marker = tmp_path / "spawns.log"
    config = {
        "name": "fake-external",
        "description": "test fake",
        "command": sys.executable,
        "args": [str(script)],
        "env": {"FAKE_MARKER": str(marker)},
        "cwd": None,
        "enabled": True,
        "version_timeout_s": 10,
        "handshake_timeout_s": 60,
        "default_call_timeout_s": 30,
        "deny_patterns": [],
        "health_tools": ["echo"],
        "health_tool_args": {},
    }
    monkeypatch.setattr(external_mcp, "_load_config", lambda: [config])
    external_mcp._probe_cache.clear()
    external_mcp._tool_cache.clear()
    external_mcp._config_cache = None
    return {"config": config, "marker": marker}


def spawn_count(marker):
    if not marker.exists():
        return 0
    return len(marker.read_text(encoding="utf-8").splitlines())


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestConfig:

    def test_config_parses_committed_servers(self):
        external_mcp._config_cache = None
        servers = external_mcp._load_config()
        assert [s["name"] for s in servers] == ["jcodemunch", "jdocmunch", "git", "pyright"]
        assert all(s.get("enabled") for s in servers)
        assert all(s.get("health_tools") for s in servers)
        deny = {s["name"]: s.get("deny_patterns") or [] for s in servers}
        assert deny["jcodemunch"] and deny["jdocmunch"]
        assert "reset" in deny["git"] and "init" in deny["git"]
        assert deny["pyright"] == []

    def test_unknown_server_is_honest_error(self, fake_server):
        result = external_mcp.list_server_tools("no-such-server")
        assert result["success"] is False
        assert "no-such-server" in result["errors"][0]
        assert "fake-external" in result["errors"][0]  # lists configured names


# ---------------------------------------------------------------------------
# Probing / availability
# ---------------------------------------------------------------------------

class TestProbe:

    def test_probe_not_installed_is_honest(self, monkeypatch):
        monkeypatch.setattr(
            external_mcp, "_load_config",
            lambda: [{"name": "ghost", "command": "definitely-not-a-real-binary-xyz", "enabled": True}],
        )
        external_mcp._probe_cache.clear()
        result = external_mcp.list_servers()
        assert result["success"] is True
        assert result["servers"][0]["status"] == "not-installed"
        assert result["servers"][0]["resolved_path"] is None

    def test_probe_installed_fake(self, fake_server):
        external_mcp._probe_cache.clear()
        result = external_mcp.list_servers()
        server = result["servers"][0]
        assert server["status"] == "installed"
        assert server["version"] is not None  # python -V prints "Python x.y.z"
        assert server["resolved_path"] == sys.executable

    def test_probe_cli_without_version_flag_reports_installed(self, tmp_path, monkeypatch):
        # CLIs like mcp-server-git / jons-mcp-pyright exit 2 with usage on
        # -V/--version; the binary ran, so the server is installed and the
        # version stays unknown.
        bindir = tmp_path / "bin"
        bindir.mkdir()
        script = bindir / "noversion-cli"
        script.write_text("#!/bin/sh\necho 'Usage: noversion-cli [OPTIONS]' >&2\nexit 2\n", encoding="utf-8")
        script.chmod(0o755)
        monkeypatch.setenv("PATH", f"{bindir}:{os.environ['PATH']}")
        probe = external_mcp._probe({"name": "noversion", "command": "noversion-cli"})
        assert probe["status"] == "installed"
        assert probe["version"] is None


# ---------------------------------------------------------------------------
# Tool listing
# ---------------------------------------------------------------------------

class TestToolListing:

    def test_list_server_tools_fake(self, fake_server):
        result = external_mcp.list_server_tools("fake-external")
        assert result["success"] is True
        names = [t["name"] for t in result["tools"]]
        assert {"echo", "explode", "big_output", "slow"} <= set(names)
        assert result["server_info"]["name"] == "fake-external"

    def test_tool_list_is_cached_30s(self, fake_server):
        assert external_mcp.list_server_tools("fake-external")["success"] is True
        assert external_mcp.list_server_tools("fake-external")["success"] is True
        assert spawn_count(fake_server["marker"]) == 1  # second call served from cache


# ---------------------------------------------------------------------------
# Calling
# ---------------------------------------------------------------------------

class TestCalling:

    def test_call_roundtrip(self, fake_server):
        result = external_mcp.call_external_tool("fake-external", "echo", {"text": "hi"})
        assert result["success"] is True
        assert result["isError"] is False
        assert json.loads(result["content"]) == {"text": "hi"}
        assert result["note"] == "fresh server process per call"

    def test_call_iserror_surfaces_failure(self, fake_server):
        result = external_mcp.call_external_tool("fake-external", "explode", {})
        assert result["success"] is False
        assert result["isError"] is True
        assert result["errors"]

    def test_call_denied_tool_refused_before_spawn(self, fake_server, monkeypatch):
        config = dict(fake_server["config"])
        config["deny_patterns"] = ["explode"]
        monkeypatch.setattr(external_mcp, "_load_config", lambda: [config])
        external_mcp._probe_cache.clear()
        result = external_mcp.call_external_tool("fake-external", "explode", {})
        assert result["success"] is False
        assert "deny pattern" in result["errors"][0]
        assert spawn_count(fake_server["marker"]) == 0  # never spawned

    def test_call_unknown_tool(self, fake_server):
        result = external_mcp.call_external_tool("fake-external", "nope", {})
        assert result["success"] is False

    def test_call_timeout_enforced(self, fake_server):
        started = time.monotonic()
        result = external_mcp.call_external_tool("fake-external", "slow", {}, timeout=1)
        elapsed = time.monotonic() - started
        assert result["success"] is False
        assert "timed out" in result["errors"][0]
        assert elapsed < 10

    def test_result_truncation(self, fake_server):
        result = external_mcp.call_external_tool("fake-external", "big_output", {})
        assert result["success"] is True
        assert result["truncated"] is True
        assert "truncated" in result["content"]
        assert len(result["content"]) < 21000


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:

    def test_health_fake(self, fake_server):
        result = external_mcp.server_health("fake-external")
        assert result["success"] is True
        assert result["status"] == "healthy"
        assert result["tool_count"] == 4
        assert result["health_tool"] == "echo"
        assert result["health_result"]["success"] is True

    def test_health_not_installed(self, monkeypatch):
        monkeypatch.setattr(
            external_mcp, "_load_config",
            lambda: [{"name": "ghost", "command": "definitely-not-a-real-binary-xyz", "enabled": True}],
        )
        external_mcp._probe_cache.clear()
        result = external_mcp.server_health("ghost")
        assert result["success"] is False
        assert "not-installed" in result["errors"][0]


# ---------------------------------------------------------------------------
# Real servers (skip when not installed - conditional by design)
# ---------------------------------------------------------------------------

class TestRealServers:

    @pytest.mark.skipif(shutil.which("jcodemunch-mcp") is None, reason="jcodemunch-mcp not installed")
    def test_real_jcodemunch(self):
        external_mcp._probe_cache.clear()
        external_mcp._tool_cache.clear()
        assert external_mcp.list_server_tools("jcodemunch")["success"] is True
        health = external_mcp.server_health("jcodemunch")
        assert health["success"] is True
        assert health["tool_count"] > 0

    @pytest.mark.skipif(shutil.which("jdocmunch-mcp") is None, reason="jdocmunch-mcp not installed")
    def test_real_jdocmunch(self):
        external_mcp._probe_cache.clear()
        external_mcp._tool_cache.clear()
        assert external_mcp.list_server_tools("jdocmunch")["success"] is True

    @pytest.mark.skipif(shutil.which("mcp-server-git") is None, reason="mcp-server-git not installed")
    def test_real_git(self):
        external_mcp._probe_cache.clear()
        result = external_mcp.server_health("git")
        assert result["success"] is True
        assert result["health_tool"] == "git_status"

    @pytest.mark.skipif(shutil.which("jons-mcp-pyright") is None, reason="jons-mcp-pyright not installed")
    def test_real_pyright(self):
        external_mcp._probe_cache.clear()
        external_mcp._tool_cache.clear()
        assert external_mcp.list_server_tools("pyright")["success"] is True
