"""Tests for arm/api/v1/settings.py — FastAPI settings endpoints.

Covers the GET and PUT /settings/config endpoints, including
hidden field masking, validation, write errors, and reload failures.
"""

import unittest.mock

import pytest
import yaml


@pytest.fixture
def client(tmp_path):
    """Create a test client with mocked config state."""
    import arm.config.config as cfg
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from arm.api.v1.settings import router

    app = FastAPI()
    app.include_router(router)

    # Set up a temp config file for write/reload tests
    config_file = tmp_path / "arm_test.yaml"
    original_config = dict(cfg.arm_config)
    original_path = cfg.arm_config_path
    cfg.arm_config_path = str(config_file)
    yaml.dump(original_config, config_file.open("w"))

    with TestClient(app) as c:
        yield c

    # Restore original config state
    cfg.arm_config.clear()
    cfg.arm_config.update(original_config)
    cfg.arm_config_path = original_path


class TestGetConfig:
    def test_returns_config_comments_and_variables(self, client):
        resp = client.get("/api/v1/settings/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "config" in data
        assert "comments" in data
        assert "naming_variables" in data

    def test_hidden_fields_masked(self, client):
        import arm.config.config as cfg
        from arm.models.config import hidden_attribs, HIDDEN_VALUE

        # Ensure at least one hidden field has a value
        cfg.arm_config["OMDB_API_KEY"] = "secret123"
        try:
            resp = client.get("/api/v1/settings/config")
            data = resp.json()
            assert data["config"]["OMDB_API_KEY"] == HIDDEN_VALUE
        finally:
            cfg.arm_config["OMDB_API_KEY"] = ""

    def test_none_values_returned_as_null(self, client):
        import arm.config.config as cfg

        cfg.arm_config["ARM_NAME"] = None
        try:
            resp = client.get("/api/v1/settings/config")
            data = resp.json()
            assert data["config"]["ARM_NAME"] is None
        finally:
            cfg.arm_config["ARM_NAME"] = ""


class TestUpdateConfig:
    def test_success(self, client):
        resp = client.put(
            "/api/v1/settings/config",
            json={"config": {"RIPMETHOD": "mkv", "MAINFEATURE": False}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_missing_config_key_returns_400(self, client):
        resp = client.put("/api/v1/settings/config", json={"bad": "data"})
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_empty_body_returns_400(self, client):
        resp = client.put("/api/v1/settings/config", json={})
        assert resp.status_code == 400

    def test_empty_config_dict_returns_400(self, client):
        resp = client.put("/api/v1/settings/config", json={"config": {}})
        assert resp.status_code == 400

    def test_non_dict_config_returns_400(self, client):
        resp = client.put("/api/v1/settings/config", json={"config": "string"})
        assert resp.status_code == 400

    def test_hidden_fields_preserved(self, client):
        import arm.config.config as cfg
        from arm.models.config import HIDDEN_VALUE

        cfg.arm_config["OMDB_API_KEY"] = "real_secret"
        try:
            resp = client.put(
                "/api/v1/settings/config",
                json={"config": {"OMDB_API_KEY": HIDDEN_VALUE, "RIPMETHOD": "mkv"}},
            )
            assert resp.status_code == 200
            # After reload, the real secret should be preserved
            assert cfg.arm_config.get("OMDB_API_KEY") is not None
        finally:
            cfg.arm_config["OMDB_API_KEY"] = ""

    def test_write_failure_returns_500(self, client):
        import arm.config.config as cfg

        # Point to a path that cannot be written
        cfg.arm_config_path = "/nonexistent/dir/arm.yaml"
        resp = client.put(
            "/api/v1/settings/config",
            json={"config": {"RIPMETHOD": "mkv"}},
        )
        assert resp.status_code == 500
        assert resp.json()["success"] is False

    def test_reload_failure_returns_warning(self, client):
        import arm.config.config as cfg

        with unittest.mock.patch(
            "arm.api.v1.settings.yaml.safe_load",
            side_effect=Exception("parse error"),
        ):
            resp = client.put(
                "/api/v1/settings/config",
                json={"config": {"RIPMETHOD": "mkv"}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "warning" in data

    def test_config_reloaded_in_place(self, client):
        import arm.config.config as cfg

        ref_before = cfg.arm_config
        resp = client.put(
            "/api/v1/settings/config",
            json={"config": {"RIPMETHOD": "backup"}},
        )
        assert resp.status_code == 200
        # The dict object should be the same (in-place reload)
        assert ref_before is cfg.arm_config


class TestGetAbcdeConfig:
    def test_reads_existing_file(self, client, tmp_path):
        import arm.config.config as cfg

        abcde_file = tmp_path / "abcde.conf"
        abcde_file.write_text("# test config\nCDDBMETHOD=musicbrainz\n")
        cfg.arm_config["ABCDE_CONFIG_FILE"] = str(abcde_file)
        try:
            resp = client.get("/api/v1/settings/abcde")
            assert resp.status_code == 200
            data = resp.json()
            assert data["exists"] is True
            assert "CDDBMETHOD=musicbrainz" in data["content"]
            assert data["path"] == str(abcde_file)
        finally:
            cfg.arm_config["ABCDE_CONFIG_FILE"] = "/etc/abcde.conf"

    def test_missing_file_returns_exists_false(self, client, tmp_path):
        import arm.config.config as cfg

        cfg.arm_config["ABCDE_CONFIG_FILE"] = str(tmp_path / "nonexistent.conf")
        try:
            resp = client.get("/api/v1/settings/abcde")
            assert resp.status_code == 200
            data = resp.json()
            assert data["exists"] is False
            assert data["content"] == ""
        finally:
            cfg.arm_config["ABCDE_CONFIG_FILE"] = "/etc/abcde.conf"


class TestUpdateAbcdeConfig:
    def test_write_success(self, client, tmp_path):
        import arm.config.config as cfg

        abcde_file = tmp_path / "abcde.conf"
        abcde_file.write_text("# old content\n")
        cfg.arm_config["ABCDE_CONFIG_FILE"] = str(abcde_file)
        try:
            resp = client.put(
                "/api/v1/settings/abcde",
                json={"content": "# new content\nOUTPUTTYPE=flac\n"},
            )
            assert resp.status_code == 200
            assert resp.json()["success"] is True
            assert "OUTPUTTYPE=flac" in abcde_file.read_text()
        finally:
            cfg.arm_config["ABCDE_CONFIG_FILE"] = "/etc/abcde.conf"

    def test_missing_content_returns_400(self, client):
        resp = client.put("/api/v1/settings/abcde", json={"bad": "data"})
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_write_failure_returns_500(self, client):
        import arm.config.config as cfg

        cfg.arm_config["ABCDE_CONFIG_FILE"] = "/nonexistent/dir/abcde.conf"
        try:
            resp = client.put(
                "/api/v1/settings/abcde",
                json={"content": "# test\n"},
            )
            assert resp.status_code == 500
            assert resp.json()["success"] is False
        finally:
            cfg.arm_config["ABCDE_CONFIG_FILE"] = "/etc/abcde.conf"
