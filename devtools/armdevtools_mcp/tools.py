"""Devtools MCP tool registry - the single source for names, schemas and handlers.

Both ``build_tools()`` and the server dispatch table derive from
``TOOL_REGISTRY``, so a name can never exist on one side without the other.
"""
from __future__ import annotations

from typing import Any

from mcp.types import Tool

from armdevtools_mcp import external_mcp
from armdevtools_mcp.host_tools import (
    handle_docker_compose_build,
    handle_docker_compose_restart,
    handle_run_pr_checks,
)
from armdevtools_mcp.jcm_tools import JCM_NATIVE_TOOLS, jcm_call
from armdevtools_mcp.telemetry import _read_tool_errors

_EMPTY_SCHEMA = {"type": "object", "properties": {}}
_DRY_RUN_PROP = {"type": "boolean", "default": False}
_SERVER_DESC = "Configured server name, e.g. jcodemunch, jdocmunch, git or pyright"

def _id_prop(description: str) -> dict:
    return {"type": "integer", "description": description}


def _arg_int(arguments: dict, name: str, default: int | None = None) -> int:
    value = arguments.get(name, default)
    if value is None:
        raise KeyError(name)
    return int(value)


def _arg_bool(arguments: dict, name: str, default: bool = False) -> bool:
    return bool(arguments.get(name, default))


def _arg_int_list(arguments: dict, name: str) -> list[int]:
    return [int(item) for item in arguments[name]]


