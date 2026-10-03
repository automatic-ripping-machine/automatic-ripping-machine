#!/usr/bin/env python3
"""
ARM v3 Dev API MCP server - exposes the /__devtools JSON API to MCP clients.

Installed as the ``arm-devtools-mcp`` command (see devtools/pyproject.toml):

    uv tool install ./devtools
    arm-devtools-mcp --base-url http://127.0.0.1:8080

or run from a checkout without installing:

    uvx --from ./devtools arm-devtools-mcp --base-url http://127.0.0.1:8080

Works with any MCP client (Claude Code, Cursor, Copilot, ...).

Error telemetry: genuine tool failures are appended to devapi_errors.log as
bounded JSON lines with redacted arguments; the ``get_tool_errors`` tool reads
them back. Start every session by checking it.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from armdevtools_mcp.client import DevtoolsClient
from armdevtools_mcp.telemetry import _genuine_error_payload, _log_tool_error, failure
from armdevtools_mcp.tools import build_tools

DEFAULT_BASE_URL = "http://127.0.0.1:8080"

def _base_url() -> str:
    return os.environ.get("ARM_DEVTOOLS_BASE_URL", DEFAULT_BASE_URL)


def _build_dispatch(client: Any) -> dict[str, Any]:
    """Build the tool-name -> handler dispatch table, derived from the registry."""
    from armdevtools_mcp.tools import TOOL_REGISTRY

    return {
        name: (lambda args, handler=handler: handler(client, args or {}))
        for name, (_description, _schema, handler) in TOOL_REGISTRY.items()
    }


_dispatch_cache: dict[str, tuple[Any, dict[str, Any]]] = {}


def _dispatch_for(base_url: str) -> tuple[Any, dict[str, Any]]:
    """Build (or reuse) the client and dispatch table for one base URL."""
    cached = _dispatch_cache.get(base_url)
    if cached is None:
        client = DevtoolsClient(base_url)
        cached = (client, _build_dispatch(client))
        _dispatch_cache[base_url] = cached
    return cached


def call_tool_internal(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Route one tool call and return an enveloped result."""
    try:
        _client, dispatch = _dispatch_for(_base_url())
        handler = dispatch.get(name)
        if handler is None:
            raise ValueError(f"unknown tool '{name}'")
        result = handler(arguments or {})
        error_payload = _genuine_error_payload(result)
        if error_payload is not None:
            _log_tool_error(name, arguments or {}, error_payload)
        return result
    except Exception as error:  # noqa: BLE001 - every failure becomes an envelope
        _log_tool_error(name, arguments or {}, {"exception": str(error)})
        return failure(str(error))


server = Server("arm-v3-devapi")

_tool_list_cache: list[Tool] | None = None


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return the (cached) tool descriptors."""
    global _tool_list_cache
    if _tool_list_cache is None:
        _tool_list_cache = build_tools()
    return _tool_list_cache


@server.call_tool()
async def call_tool_sdk(name: str, arguments: dict) -> list[TextContent]:
    """Run one tool handler off the event loop and return its JSON result."""
    result = await asyncio.to_thread(call_tool_internal, name, arguments or {})
    return [TextContent(type="text", text=json.dumps(result, default=str))]


async def run_server() -> None:
    """Serve the MCP server over stdio."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the stdio server."""
    parser = argparse.ArgumentParser(description="ARM Devtools MCP server")
    parser.add_argument("--base-url", help="Base URL of the ARM UI, e.g. http://127.0.0.1:8080")
    args = parser.parse_args(argv)
    if args.base_url:
        os.environ["ARM_DEVTOOLS_BASE_URL"] = args.base_url
    # MCP speaks newline-delimited JSON-RPC; buffered stdout would stall every client.
    sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(run_server())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
