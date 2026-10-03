"""
Host-side tests for the jCodeMunch native wrappers in devapi_mcp.

The wrappers are thin mappings over the external MCP gateway, so these tests
check the mapping is wired (names, dispatch) and exercise one live wrapper
when jcodemunch is installed.
"""
import shutil
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp", reason="mcp SDK not installed")

sys.path.insert(0, str(Path(__file__).parent.parent))

from armdevtools_mcp import jcm_tools, server  # noqa: E402


def test_all_jcm_names_in_build_tools():
    names = {t.name for t in server.build_tools()}
    for name in jcm_tools.JCM_NATIVE_TOOLS:
        assert name in names


def test_jcm_dispatch_wired():
    dispatch = server._build_dispatch(None)
    for name, (jcm_tool, _description, _schema) in jcm_tools.JCM_NATIVE_TOOLS.items():
        assert dispatch.get(name) is not None
        assert jcm_tool  # non-empty target tool name


def test_absent_jcodemunch_just_skips(monkeypatch):
    """With jcodemunch missing, a jcm wrapper returns the honest not-installed
    envelope - no spawn, no crash, nothing required."""
    from armdevtools_mcp import external_mcp

    monkeypatch.setattr(
        external_mcp, "_load_config",
        lambda: [{"name": "jcodemunch", "command": "definitely-not-installed-xyz",
                  "args": ["serve"], "env": {}, "cwd": None, "enabled": True}],
    )
    external_mcp._probe_cache.clear()
    jcm_tools._JCM_DEFAULT_REPO = None

    from armdevtools_mcp.server import call_tool_internal

    try:
        result = call_tool_internal("jcm_search_symbols", {"query": "Job"})
        assert result["success"] is False
        assert "not-installed" in result["errors"][0]
    finally:
        # The fake probe would poison the cache for the live tests below.
        external_mcp._probe_cache.clear()
        jcm_tools._JCM_DEFAULT_REPO = None


@pytest.mark.skipif(shutil.which("jcodemunch-mcp") is None, reason="jcodemunch-mcp not installed")
def test_live_search_symbols():
    import json

    from armdevtools_mcp import external_mcp
    from armdevtools_mcp.server import call_tool_internal

    external_mcp._probe_cache.clear()
    jcm_tools._JCM_DEFAULT_REPO = None

    result = call_tool_internal("jcm_search_symbols", {"query": "Job"})
    assert result["success"] is True
    assert result["server"] == "jcodemunch"
    content = json.dumps(result)
    assert "Job" in content or result.get("content")


@pytest.mark.skipif(shutil.which("jcodemunch-mcp") is None, reason="jcodemunch-mcp not installed")
def test_live_repo_health():
    from armdevtools_mcp import external_mcp
    from armdevtools_mcp.server import call_tool_internal

    external_mcp._probe_cache.clear()
    jcm_tools._JCM_DEFAULT_REPO = None

    result = call_tool_internal("jcm_get_repo_health", {})
    assert result["success"] is True
    assert result["server"] == "jcodemunch"
