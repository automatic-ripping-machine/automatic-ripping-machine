"""
Devtools service - mutation audit.

Classifies every devtools tool as read_only, mutating or destructive so
an agent can check the blast radius before calling a tool.
"""
from __future__ import annotations

from typing import Any

# Hand-maintained classification of every devtools tool.
# Keep in sync with devtools/armdevtools_mcp/tools.py TOOL_REGISTRY.
_TOOL_AUDIT: dict[str, dict[str, str]] = {
    # Read-only
    "get_app_state": {"category": "read_only"},
    "get_recent_logs": {"category": "read_only"},
    "list_routes": {"category": "read_only"},
    "query_db": {"category": "read_only"},
    "describe_model": {"category": "read_only"},
    "get_table_counts": {"category": "read_only"},
    "get_db_status": {"category": "read_only"},
    "get_app_config": {"category": "read_only"},
    "get_config_value": {"category": "read_only"},
    "get_tool_versions": {"category": "read_only"},
    "check_disk_space": {"category": "read_only"},
    "get_process_list": {"category": "read_only"},
    "get_config_paths": {"category": "read_only"},
    "get_tool_errors": {"category": "read_only"},
    "get_job": {"category": "read_only"},
    "get_jobs_by_status": {"category": "read_only"},
    "get_recent_jobs": {"category": "read_only"},
    "export_job_as_json": {"category": "read_only"},
    "get_job_tracks": {"category": "read_only"},
    "find_orphaned_tracks": {"category": "read_only"},
    "inspect_current_view": {"category": "read_only"},
    "inspect_element": {"category": "read_only"},
    "find_element_by_text": {"category": "read_only"},
    "reload_dev_view": {"category": "read_only"},
    "compare_view_states": {"category": "read_only"},
    "check_db_integrity": {"category": "read_only"},
    "check_job_consistency": {"category": "read_only"},
    "check_route_health": {"category": "read_only"},
    "run_tests": {"category": "read_only", "note": "runs the test suite against arm-db-test"},
    "run_tests_for_file": {"category": "read_only", "note": "runs one test file against arm-db-test"},
    "find_tests_for_module": {"category": "read_only"},
    "check_test_integrity": {"category": "read_only"},
    "run_linter": {"category": "read_only"},
    "run_coverage": {"category": "read_only"},
    "run_type_check": {"category": "read_only"},
    "list_tool_mutations": {"category": "read_only"},
    "docker_compose_build": {"category": "mutating", "note": "rebuilds and restarts the dev stack on the host"},
    "docker_compose_restart": {"category": "mutating", "note": "restarts dev stack services on the host"},
    "run_pr_checks": {"category": "mutating", "note": "git submodule update plus lint and tests"},
    "mcp_external_servers": {"category": "read_only", "note": "probes external MCP servers for availability"},
    "mcp_external_tools": {"category": "read_only", "note": "lists one external server's tools"},
    "mcp_external_health": {"category": "read_only", "note": "handshake plus configured health tool on an external server"},
    "mcp_external_call": {
        "category": "mutating",
        "note": (
            "forwards a call to an external MCP server; side-effects depend on the "
            "external tool; destructive patterns are deny-listed per server config"
        ),
    },
    "get_logs_for_job": {"category": "read_only", "note": "recent log entries mentioning one job"},
    "search_logs": {"category": "read_only", "note": "full-text search across recent log lines"},
    "get_log_stats": {"category": "read_only", "note": "log level counts and newest errors"},
    "get_recent_exceptions": {"category": "read_only", "note": "traceback blocks from recent logs"},
    "list_job_outputs": {"category": "read_only", "note": "files under a job's final destination"},
    "validate_job_completion": {"category": "read_only", "note": "per-track ripped flags and output existence"},
    "probe_media_file": {"category": "read_only", "note": "ffprobe digests of media files"},
    "test_metadata_lookup": {"category": "read_only", "note": "runs the configured metadata provider once"},
    "replay_job_fixture": {"category": "mutating", "note": "imports a job fixture into the database"},
    # jCodeMunch native wrappers (read-only queries over the code index)
    "jcm_search_symbols": {"category": "read_only", "note": "indexed symbol search via jcodemunch"},
    "jcm_get_symbol_source": {"category": "read_only", "note": "one symbol's source from the index"},
    "jcm_get_file_outline": {"category": "read_only", "note": "symbols in one file from the index"},
    "jcm_get_call_hierarchy": {"category": "read_only", "note": "callers and callees of a symbol"},
    "jcm_find_dead_code": {"category": "read_only", "note": "files/symbols with no importers"},
    "jcm_get_blast_radius": {"category": "read_only", "note": "files affected by changing a symbol"},
    "jcm_get_hotspots": {"category": "read_only", "note": "highest-risk symbols by complexity and churn"},
    "jcm_check_edit_safe": {"category": "read_only", "note": "edit-safety preflight for a symbol"},
    "jcm_get_repo_health": {"category": "read_only", "note": "whole-repo triage snapshot"},
    "jcm_get_repo_map": {"category": "read_only", "note": "signature-level repository overview"},
    "jcm_get_untested_symbols": {"category": "read_only", "note": "testing-gap analysis: symbols no test exercises"},
    # Mutating
    "set_config_value": {"category": "mutating", "note": "in-memory only; lost on restart"},
    "reset_job_status": {"category": "mutating"},
    "update_job": {"category": "mutating"},
    "abandon_job": {"category": "mutating", "note": "terminates the job process and marks it failed"},
    "reset_track_state": {"category": "mutating"},
    "create_test_job": {"category": "mutating", "note": "inserts a labelled fixture job"},
    "insert_test_track": {"category": "mutating", "note": "inserts a labelled fixture track"},
    "reset_all": {"category": "mutating", "note": "resets every job to waiting"},
    "make_http_request": {"category": "mutating", "note": "proxies arbitrary requests to the local UI"},
    # Destructive (all support dry_run)
    "delete_job": {"category": "destructive", "dry_run": "supported"},
    "delete_jobs": {"category": "destructive", "dry_run": "supported"},
    "delete_all_jobs": {"category": "destructive", "dry_run": "supported"},
    "clean_jobs": {"category": "destructive", "dry_run": "supported"},
}


def list_tool_mutations() -> dict[str, Any]:
    """
    Return the mutation classification of every devtools tool.

    Returns:
        dict: tool name to category/notes
    """
    return {
        "tools": {name: dict(audit) for name, audit in sorted(_TOOL_AUDIT.items())},
        "categories": ["read_only", "mutating", "destructive"],
    }
