"""
Devtools HTTP client - speaks to the /__devtools JSON API of a running ARM UI.

The MCP server uses this client exclusively; nothing here imports ARM
code, so the devtools can run from any host with HTTP access to ARM.
"""
from __future__ import annotations

from typing import Any

import requests

# Keep-alive across calls on the MCP -> ARM hop
_SESSION = requests.Session()

_HTTP_TIMEOUTS: dict[str, int] = {
    "default": 30,
}


class DevtoolsHTTPError(Exception):
    """Raised when the devtools API returns an error."""


def _request(method: str, base_url: str, path: str, *, params: dict[str, Any] | None = None,
             json_body: dict[str, Any] | None = None, timeout: int | None = None) -> Any:
    """
    Call a /__devtools endpoint and unwrap the response envelope.

    Args:
        method: HTTP method
        base_url: base URL of the ARM UI, e.g. http://127.0.0.1:8081
        path: path including the /__devtools prefix
        params: query parameters
        json_body: JSON body for POST requests
        timeout: request timeout in seconds

    Returns:
        The ``data`` payload of the envelope

    Raises:
        DevtoolsHTTPError: on HTTP errors or success=false envelopes
    """
    url = f"{base_url}{path}"
    try:
        response = _SESSION.request(method, url, params=params, json=json_body,
                                    timeout=timeout or _HTTP_TIMEOUTS["default"])
    except requests.RequestException as error:
        raise DevtoolsHTTPError(f"could not reach {url}: {error}") from error
    if response.status_code >= 400:
        raise DevtoolsHTTPError(f"HTTP {response.status_code} from {path}")
    try:
        payload = response.json()
    except ValueError as error:
        raise DevtoolsHTTPError(f"non-JSON response from {path}") from error
    if not isinstance(payload, dict) or payload.get("success") is not True:
        errors = payload.get("errors") if isinstance(payload, dict) else None
        raise DevtoolsHTTPError(f"{path} failed: {errors or payload}")
    return payload.get("data")


