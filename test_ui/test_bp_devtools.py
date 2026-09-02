"""
Tests for the devtools blueprint (/__devtools).

The blueprint is registered only when ENABLE_DEVTOOLS is true in arm.yaml.
Tests skip with a clear message when the app was created without it.
"""
import pytest


@pytest.fixture(scope="module", autouse=True)
def _require_devtools(test_client, init_db):
    """
    Skip the module when the devtools blueprint was not registered, and ensure
    the test tables exist (v3's alembic chain does not create them on a fresh
    test database - conftest's init_db create_all is the v3 way).
    """
    response = test_client.get("/__devtools/state")
    if response.status_code == 404:
        pytest.skip("devtools blueprint not registered - set ENABLE_DEVTOOLS: true in arm.yaml")
    yield


class TestDevtoolsState:
    """GET /__devtools/state"""

    def test_state_envelope(self, test_client):
        response = test_client.get("/__devtools/state")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert payload["errors"] == []
        assert "timestamp" in payload

    def test_state_data_sections(self, test_client):
        data = test_client.get("/__devtools/state").get_json()["data"]
        for section in ("jobs", "drives", "services", "warnings", "safe_config"):
            assert section in data


class TestDevtoolsRoutes:
    """GET /__devtools/routes"""

    def test_lists_own_routes(self, test_client):
        payload = test_client.get("/__devtools/routes").get_json()
        assert payload["success"] is True
        paths = {route["path"] for route in payload["data"]["routes"]}
        assert "/__devtools/state" in paths
        assert "/login" in paths


class TestDevtoolsDb:
    """DB query endpoints"""

    @pytest.mark.usefixtures("init_db")
    def test_query_job_model(self, test_client):
        response = test_client.get("/__devtools/db?model=job")
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["model"] == "job"
        assert "count" in data
        assert isinstance(data["rows"], list)

    def test_query_unknown_model(self, test_client):
        response = test_client.get("/__devtools/db?model=nope")
        assert response.status_code == 400
        assert response.get_json()["success"] is False

    @pytest.mark.usefixtures("init_db")
    def test_describe_model(self, test_client):
        data = test_client.get("/__devtools/describe-model?model=job").get_json()["data"]
        assert data["table"] == "job"
        column_names = {column["name"] for column in data["columns"]}
        assert "job_id" in column_names

    @pytest.mark.usefixtures("init_db")
    def test_table_counts(self, test_client):
        data = test_client.get("/__devtools/db/table-counts").get_json()["data"]
        assert "job" in data["tables"]

    @pytest.mark.usefixtures("init_db")
    def test_db_status_mysql(self, test_client):
        data = test_client.get("/__devtools/db/status").get_json()["data"]
        assert data["server_version"]
        assert data["database"] == "arm_testing"
        assert data["host"]
        assert "job" in data["tables"]


class TestDevtoolsConfig:
    """Config endpoints"""

    def test_get_config_redacts_secrets(self, test_client):
        data = test_client.get("/__devtools/config").get_json()["data"]
        assert data["keys"]["LOGPATH"]
        assert data["keys"]["EMBY_PASSWORD"] == "<redacted>"

    def test_get_config_value(self, test_client):
        data = test_client.get("/__devtools/config/value?key=WEBSERVER_PORT").get_json()["data"]
        assert data["key"] == "WEBSERVER_PORT"

    def test_set_config_value_in_memory(self, test_client):
        from config import config as cfg

        original = cfg.arm_config["WEBSERVER_PORT"]
        try:
            response = test_client.post("/__devtools/config/value", json={"key": "WEBSERVER_PORT", "value": 9000})
            assert response.status_code == 200
            data = response.get_json()["data"]
            assert data["current"] == 9000
            reread = test_client.get("/__devtools/config/value?key=WEBSERVER_PORT").get_json()["data"]
            assert reread["value"] == 9000
        finally:
            cfg.arm_config["WEBSERVER_PORT"] = original

    def test_unknown_config_key(self, test_client):
        response = test_client.get("/__devtools/config/value?key=NOPE")
        assert response.status_code == 400


