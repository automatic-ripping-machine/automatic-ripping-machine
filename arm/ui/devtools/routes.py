"""
Devtools routes - dev-gated JSON API under /__devtools.

All responses use the schemas.make_response envelope. Endpoints are
development aids and return 404 when ENABLE_DEVTOOLS is not set in arm.yaml.
Destructive endpoints honour a dry_run flag from the JSON body or query string.
"""
from __future__ import annotations

import json
from typing import Any

from flask import Blueprint, jsonify, request

from config import config as cfg

from ui.devtools.schemas import make_response
from ui.devtools.services import (
    bug_finder_service,
    completion_service,
    config_service,
    db_service,
    exec_service,
    job_service,
    log_analysis_service,
    log_service,
    media_probe_service,
    metadata_service,
    mutation_audit_service,
    proxy_service,
    replay_service,
    schema_service,
    state_service,
    system_service,
    test_fixture_service,
    track_service,
    ui_inspector,
)


def _enabled() -> bool:
    """
    Check the live arm.yaml flag.

    The config is re-read per request, so a runtime toggle is honoured
    even when the blueprint was registered at startup.

    Returns:
        bool: True when ENABLE_DEVTOOLS is set
    """
    return bool(cfg.arm_config.get("ENABLE_DEVTOOLS", False))


def _json_error(message: str, status_code: int = 400):
    """
    Return an enveloped error response.

    Args:
        message: error description
        status_code: HTTP status (default 400)
    """
    return jsonify(make_response(success=False, errors=[message])), status_code


def _run(service_call: Any):
    """
    Call a devtools service and return an enveloped Flask response.

    Args:
        service_call: zero-argument callable returning the data payload
    """
    try:
        return jsonify(make_response(success=True, data=service_call()))
    except ValueError as error:
        return _json_error(str(error), status_code=400)
    except Exception as error:  # noqa: BLE001 - devtools must never raise raw
        return _json_error(str(error), status_code=500)


def _dry_run_flag() -> bool:
    """
    Read a dry_run flag from the request body or query string.

    Returns:
        bool: the parsed flag (default False)
    """
    payload = request.get_json(silent=True) or {}
    raw = payload.get("dry_run", request.args.get("dry_run", "false"))
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("1", "true", "yes", "t")


def _body() -> dict[str, Any]:
    """Return the JSON request body, or an empty dict."""
    return request.get_json(silent=True) or {}


def _int_arg(name: str) -> int | None:
    """Read an optional integer query argument."""
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    return int(raw)


