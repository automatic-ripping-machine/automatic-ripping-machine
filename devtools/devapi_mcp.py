#!/usr/bin/env python3
"""
Shim for running the MCP server straight from a checkout without installing:

    python devtools/devapi_mcp.py --base-url http://127.0.0.1:8080

The server itself lives in devtools/armdevtools_mcp/server.py and is installed
as the ``arm-devtools-mcp`` command (see devtools/pyproject.toml):

    uv tool install ./devtools
    arm-devtools-mcp --base-url http://127.0.0.1:8080
"""
from armdevtools_mcp.server import main

if __name__ == "__main__":
    raise SystemExit(main())
