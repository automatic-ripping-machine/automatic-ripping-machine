"""
Devtools MCP jCodeMunch native tools - wrappers over the external MCP gateway.

Each entry maps a devapi tool name to (jcodemunch tool name, description,
schema). The gateway reports 'not-installed' honestly when jcodemunch is
missing, so these degrade instead of breaking.
"""
from __future__ import annotations

import json

from armdevtools_mcp import external_mcp
from armdevtools_mcp.host_tools import REPO_ROOT

JCM_NATIVE_TOOLS: dict[str, tuple[str, str, dict]] = {
    "jcm_search_symbols": (
        "search_symbols",
        "Search jCodeMunch's index of this repo for symbols matching a query. Requires jcodemunch installed (reports not-installed otherwise).",
        {"type": "object", "properties": {"query": {"type": "string", "description": "Symbol name or substring to search for"}},
         "required": ["query"], "additionalProperties": True},
    ),
    "jcm_get_symbol_source": (
        "get_symbol_source",
        "Get full source of one symbol from jCodeMunch's index (symbol_id from jcm_search_symbols).",
        {"type": "object", "properties": {"symbol_id": {"type": "string", "description": "Symbol id from search results"}},
         "required": ["symbol_id"], "additionalProperties": True},
    ),
    "jcm_get_file_outline": (
        "get_file_outline",
        "All symbols in one file with full signatures, from jCodeMunch's index.",
        {"type": "object", "properties": {"file": {"type": "string", "description": "File path within the repo"}},
         "required": ["file"], "additionalProperties": True},
    ),
    "jcm_get_call_hierarchy": (
        "get_call_hierarchy",
        "Incoming callers and outgoing callees for a symbol, N levels deep. Who calls this, and what does it call?",
        {"type": "object", "properties": {"symbol_id": {"type": "string", "description": "Symbol id from search results"}},
         "required": ["symbol_id"], "additionalProperties": True},
    ),
    "jcm_find_dead_code": (
        "find_dead_code",
        "Likely-dead files and symbols: zero importers and no entry-point role. Great first pass when auditing a module.",
        {"type": "object", "properties": {}, "additionalProperties": True},
    ),
    "jcm_get_blast_radius": (
        "get_blast_radius",
        "Every file affected by changing one symbol. Use before editing shared code.",
        {"type": "object", "properties": {"symbol_id": {"type": "string", "description": "Symbol id from search results"}},
         "required": ["symbol_id"], "additionalProperties": True},
    ),
    "jcm_get_hotspots": (
        "get_hotspots",
        "Top-N highest-risk symbols by complexity x change frequency. Where bugs concentrate.",
        {"type": "object", "properties": {"top_n": {"type": "integer", "default": 20, "description": "Number of hotspots to return"}},
         "additionalProperties": True},
    ),
    "jcm_check_edit_safe": (
        "check_edit_safe",
        "Composite preflight: is this symbol safe to edit? Importers, references and risk in one call.",
        {"type": "object", "properties": {"symbol_id": {"type": "string", "description": "Symbol id from search results"}},
         "required": ["symbol_id"], "additionalProperties": True},
    ),
    "jcm_get_repo_health": (
        "get_repo_health",
        "One-call triage of the whole repo: symbol counts, dead code, hotspots, health radar. Good start for a sweep.",
        {"type": "object", "properties": {}, "additionalProperties": True},
    ),
    "jcm_get_repo_map": (
        "get_repo_map",
        "Token-budgeted signature-level overview of the repository. Orientation without reading files.",
        {"type": "object", "properties": {}, "additionalProperties": True},
    ),
    "jcm_get_untested_symbols": (
        "get_untested_symbols",
        "Testing-gap analysis: functions and methods with no evidence of being exercised by any test file, "
        "with reached percentage and per-file breakdown (unreached vs imported_not_called).",
        {"type": "object", "properties": {}, "additionalProperties": True},
    ),
}


def jcm_default_repo() -> str | None:
    """Resolve the checkout's jcodemunch repo id once and cache it.

    Every wrapped jcodemunch tool requires a ``repo`` argument; the agent
    should not have to know the index id, so the wrappers inject it. Only a
    successful resolution is cached - if jcodemunch is not installed yet, the
    next call retries (so installing it mid-session just works).
    """
    global _JCM_DEFAULT_REPO
    if _JCM_DEFAULT_REPO is None:
        result = external_mcp.call_external_tool(
            "jcodemunch", "resolve_repo", {"path": str(REPO_ROOT)}
        )
        try:
            payload = json.loads(result.get("content") or "{}")
            repo = payload.get("repo")
            if repo:
                _JCM_DEFAULT_REPO = repo
        except (TypeError, ValueError):
            pass
    return _JCM_DEFAULT_REPO


def jcm_call(jcm_tool: str, arguments: dict | None) -> dict:
    """Forward one call to jcodemunch with the default repo injected."""
    args = dict(arguments or {})
    if "repo" not in args:
        repo = jcm_default_repo()
        if repo:
            args["repo"] = repo
    return external_mcp.call_external_tool("jcodemunch", jcm_tool, arguments=args)