class TestDevtoolsSystem:
    """System endpoints"""

    def test_config_paths(self, test_client):
        payload = test_client.get("/__devtools/system/config-paths").get_json()
        assert payload["success"] is True
        assert "paths" in payload["data"]

    def test_disk_space(self, test_client):
        payload = test_client.get("/__devtools/system/disk-space").get_json()
        assert payload["success"] is True


class TestDevtoolsGate:
    """The per-request gate"""

    def test_disabled_returns_404(self, test_client):
        from config import config as cfg

        original = cfg.arm_config.get("ENABLE_DEVTOOLS")
        try:
            cfg.arm_config["ENABLE_DEVTOOLS"] = False
            response = test_client.get("/__devtools/state")
            assert response.status_code == 404
            assert response.get_json()["errors"] == ["devtools_disabled"]
        finally:
            if original is None:
                cfg.arm_config.pop("ENABLE_DEVTOOLS", None)
            else:
                cfg.arm_config["ENABLE_DEVTOOLS"] = original


class TestDevtoolsJobs:
    """Job queries and mutations through the devtools API"""

    def test_fixture_lifecycle(self, test_client):
        # Create a fixture job, verify it, then delete it
        created = test_client.post("/__devtools/fixtures/job", json={"device_path": "/dev/sr0"})
        assert created.status_code == 200
        job_id = created.get_json()["data"]["job_id"]

        fetched = test_client.get(f"/__devtools/job/{job_id}").get_json()["data"]
        assert fetched["title"] == "DEVTOOLS_FIXTURE Title"
        assert fetched["status"] == "waiting"
        assert fetched["config"] is not None

        deleted = test_client.delete(f"/__devtools/job/{job_id}")
        assert deleted.status_code == 200
        assert deleted.get_json()["data"]["removed"]["jobs"] == 1

        missing = test_client.get(f"/__devtools/job/{job_id}")
        assert missing.status_code == 400

    def test_delete_dry_run_keeps_job(self, test_client):
        created = test_client.post("/__devtools/fixtures/job", json={})
        job_id = created.get_json()["data"]["job_id"]
        try:
            dry_run = test_client.delete(f"/__devtools/job/{job_id}?dry_run=true")
            assert dry_run.status_code == 200
            assert dry_run.get_json()["data"]["dry_run"] is True
            still_there = test_client.get(f"/__devtools/job/{job_id}")
            assert still_there.status_code == 200
        finally:
            test_client.delete(f"/__devtools/job/{job_id}")

    def test_update_job_allowed_fields(self, test_client):
        created = test_client.post("/__devtools/fixtures/job", json={})
        job_id = created.get_json()["data"]["job_id"]
        try:
            updated = test_client.post(
                f"/__devtools/job/{job_id}/update",
                json={"fields": {"title": "Renamed by devtools", "year": "1999"}},
            )
            assert updated.status_code == 200
            fetched = test_client.get(f"/__devtools/job/{job_id}").get_json()["data"]
            assert fetched["title"] == "Renamed by devtools"
            assert fetched["year"] == "1999"
            rejected = test_client.post(
                f"/__devtools/job/{job_id}/update",
                json={"fields": {"status": "success"}},
            )
            assert rejected.status_code == 400
        finally:
            test_client.delete(f"/__devtools/job/{job_id}")

    def test_reset_job_status(self, test_client):
        created = test_client.post("/__devtools/fixtures/job", json={})
        job_id = created.get_json()["data"]["job_id"]
        try:
            reset = test_client.post(f"/__devtools/job/{job_id}/reset", json={"status": "active"})
            assert reset.status_code == 200
            assert reset.get_json()["data"]["status"] == "active"
        finally:
            test_client.delete(f"/__devtools/job/{job_id}")

    def test_track_fixture_and_export(self, test_client):
        created = test_client.post("/__devtools/fixtures/job", json={})
        job_id = created.get_json()["data"]["job_id"]
        try:
            track = test_client.post("/__devtools/fixtures/track", json={"job_id": job_id})
            assert track.status_code == 200
            track_id = track.get_json()["data"]["track_id"]

            tracks = test_client.get(f"/__devtools/job/{job_id}/tracks").get_json()["data"]
            assert tracks["count"] == 1
            assert tracks["pending"] == 1

            exported = test_client.get(f"/__devtools/job/{job_id}/export").get_json()["data"]
            assert exported["job"]["job_id"] == job_id
            assert len(exported["tracks"]) == 1

            reset_track = test_client.post(f"/__devtools/track/{track_id}/reset")
            assert reset_track.status_code == 200
            assert reset_track.get_json()["data"]["ripped"] is False
        finally:
            test_client.delete(f"/__devtools/job/{job_id}")

    def test_jobs_by_status_and_recent(self, test_client):
        by_status = test_client.get("/__devtools/jobs/by-status?status=waiting")
        assert by_status.status_code == 200
        assert "count" in by_status.get_json()["data"]
        recent = test_client.get("/__devtools/jobs/recent")
        assert recent.status_code == 200
        assert "jobs" in recent.get_json()["data"]

    def test_clean_jobs_skips_active(self, test_client):
        created = test_client.post("/__devtools/fixtures/job", json={})
        job_id = created.get_json()["data"]["job_id"]
        try:
            cleaned = test_client.post("/__devtools/jobs/clean", json={"job_ids": [job_id]})
            assert cleaned.status_code == 200
            assert cleaned.get_json()["data"]["skipped_not_terminal"] == [job_id]
        finally:
            test_client.delete(f"/__devtools/job/{job_id}")


