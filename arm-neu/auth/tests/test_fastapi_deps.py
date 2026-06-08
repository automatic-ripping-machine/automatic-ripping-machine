"""Tests for FastAPI auth dependencies."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from arm_auth.service import AuthService
from arm_auth.fastapi.dependencies import create_auth_dependencies


class TestAuthDisabled:
    def test_get_current_user_returns_synthetic_admin(self, auth_db):
        deps = create_auth_dependencies(auth_db, enabled=False)
        app = FastAPI()

        @app.get("/test")
        async def endpoint(user=deps.get_current_user):
            return {"username": user.username, "scopes": list(user.all_scopes)}

        client = TestClient(app)
        resp = client.get("/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "anonymous"
        assert "*" in data["scopes"]

    def test_require_scope_passes(self, auth_db):
        deps = create_auth_dependencies(auth_db, enabled=False)
        app = FastAPI()

        @app.get("/admin")
        async def endpoint(user=deps.require_scope("users:manage")):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/admin")
        assert resp.status_code == 200


class TestAuthEnabled:
    @pytest.fixture(autouse=True)
    def setup(self, auth_db):
        self.db = auth_db
        svc = AuthService(auth_db)
        svc.seed_defaults()
        svc.create_user("admin", "pw", group_name="admin")
        svc.create_user("viewer", "pw", group_name="user")
        self.deps = create_auth_dependencies(auth_db, enabled=True)

    def test_no_header_returns_401(self):
        app = FastAPI()

        @app.get("/test")
        async def endpoint(user=self.deps.get_current_user):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/test")
        assert resp.status_code == 401

    def test_valid_user_header(self):
        app = FastAPI()

        @app.get("/test")
        async def endpoint(user=self.deps.get_current_user):
            return {"username": user.username}

        client = TestClient(app)
        resp = client.get("/test", headers={"Remote-User": "admin"})
        assert resp.status_code == 200
        assert resp.json()["username"] == "admin"

    def test_unknown_user_returns_401(self):
        app = FastAPI()

        @app.get("/test")
        async def endpoint(user=self.deps.get_current_user):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/test", headers={"Remote-User": "ghost"})
        assert resp.status_code == 401

    def test_require_scope_allowed(self):
        app = FastAPI()

        @app.get("/admin")
        async def endpoint(user=self.deps.require_scope("users:manage")):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/admin", headers={"Remote-User": "admin"})
        assert resp.status_code == 200

    def test_require_scope_denied(self):
        app = FastAPI()

        @app.get("/admin")
        async def endpoint(user=self.deps.require_scope("users:manage")):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/admin", headers={"Remote-User": "viewer"})
        assert resp.status_code == 403

    def test_inactive_user_returns_401(self):
        svc = AuthService(self.db)
        user = svc.get_user("viewer")
        svc.update_user(user.id, active=False)

        app = FastAPI()

        @app.get("/test")
        async def endpoint(user=self.deps.get_current_user):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/test", headers={"Remote-User": "viewer"})
        assert resp.status_code == 401

    def test_require_scope_no_header_returns_401(self):
        app = FastAPI()

        @app.get("/admin")
        async def endpoint(user=self.deps.require_scope("users:manage")):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/admin")
        assert resp.status_code == 401

    def test_require_scope_inactive_user_returns_401(self):
        svc = AuthService(self.db)
        user = svc.get_user("viewer")
        svc.update_user(user.id, active=False)

        app = FastAPI()

        @app.get("/admin")
        async def endpoint(user=self.deps.require_scope("users:manage")):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/admin", headers={"Remote-User": "viewer"})
        assert resp.status_code == 401