def _csv_arg(name: str) -> list[str] | None:
    """Read an optional comma-separated query argument, or None when absent."""
    raw = request.args.get(name)
    if not raw:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def register_routes(blueprint: Blueprint) -> None:
    """
    Register all devtools endpoints on the blueprint.

    Args:
        blueprint: the devtools blueprint
    """

    @blueprint.before_request
    def _guard():
        # Return 404 so a disabled surface is indistinguishable from absent.
        if not _enabled():
            return _json_error("devtools_disabled", status_code=404)

    # --- State and logs ----------------------------------------------------

    @blueprint.get("/state")
    def get_state_route():
        return _run(state_service.get_app_state)

    @blueprint.get("/logs")
    def get_logs_route():
        def _get_logs():
            return log_service.get_recent_logs(
                limit=int(request.args.get("limit", 100)),
                source=request.args.get("source"),
                since=request.args.get("since"),
            )

        return _run(_get_logs)

    # --- Routes and schema -------------------------------------------------

    @blueprint.get("/routes")
    def list_routes_route():
        return _run(schema_service.list_routes)

    @blueprint.get("/db")
    def query_db_route():
        def _query_db():
            filters = None
            raw_filters = request.args.get("filters")
            if raw_filters:
                filters = json.loads(raw_filters)
                if not isinstance(filters, dict):
                    raise ValueError("filters must be a JSON object of column=value pairs")
            return db_service.query_db(
                model_name=request.args.get("model", ""),
                filters=filters,
                limit=int(request.args.get("limit", 50)),
            )

        return _run(_query_db)

    @blueprint.get("/describe-model")
    def describe_model_route():
        def _describe_model():
            return db_service.describe_model(request.args.get("model", ""))

        return _run(_describe_model)

    @blueprint.get("/db/table-counts")
    def table_counts_route():
        return _run(db_service.get_table_counts)

    @blueprint.get("/db/status")
    def db_status_route():
        return _run(db_service.get_db_status)

    # --- Config ------------------------------------------------------------

    @blueprint.get("/config")
    def get_config_route():
        return _run(config_service.get_app_config)

    @blueprint.get("/config/value")
    def get_config_value_route():
        def _get_config_value():
            return config_service.get_config_value(request.args.get("key", ""))

        return _run(_get_config_value)

    @blueprint.post("/config/value")
    def set_config_value_route():
        def _set_config_value():
            payload = _body()
            key = payload.get("key") or request.args.get("key", "")
            if "value" not in payload:
                raise ValueError("value is required")
            return config_service.set_config_value(key, payload["value"])

        return _run(_set_config_value)

    # --- System ------------------------------------------------------------

    @blueprint.get("/system/tool-versions")
    def tool_versions_route():
        return _run(system_service.get_tool_versions)

    @blueprint.get("/system/disk-space")
    def disk_space_route():
        return _run(system_service.check_disk_space)

    @blueprint.get("/system/processes")
    def processes_route():
        return _run(system_service.get_process_list)

    @blueprint.get("/system/config-paths")
    def config_paths_route():
        return _run(system_service.get_config_paths)

    # --- Jobs: read --------------------------------------------------------

    @blueprint.get("/job/<int:job_id>")
    def get_job_route(job_id: int):
        return _run(lambda: job_service.get_job(job_id))

    @blueprint.get("/jobs/by-status")
    def jobs_by_status_route():
        def _by_status():
            return job_service.get_jobs_by_status(
                status=request.args.get("status", ""),
                limit=int(request.args.get("limit", 500)),
            )

        return _run(_by_status)

    @blueprint.get("/jobs/recent")
    def recent_jobs_route():
        def _recent():
            return job_service.get_recent_jobs(limit=int(request.args.get("limit", 25)))

        return _run(_recent)

    @blueprint.get("/job/<int:job_id>/export")
    def export_job_route(job_id: int):
        return _run(lambda: job_service.export_job_as_json(job_id))

    @blueprint.get("/job/<int:job_id>/tracks")
    def job_tracks_route(job_id: int):
        return _run(lambda: track_service.get_job_tracks(job_id))

    @blueprint.get("/tracks/orphaned")
    def orphaned_tracks_route():
        return _run(track_service.find_orphaned_tracks)

    # --- Jobs: mutations ---------------------------------------------------

    @blueprint.post("/job/<int:job_id>/reset")
    def reset_job_route(job_id: int):
        def _reset():
            return job_service.reset_job_status(job_id, status=_body().get("status", "waiting"))

        return _run(_reset)

    @blueprint.post("/job/<int:job_id>/update")
    def update_job_route(job_id: int):
        def _update():
            fields = _body().get("fields")
            if not isinstance(fields, dict):
                raise ValueError("fields must be a JSON object")
            return job_service.update_job(job_id, fields)

        return _run(_update)

    @blueprint.post("/job/<int:job_id>/abandon")
    def abandon_job_route(job_id: int):
        return _run(lambda: job_service.abandon_job(job_id, dry_run=_dry_run_flag()))

    @blueprint.delete("/job/<int:job_id>")
    def delete_job_route(job_id: int):
        return _run(lambda: job_service.delete_job(job_id, dry_run=_dry_run_flag()))

    @blueprint.post("/jobs/delete")
    def delete_jobs_route():
        def _delete_jobs():
            job_ids = _body().get("job_ids")
            if not isinstance(job_ids, list) or not all(isinstance(j, int) for j in job_ids):
                raise ValueError("job_ids must be a list of integers")
            return job_service.delete_jobs(job_ids, dry_run=_dry_run_flag())

        return _run(_delete_jobs)

    @blueprint.post("/jobs/delete-all")
    def delete_all_jobs_route():
        return _run(lambda: job_service.delete_all_jobs(dry_run=_dry_run_flag()))

    @blueprint.post("/jobs/clean")
    def clean_jobs_route():
        def _clean():
            job_ids = _body().get("job_ids")
            if job_ids is not None and (not isinstance(job_ids, list) or not all(isinstance(j, int) for j in job_ids)):
                raise ValueError("job_ids must be a list of integers or omitted")
            return job_service.clean_jobs(job_ids=job_ids, dry_run=_dry_run_flag())

        return _run(_clean)

    @blueprint.post("/reset-all")
    def reset_all_route():
        return _run(lambda: job_service.reset_all(dry_run=_dry_run_flag()))

    @blueprint.post("/track/<int:track_id>/reset")
    def reset_track_route(track_id: int):
        return _run(lambda: track_service.reset_track_state(track_id))

    # --- Fixtures ----------------------------------------------------------

    @blueprint.post("/fixtures/job")
    def create_fixture_job_route():
        def _fixture_job():
            return test_fixture_service.create_test_job(device_path=_body().get("device_path", "/dev/sr0"))

        return _run(_fixture_job)

    @blueprint.post("/fixtures/track")
    def insert_fixture_track_route():
        def _fixture_track():
            return test_fixture_service.insert_test_track(int(_body().get("job_id", 0)))

        return _run(_fixture_track)

    # --- UI inspection -----------------------------------------------------

    @blueprint.get("/view")
    def view_route():
        def _view():
            return ui_inspector.capture_view(
                path=request.args.get("path", "/"),
                query={key: value for key, value in request.args.items() if key != "path"},
            )

        return _run(_view)

    @blueprint.post("/inspect-element")
    def inspect_element_route():
        def _inspect():
            payload = _body()
            return ui_inspector.inspect_element(
                snapshot_id=payload.get("snapshot_id"),
                path=payload.get("path"),
                selector=payload.get("selector"),
                visible_text=payload.get("visible_text"),
                test_id=payload.get("test_id"),
            )

        return _run(_inspect)

    @blueprint.get("/find-element")
    def find_element_route():
        def _find():
            return ui_inspector.find_element_by_text(
                text=request.args.get("text", ""),
                path=request.args.get("path"),
                snapshot_id=request.args.get("snapshot_id"),
            )

        return _run(_find)

    @blueprint.post("/reload")
    def reload_view_route():
        def _reload():
            payload = _body()
            return ui_inspector.reload_dev_view(
                path=payload.get("path", "/"),
                query={key: value for key, value in payload.items() if key != "path"},
            )

        return _run(_reload)

    @blueprint.post("/compare")
    def compare_views_route():
        def _compare():
            payload = _body()
            before_id = payload.get("before_id") or payload.get("before")
            after_id = payload.get("after_id") or payload.get("after")
            if not before_id or not after_id:
                raise ValueError("before_id= and after_id= (snapshot ids) are required")
            return ui_inspector.compare_view_states(before_id, after_id)

        return _run(_compare)

    # --- Dev loop ----------------------------------------------------------

    @blueprint.post("/exec/tests")
    def run_tests_route():
        def _tests():
            payload = _body()
            return exec_service.run_tests(
                paths=payload.get("paths"),
                verbose=payload.get("verbose", True),
                maxfail=payload.get("maxfail", 1),
            )

        return _run(_tests)

    @blueprint.get("/exec/find-tests")
    def find_tests_route():
        def _find_tests():
            return exec_service.find_tests_for_module(request.args.get("module", ""))

        return _run(_find_tests)

    @blueprint.post("/exec/run-for-file")
    def run_for_file_route():
        def _run_for_file():
            return exec_service.run_tests_for_file(test_path=_body().get("test_path", ""))

        return _run(_run_for_file)

    @blueprint.post("/exec/lint")
    def lint_route():
        def _lint():
            return exec_service.run_linter(paths=_body().get("paths"))

        return _run(_lint)

    @blueprint.post("/exec/coverage")
    def coverage_route():
        def _coverage():
            return exec_service.run_coverage(paths=_body().get("paths"))

        return _run(_coverage)

    @blueprint.post("/exec/integrity")
    def integrity_route():
        return _run(exec_service.check_test_integrity)

    # --- Bugs, audit and proxy ---------------------------------------------

    @blueprint.get("/tools/mutations")
    def mutations_route():
        return _run(mutation_audit_service.list_tool_mutations)

    @blueprint.get("/bugs/db-integrity")
    def db_integrity_route():
        return _run(bug_finder_service.check_db_integrity)

    @blueprint.get("/bugs/job-consistency")
    def job_consistency_route():
        return _run(bug_finder_service.check_job_consistency)

    @blueprint.get("/bugs/route-health")
    def route_health_route():
        return _run(bug_finder_service.check_route_health)

    @blueprint.post("/bugs/type-check")
    def type_check_route():
        return _run(bug_finder_service.run_type_check)

    @blueprint.post("/request")
    def proxy_route():
        def _proxy():
            payload = _body()
            return proxy_service.make_http_request(
                method=payload.get("method", "GET"),
                path=payload.get("path", "/"),
                body=payload.get("body"),
            )

        return _run(_proxy)

    # Log analysis (ported from v2: filter, search, stats, exceptions)
    @blueprint.get("/logs/job/<int:job_id>")
    def logs_for_job_route(job_id: int):
        def _logs_for_job():
            return log_analysis_service.get_logs_for_job(
                job_id=job_id,
                limit=int(request.args.get("limit", 200)),
                levels=_csv_arg("levels"),
            )

        return _run(_logs_for_job)

    @blueprint.get("/logs/search")
    def logs_search_route():
        def _logs_search():
            return log_analysis_service.search_logs(
                query=request.args.get("query", ""),
                limit=int(request.args.get("limit", 100)),
                levels=_csv_arg("levels"),
            )

        return _run(_logs_search)

    @blueprint.get("/logs/stats")
    def logs_stats_route():
        def _logs_stats():
            return log_analysis_service.get_log_stats(
                lines_to_scan=int(request.args.get("lines", 1000))
            )

        return _run(_logs_stats)

    @blueprint.get("/logs/exceptions")
    def logs_exceptions_route():
        def _logs_exceptions():
            return log_analysis_service.get_recent_exceptions(
                limit=int(request.args.get("limit", 20))
            )

        return _run(_logs_exceptions)

    # Job outputs and completion (ported from v2)
    @blueprint.get("/job/<int:job_id>/outputs")
    def job_outputs_route(job_id: int):
        def _job_outputs():
            return completion_service.list_job_outputs(job_id=job_id)

        return _run(_job_outputs)

    @blueprint.get("/job/<int:job_id>/completion")
    def job_completion_route(job_id: int):
        def _job_completion():
            return completion_service.validate_job_completion(job_id=job_id)

        return _run(_job_completion)

    # Media probing and metadata lookup (ported from v2)
    @blueprint.get("/media/probe")
    def media_probe_route():
        def _media_probe():
            return media_probe_service.probe_media_file(
                job_id=_int_arg("job_id"),
                path=request.args.get("path"),
            )

        return _run(_media_probe)

    @blueprint.get("/metadata/test")
    def metadata_test_route():
        def _metadata_test():
            imdb_id = request.args.get("imdb_id", "")
            if not imdb_id:
                raise ValueError("imdb_id required")
            return metadata_service.test_metadata_lookup(imdb_id=imdb_id)

        return _run(_metadata_test)

    # Fixture replay (ported from v2, without transitions - v3 has no model)
    @blueprint.post("/jobs/replay")
    def jobs_replay_route():
        def _jobs_replay():
            payload = _body()
            return replay_service.replay_job_fixture(payload)

        return _run(_jobs_replay)