class TestDevtoolsInspection:
    """Server-side UI inspection"""

    def test_view_snapshot(self, test_client):
        payload = test_client.get("/__devtools/view?path=/").get_json()
        assert "data" in payload, payload
        data = payload["data"]
        assert data["snapshot_id"]
        assert "endpoint" in data
        assert "interactive_elements" in data

    def test_find_element_by_text(self, test_client):
        data = test_client.get("/__devtools/find-element?text=ARM&path=/").get_json()["data"]
        assert "count" in data
        assert isinstance(data["elements"], list)

    def test_inspect_element_requires_selector(self, test_client):
        response = test_client.post("/__devtools/inspect-element", json={"path": "/"})
        assert response.status_code == 400

    def test_inspect_element_by_selector(self, test_client):
        response = test_client.post("/__devtools/inspect-element", json={"path": "/", "selector": "html"})
        assert response.status_code == 200
        assert response.get_json()["data"]["count"] >= 1

    def test_compare_requires_snapshot_ids(self, test_client):
        response = test_client.post("/__devtools/compare", json={})
        assert response.status_code == 400


class TestDevtoolsAuditAndBugs:
    """Mutation audit and bug finding"""

    def test_list_tool_mutations(self, test_client):
        data = test_client.get("/__devtools/tools/mutations").get_json()["data"]
        assert "read_only" in data["categories"]
        assert data["tools"]["delete_job"]["category"] == "destructive"

    @pytest.mark.usefixtures("init_db")
    def test_db_integrity(self, test_client):
        data = test_client.get("/__devtools/bugs/db-integrity").get_json()["data"]
        assert "job" in data["tables"]

    def test_job_consistency(self, test_client):
        payload = test_client.get("/__devtools/bugs/job-consistency").get_json()
        assert payload["success"] is True
        assert "findings" in payload["data"]

    def test_proxy_rejects_unsupported_method(self, test_client):
        # The proxy hits the real UI on localhost, which is absent in the test
        # container - the live path is verified against the running arm-ui.
        response = test_client.post("/__devtools/request", json={"method": "PUT", "path": "/json"})
        assert response.status_code == 400