TOOL_REGISTRY: dict[str, tuple[str, dict, Any]] = {
    "get_app_state": (
        'Get current ARM job, drive, service, warning and safe config summaries. The fastest way to see what ARM is doing right now.',
        _EMPTY_SCHEMA,
        lambda client, _args: client.get_app_state(),
    ),
    "get_recent_logs": (
        "Get recent ARM log lines. Use 'since' to poll for new entries after a known timestamp - pass the timestamp of the last entry you received to get only newer lines. Useful for tailing logs during an active rip.",
        {'type': 'object', 'properties': {'limit': {'type': ['integer', 'string'], 'default': 100}, 'source': {'type': 'string', 'description': 'Log file name under LOGPATH; default is the newest'}, 'since': {'type': 'string', 'description': 'Only return entries after this timestamp'}}},
        lambda client, a: client.get_recent_logs(limit=_arg_int(a, "limit", 100), source=a.get('source'), since=a.get('since')),
    ),
    "list_routes": (
        'List all Flask routes registered on the ARM UI with methods and endpoints.',
        _EMPTY_SCHEMA,
        lambda client, _args: client.list_routes(),
    ),
    "query_db": (
        "Query ARM's MySQL database by model name. Models: job, track, config, user, ui_settings, system_info, system_drives, notifications, alembic_version. Use 'filters' for column=value pairs. Values are redacted via the model's hidden_attribs.",
        {'type': 'object', 'properties': {'model': {'type': 'string', 'description': 'Model name, e.g. job or track'}, 'filters': {'type': 'object', 'description': 'Optional column=value pairs'}, 'limit': {'type': ['integer', 'string'], 'default': 50}}, 'required': ['model']},
        lambda client, a: client.query_db(model=a['model'], filters=a.get('filters'), limit=_arg_int(a, "limit", 50)),
    ),
    "describe_model": (
        "Describe one model's table, columns, types and redaction contract.",
        {'type': 'object', 'properties': {'model': {'type': 'string', 'description': 'Model name, e.g. job or track'}}, 'required': ['model']},
        lambda client, a: client.describe_model(model=a['model']),
    ),
    "get_table_counts": (
        'Count rows in every ARM table.',
        _EMPTY_SCHEMA,
        lambda client, _args: client.get_table_counts(),
    ),
    "get_db_status": (
        'Report the MySQL connection the models run on: server version, database, host, and per-table engine and row counts.',
        _EMPTY_SCHEMA,
        lambda client, _args: client.get_db_status(),
    ),
    "get_app_config": (
        'Return the full arm.yaml config with secret-looking values redacted.',
        _EMPTY_SCHEMA,
        lambda client, _args: client.get_app_config(),
    ),
    "get_config_value": (
        'Return one arm.yaml value (redacted when secret-looking).',
        {'type': 'object', 'properties': {'key': {'type': 'string', 'description': 'arm.yaml key name'}}, 'required': ['key']},
        lambda client, a: client.get_config_value(key=a['key']),
    ),
    "set_config_value": (
        "Set an arm.yaml value IN-MEMORY only - it is lost on restart. Durable, behaviour-affecting changes must go through the UI's /save_settings path.",
        {'type': 'object', 'properties': {'key': {'type': 'string', 'description': 'arm.yaml key name'}, 'value': {'description': "New value; coerced to the existing value's type"}}, 'required': ['key', 'value']},
        lambda client, a: client.set_config_value(key=a['key'], value=a['value']),
    ),
    "get_tool_versions": (
        'Report the installed version of each ARM media tool (HandBrakeCLI, makemkvcon, ffmpeg, abcde, python).',
        _EMPTY_SCHEMA,
        lambda client, _args: client.get_tool_versions(),
    ),
    "check_disk_space": (
        'Report free space on the configured RAW_PATH, TRANSCODE_PATH, COMPLETED_PATH and LOGPATH.',
        _EMPTY_SCHEMA,
        lambda client, _args: client.check_disk_space(),
    ),
    "get_process_list": (
        'List running ARM-related processes (arm, makemkv, handbrake, ffmpeg, abcde).',
        _EMPTY_SCHEMA,
        lambda client, _args: client.get_process_list(),
    ),
    "get_config_paths": (
        'Check existence of the filesystem paths ARM relies on (config, install, logs, db).',
        _EMPTY_SCHEMA,
        lambda client, _args: client.get_config_paths(),
    ),
    "get_job": (
        'Get a full job payload: the serialized row plus attached config, track count and drive references.',
        {'type': 'object', 'properties': {'job_id': {'type': 'integer'}}, 'required': ['job_id']},
        lambda client, a: client.get_job(job_id=_arg_int(a, "job_id")),
    ),
    "get_jobs_by_status": (
        'Return jobs with the given status (e.g. active, success, fail, waiting), newest first.',
        {'type': 'object', 'properties': {'status': {'type': 'string'}, 'limit': {'type': ['integer', 'string'], 'default': 500}}, 'required': ['status']},
        lambda client, a: client.get_jobs_by_status(status=a['status'], limit=_arg_int(a, "limit", 500)),
    ),
    "get_recent_jobs": (
        'Return the most recent jobs with key fields only.',
        {'type': 'object', 'properties': {'limit': {'type': ['integer', 'string'], 'default': 25}}},
        lambda client, a: client.get_recent_jobs(limit=_arg_int(a, "limit", 25)),
    ),
    "export_job_as_json": (
        'Export a job, its redacted config and its tracks as a fixture.',
        {'type': 'object', 'properties': {'job_id': {'type': 'integer'}}, 'required': ['job_id']},
        lambda client, a: client.export_job_as_json(job_id=_arg_int(a, "job_id")),
    ),
    "get_job_tracks": (
        'Return the tracks of a job with ripped/failed/pending counts.',
        {'type': 'object', 'properties': {'job_id': {'type': 'integer'}}, 'required': ['job_id']},
        lambda client, a: client.get_job_tracks(job_id=_arg_int(a, "job_id")),
    ),
    "find_orphaned_tracks": (
        'Return tracks whose job no longer exists.',
        _EMPTY_SCHEMA,
        lambda client, _args: client.find_orphaned_tracks(),
    ),
    "reset_job_status": (
        'Reset a job to a clean state (default waiting): clears stop_time, job_length, errors, ejected and pid fields.',
        {'type': 'object', 'properties': {'job_id': {'type': 'integer'}, 'status': {'type': 'string', 'default': 'waiting'}}, 'required': ['job_id']},
        lambda client, a: client.reset_job_status(job_id=_arg_int(a, "job_id"), status=a.get('status', 'waiting')),
    ),
    "update_job": (
        'Update allowlisted manual fields on a job: title, year, video_type, imdb_id, poster_url, disctype, label, no_of_titles.',
        {'type': 'object', 'properties': {'job_id': {'type': 'integer'}, 'fields': {'type': 'object'}}, 'required': ['job_id', 'fields']},
        lambda client, a: client.update_job(job_id=_arg_int(a, "job_id"), fields=a['fields']),
    ),
    "abandon_job": (
        'Abandon a job: terminates its process (when alive) and marks it failed. dry_run reports what would happen.',
        {'type': 'object', 'properties': {'job_id': {'type': 'integer'}, 'dry_run': _DRY_RUN_PROP}, 'required': ['job_id']},
        lambda client, a: client.abandon_job(job_id=_arg_int(a, "job_id"), dry_run=_arg_bool(a, "dry_run", False)),
    ),
    "delete_job": (
        "Delete one job, its tracks and config, following ARM's own deletion pattern (drive references cleared, notification left). DESTRUCTIVE - pass dry_run=true first.",
        {'type': 'object', 'properties': {'job_id': {'type': 'integer'}, 'dry_run': _DRY_RUN_PROP}, 'required': ['job_id']},
        lambda client, a: client.delete_job(job_id=_arg_int(a, "job_id"), dry_run=_arg_bool(a, "dry_run", False)),
    ),
    "delete_jobs": (
        'Delete several jobs by id. DESTRUCTIVE - pass dry_run=true first.',
        {'type': 'object', 'properties': {'job_ids': {'type': 'array', 'items': {'type': 'integer'}}, 'dry_run': _DRY_RUN_PROP}, 'required': ['job_ids']},
        lambda client, a: client.delete_jobs(job_ids=_arg_int_list(a, "job_ids"), dry_run=_arg_bool(a, "dry_run", False)),
    ),
    "delete_all_jobs": (
        'Delete every job row (plus tracks, config and drive references). DESTRUCTIVE - pass dry_run=true first.',
        {'type': 'object', 'properties': {'dry_run': {'type': 'boolean', 'default': False}}},
        lambda client, a: client.delete_all_jobs(dry_run=_arg_bool(a, "dry_run", False)),
    ),
    "clean_jobs": (
        'Delete finished jobs (success/fail); active jobs are refused. DESTRUCTIVE - pass dry_run=true first.',
        {'type': 'object', 'properties': {'job_ids': {'type': 'array', 'items': {'type': 'integer'}}, 'dry_run': _DRY_RUN_PROP}},
        lambda client, a: client.clean_jobs(job_ids=_arg_int_list(a, "job_ids") if a.get('job_ids') is not None else None, dry_run=_arg_bool(a, "dry_run", False)),
    ),
    "reset_all": (
        'Reset every job to waiting and clear its finish fields. MUTATING - pass dry_run=true first.',
        {'type': 'object', 'properties': {'dry_run': {'type': 'boolean', 'default': False}}},
        lambda client, a: client.reset_all(dry_run=_arg_bool(a, "dry_run", False)),
    ),
    "reset_track_state": (
        'Reset a track to its unripped state.',
        {'type': 'object', 'properties': {'track_id': {'type': 'integer'}}, 'required': ['track_id']},
        lambda client, a: client.reset_track_state(track_id=_arg_int(a, "track_id")),
    ),
    "create_test_job": (
        'Create a labelled DEVTOOLS_FIXTURE test job with a config snapshot. Remove it with delete_job afterwards.',
        {'type': 'object', 'properties': {'device_path': {'type': 'string', 'default': '/dev/sr0'}}},
        lambda client, a: client.create_test_job(device_path=a.get('device_path', '/dev/sr0')),
    ),
    "insert_test_track": (
        'Insert a labelled DEVTOOLS_FIXTURE test track on an existing job.',
        {'type': 'object', 'properties': {'job_id': {'type': 'integer'}}, 'required': ['job_id']},
        lambda client, a: client.insert_test_track(job_id=_arg_int(a, "job_id")),
    ),
    "inspect_current_view": (
        'Render an ARM page server-side (login and CSRF bypassed) and return its title, visible sections and interactive elements. Use for quick UI inspection.',
        {'type': 'object', 'properties': {'path': {'type': 'string', 'default': '/'}, 'query': {'type': 'object'}}},
        lambda client, a: client.inspect_current_view(path=a.get('path', '/'), query=a.get('query')),
    ),
    "inspect_element": (
        'Inspect one element in a snapshot by selector (#id, .class, tag), visible text, or data-testid.',
        {'type': 'object', 'properties': {'snapshot_id': {'type': 'string'}, 'path': {'type': 'string'}, 'selector': {'type': 'string'}, 'visible_text': {'type': 'string'}, 'test_id': {'type': 'string'}}},
        lambda client, a: client.inspect_element({key: value for key, value in a.items() if key in {'snapshot_id', 'path', 'selector', 'visible_text', 'test_id'} and value is not None}),
    ),
    "find_element_by_text": (
        'Find elements whose text contains the given string.',
        {'type': 'object', 'properties': {'text': {'type': 'string'}, 'path': {'type': 'string'}, 'snapshot_id': {'type': 'string'}}, 'required': ['text']},
        lambda client, a: client.find_element_by_text(text=a['text'], path=a.get('path'), snapshot_id=a.get('snapshot_id')),
    ),
    "reload_dev_view": (
        'Re-render an ARM route and return a fresh snapshot (same as inspect_current_view after a code change).',
        {'type': 'object', 'properties': {'path': {'type': 'string', 'default': '/'}, 'query': {'type': 'object'}}},
        lambda client, a: client.reload_dev_view(path=a.get('path', '/'), query=a.get('query')),
    ),
    "compare_view_states": (
        "Compare two snapshots' sections and interactive elements by snapshot id.",
        {'type': 'object', 'properties': {'before_id': {'type': 'string'}, 'after_id': {'type': 'string'}, 'before': {'type': 'string', 'description': 'Alias for before_id.'}, 'after': {'type': 'string', 'description': 'Alias for after_id.'}}},
        lambda client, a: {'success': False, 'error': 'compare_view_states requires before_id= and after_id= (snapshot IDs from a prior snapshot call).'} if not (a.get('before_id') or a.get('before')) or not (a.get('after_id') or a.get('after')) else client.compare_view_states(before_id=a.get('before_id') or a.get('before'), after_id=a.get('after_id') or a.get('after')),
    ),
    "run_tests": (
        'Run the pytest suite (default test_ui) against the MySQL test database arm-db-test. arm-db-test must be running. Returns exit code, output tail and duration.',
        {'type': 'object', 'properties': {'paths': {'type': 'array', 'items': {'type': 'string'}}, 'verbose': {'type': 'boolean', 'default': True}, 'maxfail': {'type': ['integer', 'string'], 'default': 1}}},
        lambda client, a: client.run_tests(paths=a.get('paths'), verbose=_arg_bool(a, "verbose", True), maxfail=_arg_int(a, "maxfail", 1)),
    ),
    "find_tests_for_module": (
        'Find the test files covering a module (e.g. ui.devtools.routes, models.job).',
        {'type': 'object', 'properties': {'module': {'type': 'string'}}, 'required': ['module']},
        lambda client, a: client.find_tests_for_module(module_name=a['module']),
    ),
    "run_tests_for_file": (
        'Run one test file, e.g. test_ui/test_bp_devtools.py, against arm-db-test.',
        {'type': 'object', 'properties': {'test_path': {'type': 'string'}, 'verbose': {'type': 'boolean', 'default': True}}, 'required': ['test_path']},
        lambda client, a: client.run_tests_for_file(test_path=a['test_path'], verbose=_arg_bool(a, "verbose", True)),
    ),
    "run_linter": (
        "Run flake8 against ARM code with v3's setup.cfg configuration (default: arm, test_ui, test_ripper, devtools).",
        {'type': 'object', 'properties': {'paths': {'type': 'array', 'items': {'type': 'string'}}}},
        lambda client, a: client.run_linter(paths=a.get('paths')),
    ),
    "run_coverage": (
        'Run pytest with coverage over the UI package against arm-db-test.',
        {'type': 'object', 'properties': {'paths': {'type': 'array', 'items': {'type': 'string'}}}},
        lambda client, a: client.run_coverage(paths=a.get('paths')),
    ),
    "check_test_integrity": (
        'Verify the test suite has not been modified since the last snapshot (sha256 manifest under the log path).',
        _EMPTY_SCHEMA,
        lambda client, _args: client.check_test_integrity(),
    ),
    "list_tool_mutations": (
        'Classify every devtools tool as read_only, mutating or destructive. Check before calling.',
        _EMPTY_SCHEMA,
        lambda client, _args: client.list_tool_mutations(),
    ),
    "check_db_integrity": (
        'Run MySQL CHECK TABLE against every ARM table.',
        _EMPTY_SCHEMA,
        lambda client, _args: client.check_db_integrity(),
    ),
    "check_job_consistency": (
        'Heuristic consistency checks: dead pids, missing tracks, orphaned configs, active jobs without a drive.',
        _EMPTY_SCHEMA,
        lambda client, _args: client.check_job_consistency(),
    ),
    "check_route_health": (
        'GET every parameterless ARM route through the test client and report non-2xx responses.',
        _EMPTY_SCHEMA,
        lambda client, _args: client.check_route_health(),
    ),
    "run_type_check": (
        'Run pyright against arm/ui when installed (reports an install hint otherwise).',
        _EMPTY_SCHEMA,
        lambda client, _args: client.run_type_check(),
    ),
    "make_http_request": (
        'Make a GET or POST request to the local ARM UI (localhost only), e.g. to call the /json feed.',
        {'type': 'object', 'properties': {'method': {'type': 'string', 'default': 'GET'}, 'path': {'type': 'string'}, 'body': {'type': 'object'}}, 'required': ['path']},
        lambda client, a: client.make_http_request(method=a.get('method', 'GET'), path=a['path'], body=a.get('body')),
    ),
    "docker_compose_build": (
        "Build and restart the ARM stack on the dev machine (default: the arm-ui service). Uses the checkout's docker-compose.yml, plus docker-compose.dev.yml when present (override with dev_override=false). This replaces the legacy armdocker rebuild CLI.",
        {'type': 'object', 'properties': {'services': {'type': ['array', 'string'], 'items': {'type': 'string'}, 'default': ['arm-ui']}, 'dev_override': {'type': 'boolean'}}},
        lambda client, a: handle_docker_compose_build(a),
    ),
    "docker_compose_restart": (
        'Restart services in the ARM stack on the dev machine (default: arm-ui).',
        {'type': 'object', 'properties': {'services': {'type': ['array', 'string'], 'items': {'type': 'string'}, 'default': ['arm-ui']}, 'dev_override': {'type': 'boolean'}}},
        lambda client, a: handle_docker_compose_restart(a),
    ),
    "run_pr_checks": (
        'Run the pre-PR checks that used to be armgit.pr_update(): git submodule update --remote, flake8 over arm/test_ui/test_ripper/devtools, and the test suite against arm-db-test (all through the UI container).',
        {'type': 'object', 'properties': {'dev_override': {'type': 'boolean'}}},
        lambda client, a: handle_run_pr_checks(a),
    ),
    "get_tool_errors": (
        'Read recent entries from devapi_errors.log next to the server, newest first. Start every session by checking this; wrong-parameter calls are filtered out, so entries here are genuine failures.',
        {'type': 'object', 'properties': {'limit': {'type': ['integer', 'string'], 'default': 20}}},
        lambda client, a: _read_tool_errors(limit=_arg_int(a, "limit", 20)),
    ),
    "mcp_external_servers": (
        "List configured external MCP servers with availability status (jcodemunch, jdocmunch, git, pyright). Each server is probed lazily (executable on PATH plus a version check, cached 60s); a server that is not installed reports status 'not-installed' - never an error. Use before mcp_external_tools or mcp_external_call to see what is available.",
        _EMPTY_SCHEMA,
        lambda client, _args: external_mcp.list_servers(),
    ),
    "mcp_external_tools": (
        "List one external MCP server's tools (name, description, inputSchema). Spawns the server over stdio and caches the list for 30 seconds. Requires the server to be installed (see mcp_external_servers).",
        {'type': 'object', 'properties': {'server': {'type': 'string', 'description': _SERVER_DESC}}, 'required': ['server']},
        lambda client, a: external_mcp.list_server_tools(a['server']),
    ),
    "mcp_external_call": (
        "Call one tool on an external MCP server and return its JSON result. Arguments are passed through as JSON. Each call spawns a fresh server process, so server-side session state does not persist between calls. Tool names matching the server's deny patterns (destructive/index-management tools, configured in devtools/armdevtools_mcp/external_mcp.json) are refused before any process starts. Result text is truncated to 20000 chars.",
        {'type': 'object', 'properties': {'server': {'type': 'string', 'description': _SERVER_DESC}, 'tool': {'type': 'string', 'description': 'External tool name, from mcp_external_tools'}, 'arguments': {'type': 'object', 'description': 'Tool arguments as JSON'}, 'timeout': {'type': 'integer', 'default': 120, 'description': 'Seconds; 1-600'}}, 'required': ['server', 'tool']},
        lambda client, a: external_mcp.call_external_tool(a['server'], a['tool'], arguments=a.get('arguments') or {}, timeout=_arg_int(a, "timeout", 120)),
    ),
    "mcp_external_health": (
        "Health/index status of one external MCP server: handshake plus the server's configured health tool (list_repos for jcodemunch, get_index_overview for jdocmunch, git_status for git, list_environments for pyright). Useful to see whether a server has indexes at all.",
        {'type': 'object', 'properties': {'server': {'type': 'string', 'description': _SERVER_DESC}}, 'required': ['server']},
        lambda client, a: external_mcp.server_health(a['server']),
    ),
    "get_logs_for_job": (
        'Return recent log entries that mention one job (v3 logs are plain text, so matching is a substring search for the job id). Optionally filter by levels.',
        {'type': 'object', 'properties': {'job_id': _id_prop('Job whose log lines to find'), 'limit': {'type': 'integer', 'default': 200, 'description': 'Max entries (capped 500)'}, 'levels': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Optional levels, e.g. ["ERROR"]'}}, 'required': ['job_id']},
        lambda client, a: client.get_logs_for_job(job_id=_arg_int(a, "job_id"), limit=_arg_int(a, "limit", 200), levels=a.get('levels')),
    ),
    "search_logs": (
        'Full-text search across recent ARM log lines (case-insensitive substring on the message). Optionally filter by levels.',
        {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'Text to search for'}, 'limit': {'type': 'integer', 'default': 100, 'description': 'Max entries (capped 500)'}, 'levels': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Optional levels, e.g. ["ERROR"]'}}, 'required': ['query']},
        lambda client, a: client.search_logs(query=a['query'], limit=_arg_int(a, "limit", 100), levels=a.get('levels')),
    ),
    "get_log_stats": (
        'Summarise recent ARM log activity: counts by level, the newest ERROR and CRITICAL messages, and an error rate. Quick health check without reading the full log.',
        {'type': 'object', 'properties': {'lines_to_scan': {'type': 'integer', 'default': 1000, 'description': 'Recent lines to analyse (capped 5000)'}}},
        lambda client, a: client.get_log_stats(lines_to_scan=_arg_int(a, "lines_to_scan", 1000)),
    ),
    "get_recent_exceptions": (
        "Extract Python traceback blocks from recent ARM logs (a parsed line whose message starts with 'Traceback' opens a block). Useful after a run to see what actually raised.",
        {'type': 'object', 'properties': {'limit': {'type': 'integer', 'default': 20, 'description': 'Max exception blocks (capped 100)'}}},
        lambda client, a: client.get_recent_exceptions(limit=_arg_int(a, "limit", 20)),
    ),
    "list_job_outputs": (
        "List the files on disk under a job's final destination directory. Read-only.",
        {'type': 'object', 'properties': {'job_id': _id_prop('Job to inspect')}, 'required': ['job_id']},
        lambda client, a: client.list_job_outputs(job_id=_arg_int(a, "job_id")),
    ),
    "validate_job_completion": (
        "Check whether a job actually completed: per-track ripped flags, whether each ripped track's output exists on disk under the job's final destination, and the overall verdict. Read-only; does not re-derive ripper state.",
        {'type': 'object', 'properties': {'job_id': _id_prop('Job to verify')}, 'required': ['job_id']},
        lambda client, a: client.validate_job_completion(job_id=_arg_int(a, "job_id")),
    ),
    "probe_media_file": (
        "ffprobe digests for a job's completed output files, or for one explicit file path: video/audio/subtitle streams, format info and chapters. Read-only.",
        {'type': 'object', 'properties': {'job_id': _id_prop("Probe media files under this job's final destination"), 'path': {'type': 'string', 'description': 'Or probe exactly this file'}}},
        lambda client, a: client.probe_media_file(job_id=a.get('job_id'), path=a.get('path')),
    ),
    "test_metadata_lookup": (
        'Run the configured metadata provider (OMDB or TMDB per METADATA_PROVIDER) against one IMDb id and report the raw result plus diagnostics. Read-only.',
        {'type': 'object', 'properties': {'imdb_id': {'type': 'string', 'description': 'IMDb id, e.g. tt0088559'}}, 'required': ['imdb_id']},
        lambda client, a: client.test_metadata_lookup(imdb_id=a['imdb_id']),
    ),
    "replay_job_fixture": (
        'Import an export_job_as_json fixture into the database: reconstructs the job row, a fresh config snapshot and its tracks. Mutating. v3 has no state-transition model, so transitions are not carried.',
        {'type': 'object', 'properties': {'fixture': {'type': 'object', 'description': 'The export_job_as_json payload (job, config, tracks keys)'}}, 'required': ['fixture']},
        lambda client, a: client.replay_job_fixture(fixture=a['fixture']),
    ),
}

# jCodeMunch wrappers join the registry from their own table.
TOOL_REGISTRY.update({
    name: (description, schema, lambda client, a, target=target: jcm_call(target, a or {}))
    for name, (target, description, schema) in JCM_NATIVE_TOOLS.items()
})


def build_tools() -> list[Tool]:
    """Return the MCP tool descriptors, derived from the registry."""
    return [
        Tool(name=name, description=description, inputSchema=schema)
        for name, (description, schema, _handler) in TOOL_REGISTRY.items()
    ]