class DevtoolsClient:
    """Typed client for the devtools API endpoints."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def get_app_state(self) -> Any:
        return _request("GET", self.base_url, "/__devtools/state")

    def get_recent_logs(self, limit: int = 100, source: str | None = None, since: str | None = None) -> Any:
        params: dict[str, Any] = {"limit": limit}
        if source:
            params["source"] = source
        if since:
            params["since"] = since
        return _request("GET", self.base_url, "/__devtools/logs", params=params)

    def list_routes(self) -> Any:
        return _request("GET", self.base_url, "/__devtools/routes")

    def query_db(self, model: str, filters: dict[str, Any] | None = None, limit: int = 50) -> Any:
        import json
        params = {"model": model, "limit": limit}
        if filters:
            params["filters"] = json.dumps(filters)
        return _request("GET", self.base_url, "/__devtools/db", params=params)

    def describe_model(self, model: str) -> Any:
        return _request("GET", self.base_url, "/__devtools/describe-model", params={"model": model})

    def get_table_counts(self) -> Any:
        return _request("GET", self.base_url, "/__devtools/db/table-counts")

    def get_db_status(self) -> Any:
        return _request("GET", self.base_url, "/__devtools/db/status")

    def get_app_config(self) -> Any:
        return _request("GET", self.base_url, "/__devtools/config")

    def get_config_value(self, key: str) -> Any:
        return _request("GET", self.base_url, "/__devtools/config/value", params={"key": key})

    def set_config_value(self, key: str, value: Any) -> Any:
        return _request("POST", self.base_url, "/__devtools/config/value", json_body={"key": key, "value": value})

    def get_tool_versions(self) -> Any:
        return _request("GET", self.base_url, "/__devtools/system/tool-versions")

    def check_disk_space(self) -> Any:
        return _request("GET", self.base_url, "/__devtools/system/disk-space")

    def get_process_list(self) -> Any:
        return _request("GET", self.base_url, "/__devtools/system/processes")

    def get_config_paths(self) -> Any:
        return _request("GET", self.base_url, "/__devtools/system/config-paths")

    # --- Jobs: read ---

    def get_job(self, job_id: int) -> Any:
        return _request("GET", self.base_url, f"/__devtools/job/{job_id}")

    def get_jobs_by_status(self, status: str, limit: int = 500) -> Any:
        return _request("GET", self.base_url, "/__devtools/jobs/by-status", params={"status": status, "limit": limit})

    def get_recent_jobs(self, limit: int = 25) -> Any:
        return _request("GET", self.base_url, "/__devtools/jobs/recent", params={"limit": limit})

    def export_job_as_json(self, job_id: int) -> Any:
        return _request("GET", self.base_url, f"/__devtools/job/{job_id}/export")

    def get_job_tracks(self, job_id: int) -> Any:
        return _request("GET", self.base_url, f"/__devtools/job/{job_id}/tracks")

    def find_orphaned_tracks(self) -> Any:
        return _request("GET", self.base_url, "/__devtools/tracks/orphaned")

    # --- Jobs: mutations ---

    def reset_job_status(self, job_id: int, status: str = "waiting") -> Any:
        return _request("POST", self.base_url, f"/__devtools/job/{job_id}/reset", json_body={"status": status})

    def update_job(self, job_id: int, fields: dict[str, Any]) -> Any:
        return _request("POST", self.base_url, f"/__devtools/job/{job_id}/update", json_body={"fields": fields})

    def abandon_job(self, job_id: int, dry_run: bool = False) -> Any:
        return _request("POST", self.base_url, f"/__devtools/job/{job_id}/abandon", json_body={"dry_run": dry_run})

    def delete_job(self, job_id: int, dry_run: bool = False) -> Any:
        return _request("DELETE", self.base_url, f"/__devtools/job/{job_id}", json_body={"dry_run": dry_run})

    def delete_jobs(self, job_ids: list[int], dry_run: bool = False) -> Any:
        return _request("POST", self.base_url, "/__devtools/jobs/delete", json_body={"job_ids": job_ids, "dry_run": dry_run})

    def delete_all_jobs(self, dry_run: bool = False) -> Any:
        return _request("POST", self.base_url, "/__devtools/jobs/delete-all", json_body={"dry_run": dry_run})

    def clean_jobs(self, job_ids: list[int] | None = None, dry_run: bool = False) -> Any:
        body: dict[str, Any] = {"dry_run": dry_run}
        if job_ids is not None:
            body["job_ids"] = job_ids
        return _request("POST", self.base_url, "/__devtools/jobs/clean", json_body=body)

    def reset_all(self, dry_run: bool = False) -> Any:
        return _request("POST", self.base_url, "/__devtools/reset-all", json_body={"dry_run": dry_run})

    def reset_track_state(self, track_id: int) -> Any:
        return _request("POST", self.base_url, f"/__devtools/track/{track_id}/reset")

    # --- Fixtures ---

    def create_test_job(self, device_path: str = "/dev/sr0") -> Any:
        return _request("POST", self.base_url, "/__devtools/fixtures/job", json_body={"device_path": device_path})

    def insert_test_track(self, job_id: int) -> Any:
        return _request("POST", self.base_url, "/__devtools/fixtures/track", json_body={"job_id": job_id})

    # --- UI inspection ---

    def inspect_current_view(self, path: str = "/", query: dict[str, Any] | None = None) -> Any:
        params: dict[str, Any] = {"path": path}
        if query:
            params.update(query)
        return _request("GET", self.base_url, "/__devtools/view", params=params)

    def inspect_element(self, payload: dict[str, Any]) -> Any:
        return _request("POST", self.base_url, "/__devtools/inspect-element", json_body=payload)

    def find_element_by_text(self, text: str, path: str | None = None, snapshot_id: str | None = None) -> Any:
        params: dict[str, Any] = {"text": text}
        if path:
            params["path"] = path
        if snapshot_id:
            params["snapshot_id"] = snapshot_id
        return _request("GET", self.base_url, "/__devtools/find-element", params=params)

    def reload_dev_view(self, path: str = "/", query: dict[str, Any] | None = None) -> Any:
        body: dict[str, Any] = {"path": path}
        if query:
            body.update(query)
        return _request("POST", self.base_url, "/__devtools/reload", json_body=body)

    def compare_view_states(self, before_id: str, after_id: str) -> Any:
        return _request("POST", self.base_url, "/__devtools/compare", json_body={"before_id": before_id, "after_id": after_id})

    # --- Dev loop ---

    def run_tests(self, paths: list[str] | None = None, verbose: bool = True, maxfail: int = 1) -> Any:
        body: dict[str, Any] = {"verbose": verbose, "maxfail": maxfail}
        if paths:
            body["paths"] = paths
        return _request("POST", self.base_url, "/__devtools/exec/tests", json_body=body, timeout=600)

    def find_tests_for_module(self, module_name: str) -> Any:
        return _request("GET", self.base_url, "/__devtools/exec/find-tests", params={"module": module_name})

    def run_tests_for_file(self, test_path: str, verbose: bool = True) -> Any:
        return _request("POST", self.base_url, "/__devtools/exec/run-for-file",
                        json_body={"test_path": test_path, "verbose": verbose}, timeout=600)

    def run_linter(self, paths: list[str] | None = None) -> Any:
        body: dict[str, Any] = {}
        if paths:
            body["paths"] = paths
        return _request("POST", self.base_url, "/__devtools/exec/lint", json_body=body, timeout=300)

    def run_coverage(self, paths: list[str] | None = None) -> Any:
        body: dict[str, Any] = {}
        if paths:
            body["paths"] = paths
        return _request("POST", self.base_url, "/__devtools/exec/coverage", json_body=body, timeout=600)

    def check_test_integrity(self) -> Any:
        return _request("POST", self.base_url, "/__devtools/exec/integrity")

    # --- Bugs, audit and proxy ---

    def list_tool_mutations(self) -> Any:
        return _request("GET", self.base_url, "/__devtools/tools/mutations")

    def check_db_integrity(self) -> Any:
        return _request("GET", self.base_url, "/__devtools/bugs/db-integrity")

    def check_job_consistency(self) -> Any:
        return _request("GET", self.base_url, "/__devtools/bugs/job-consistency")

    def check_route_health(self) -> Any:
        return _request("GET", self.base_url, "/__devtools/bugs/route-health", timeout=120)

    def run_type_check(self) -> Any:
        return _request("POST", self.base_url, "/__devtools/bugs/type-check", timeout=600)

    def make_http_request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        return _request("POST", self.base_url, "/__devtools/request",
                        json_body={"method": method, "path": path, "body": body})

    # --- Log analysis, outputs, media and metadata (v2 backlog ports) ---

    def get_logs_for_job(self, job_id: int, limit: int = 200, levels: list[str] | None = None) -> Any:
        params: dict[str, Any] = {"limit": limit}
        if levels:
            params["levels"] = ",".join(levels)
        return _request("GET", self.base_url, f"/__devtools/logs/job/{job_id}", params=params)

    def search_logs(self, query: str, limit: int = 100, levels: list[str] | None = None) -> Any:
        params: dict[str, Any] = {"query": query, "limit": limit}
        if levels:
            params["levels"] = ",".join(levels)
        return _request("GET", self.base_url, "/__devtools/logs/search", params=params)

    def get_log_stats(self, lines_to_scan: int = 1000) -> Any:
        return _request("GET", self.base_url, "/__devtools/logs/stats", params={"lines": lines_to_scan})

    def get_recent_exceptions(self, limit: int = 20) -> Any:
        return _request("GET", self.base_url, "/__devtools/logs/exceptions", params={"limit": limit})

    def list_job_outputs(self, job_id: int) -> Any:
        return _request("GET", self.base_url, f"/__devtools/job/{job_id}/outputs")

    def validate_job_completion(self, job_id: int) -> Any:
        return _request("GET", self.base_url, f"/__devtools/job/{job_id}/completion")

    def probe_media_file(self, job_id: int | None = None, path: str | None = None) -> Any:
        params: dict[str, Any] = {}
        if job_id is not None:
            params["job_id"] = job_id
        if path:
            params["path"] = path
        return _request("GET", self.base_url, "/__devtools/media/probe", params=params, timeout=120)

    def test_metadata_lookup(self, imdb_id: str) -> Any:
        return _request("GET", self.base_url, "/__devtools/metadata/test", params={"imdb_id": imdb_id}, timeout=120)

    def replay_job_fixture(self, fixture: dict[str, Any]) -> Any:
        return _request("POST", self.base_url, "/__devtools/jobs/replay", json_body=fixture)