class TestDevtoolsExecFixes:
    """Regression tests for dead-call fixes (type-check, coverage, find-tests, audit names)"""

    def test_find_tests_for_module_devtools_routes(self, test_client):
        data = test_client.get("/__devtools/exec/find-tests?module=ui.devtools.routes").get_json()["data"]
        assert "test_ui/test_bp_devtools.py" in data["tests"]

    def test_run_type_check_returns_install_hint(self, test_client):
        # pyright is not installed in the UI container - the route must
        # return the hint instead of a 500
        payload = test_client.post("/__devtools/bugs/type-check").get_json()
        assert payload["success"] is True
        assert "pyright" in payload["data"]["error"]

    def test_run_coverage_returns_install_hint(self, test_client):
        # pytest-cov is not installed in the UI container - the route must
        # return the hint instead of a raw pytest usage error
        payload = test_client.post("/__devtools/exec/coverage",
                                   json={"paths": ["arm/ui/devtools"]}).get_json()
        assert payload["success"] is True
        assert "pytest-cov" in payload["data"]["error"]

    def test_mutations_audit_names_actual_tools(self, test_client):
        data = test_client.get("/__devtools/tools/mutations").get_json()["data"]
        assert "run_coverage" in data["tools"]
        assert "get_test_coverage" not in data["tools"]


class TestDevtoolsBacklogPorts:
    """v2 backlog ports: log analysis, outputs, media, metadata, replay"""

    def test_logs_for_job_shape(self, test_client):
        result = test_client.get("/__devtools/logs/job/999999?limit=10")
        assert result.status_code == 200
        data = result.get_json()["data"]
        assert data["matched"] == 0
        assert data["entries"] == []
        assert data["job_id"] == 999999

    def test_search_logs(self, test_client):
        result = test_client.get("/__devtools/logs/search", query_string={"query": "ARM", "limit": "10"})
        assert result.status_code == 200
        assert "entries" in result.get_json()["data"]

    def test_log_stats(self, test_client):
        result = test_client.get("/__devtools/logs/stats?lines=100")
        assert result.status_code == 200
        data = result.get_json()["data"]
        assert "counts_by_level" in data
        assert data["lines_parsed"] + data["lines_unparsed"] == data["lines_scanned"]

    def test_recent_exceptions(self, test_client):
        result = test_client.get("/__devtools/logs/exceptions?limit=5")
        assert result.status_code == 200
        assert "exceptions" in result.get_json()["data"]

    def test_job_outputs_and_completion(self, test_client):
        created = test_client.post("/__devtools/fixtures/job", json={})
        job_id = created.get_json()["data"]["job_id"]
        try:
            outputs = test_client.get(f"/__devtools/job/{job_id}/outputs")
            assert outputs.status_code == 200
            assert outputs.get_json()["data"]["final_path"] is not None
            completion = test_client.get(f"/__devtools/job/{job_id}/completion")
            assert completion.status_code == 200
            completion_data = completion.get_json()["data"]
            assert "tracks" in completion_data
            assert "missing_outputs" in completion_data
        finally:
            test_client.delete(f"/__devtools/job/{job_id}")

    def test_job_outputs_unknown_job(self, test_client):
        result = test_client.get("/__devtools/job/999999/outputs")
        assert result.status_code == 400

    def test_probe_media_requires_arg(self, test_client):
        result = test_client.get("/__devtools/media/probe")
        assert result.status_code == 400

    def test_metadata_test_requires_imdb(self, test_client):
        result = test_client.get("/__devtools/metadata/test")
        assert result.status_code == 400

    def test_replay_roundtrip(self, test_client):
        created = test_client.post("/__devtools/fixtures/job", json={})
        job_id = created.get_json()["data"]["job_id"]
        new_id = None
        try:
            track = test_client.post("/__devtools/fixtures/track", json={"job_id": job_id})
            assert track.status_code == 200
            fixture = test_client.get(f"/__devtools/job/{job_id}/export").get_json()["data"]
            test_client.delete(f"/__devtools/job/{job_id}")
            replayed = test_client.post("/__devtools/jobs/replay", json=fixture)
            assert replayed.status_code == 200
            data = replayed.get_json()["data"]
            assert data["created"] is True
            assert data["track_count"] == 1
            new_id = data["job_id"]
            assert new_id != job_id
            fetched = test_client.get(f"/__devtools/job/{new_id}").get_json()["data"]
            assert fetched["title"] == "DEVTOOLS_FIXTURE Title"
            assert fetched["config"] is not None
        finally:
            if new_id is not None:
                test_client.delete(f"/__devtools/job/{new_id}")

    def test_replay_rejects_non_dict(self, test_client):
        result = test_client.post("/__devtools/jobs/replay", json=["not", "a", "dict"])
        assert result.status_code == 400
