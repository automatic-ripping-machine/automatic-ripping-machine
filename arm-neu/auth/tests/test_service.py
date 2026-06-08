"""Tests for auth service CRUD operations."""

import json

import pytest

from arm_auth.service import AuthService, UserInfo, GroupInfo
from arm_auth.models import User, Group
from arm_auth.scopes import DEFAULT_GROUPS


class TestAuthServiceInit:
    def test_seed_default_groups(self, auth_db):
        svc = AuthService(auth_db)
        svc.seed_defaults()

        with auth_db.session() as s:
            groups = s.query(Group).all()
            names = {g.name for g in groups}
            assert "admin" in names
            assert "user" in names

    def test_seed_defaults_idempotent(self, auth_db):
        svc = AuthService(auth_db)
        svc.seed_defaults()
        svc.seed_defaults()

        with auth_db.session() as s:
            count = s.query(Group).count()
            assert count == len(DEFAULT_GROUPS)


class TestUserCRUD:
    @pytest.fixture(autouse=True)
    def setup(self, auth_db):
        self.db = auth_db
        self.svc = AuthService(auth_db)
        self.svc.seed_defaults()

    def test_create_user(self):
        user = self.svc.create_user("admin", "secret", "admin@arm.local", "admin")
        assert user.id is not None
        assert user.username == "admin"
        assert user.email == "admin@arm.local"
        assert user.password_hash.startswith("$2b$")
        assert len(user.groups) == 1
        assert user.groups[0].name == "admin"

    def test_create_user_default_group(self):
        user = self.svc.create_user("viewer", "secret")
        assert len(user.groups) == 1
        assert user.groups[0].name == "user"

    def test_create_duplicate_username_raises(self):
        self.svc.create_user("admin", "secret")
        with pytest.raises(ValueError, match="already exists"):
            self.svc.create_user("admin", "other")

    def test_list_users(self):
        self.svc.create_user("alice", "pw1")
        self.svc.create_user("bob", "pw2")
        users = self.svc.list_users()
        assert len(users) == 2
        names = {u.username for u in users}
        assert names == {"alice", "bob"}

    def test_get_user_by_username(self):
        self.svc.create_user("admin", "secret")
        user = self.svc.get_user("admin")
        assert user is not None
        assert user.username == "admin"

    def test_get_user_not_found(self):
        assert self.svc.get_user("ghost") is None

    def test_update_user(self):
        user = self.svc.create_user("admin", "secret")
        updated = self.svc.update_user(user.id, email="new@arm.local", group_name="user")
        assert updated.email == "new@arm.local"
        assert updated.groups[0].name == "user"

    def test_update_password(self):
        user = self.svc.create_user("admin", "old")
        self.svc.update_password(user.id, "new")
        from arm_auth.passwords import verify_password
        with self.db.session() as s:
            refreshed = s.get(User, user.id)
            assert verify_password("new", refreshed.password_hash)
            assert not verify_password("old", refreshed.password_hash)

    def test_delete_user(self):
        user = self.svc.create_user("temp", "pw")
        self.svc.delete_user(user.id)
        assert self.svc.get_user("temp") is None

    def test_delete_last_admin_raises(self):
        user = self.svc.create_user("admin", "pw", group_name="admin")
        with pytest.raises(ValueError, match="last admin"):
            self.svc.delete_user(user.id)

    def test_verify_credentials(self):
        self.svc.create_user("admin", "secret")
        user = self.svc.verify_credentials("admin", "secret")
        assert user is not None
        assert user.username == "admin"

    def test_verify_credentials_wrong_password(self):
        self.svc.create_user("admin", "secret")
        assert self.svc.verify_credentials("admin", "wrong") is None

    def test_verify_credentials_unknown_user(self):
        assert self.svc.verify_credentials("ghost", "pw") is None

    def test_create_user_nonexistent_group(self):
        with pytest.raises(ValueError, match="does not exist"):
            self.svc.create_user("x", "pw", group_name="nonexistent")

    def test_update_user_nonexistent_id(self):
        with pytest.raises(ValueError):
            self.svc.update_user(9999, email="x")

    def test_update_password_nonexistent_id(self):
        with pytest.raises(ValueError):
            self.svc.update_password(9999, "pw")

    def test_delete_user_nonexistent_id(self):
        with pytest.raises(ValueError):
            self.svc.delete_user(9999)

    def test_delete_non_admin_with_admins_existing(self):
        self.svc.create_user("admin", "pw", group_name="admin")
        regular = self.svc.create_user("regular", "pw", group_name="user")
        self.svc.delete_user(regular.id)
        assert self.svc.get_user("regular") is None
        assert self.svc.get_user("admin") is not None

    def test_delete_one_of_two_admins(self):
        admin1 = self.svc.create_user("admin1", "pw", group_name="admin")
        self.svc.create_user("admin2", "pw", group_name="admin")
        self.svc.delete_user(admin1.id)
        assert self.svc.get_user("admin1") is None
        assert self.svc.get_user("admin2") is not None

    def test_verify_credentials_inactive_user(self):
        user = self.svc.create_user("admin", "secret")
        self.svc.update_user(user.id, active=False)
        assert self.svc.verify_credentials("admin", "secret") is None


class TestInputValidation:
    @pytest.fixture(autouse=True)
    def setup(self, auth_db):
        self.db = auth_db
        self.svc = AuthService(auth_db)
        self.svc.seed_defaults()

    def test_create_user_empty_username(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            self.svc.create_user("", "password")

    def test_create_user_whitespace_only_username(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            self.svc.create_user("   ", "password")

    def test_create_user_username_with_colon(self):
        with pytest.raises(ValueError, match="invalid characters"):
            self.svc.create_user("user:name", "password")

    def test_create_user_username_with_newline(self):
        with pytest.raises(ValueError, match="invalid characters"):
            self.svc.create_user("user\nname", "password")

    def test_create_user_username_with_null(self):
        with pytest.raises(ValueError, match="invalid characters"):
            self.svc.create_user("user\x00name", "password")

    def test_create_user_empty_password(self):
        with pytest.raises(ValueError, match="Password cannot be empty"):
            self.svc.create_user("validuser", "")

    def test_create_user_long_password(self):
        long_pw = "a" * 73  # >72 bytes
        with pytest.raises(ValueError, match="too long"):
            self.svc.create_user("validuser", long_pw)

    def test_create_user_username_too_long(self):
        with pytest.raises(ValueError, match="too long"):
            self.svc.create_user("a" * 151, "password")


class TestUserInfoDataclass:
    @pytest.fixture(autouse=True)
    def setup(self, auth_db):
        self.db = auth_db
        self.svc = AuthService(auth_db)
        self.svc.seed_defaults()

    def test_list_users_shared_group(self):
        """Two users in the same group should not crash list_users."""
        self.svc.create_user("alice", "pw1", group_name="user")
        self.svc.create_user("bob", "pw2", group_name="user")
        users = self.svc.list_users()
        assert len(users) == 2
        names = {u.username for u in users}
        assert names == {"alice", "bob"}
        # Both should have group info
        for u in users:
            assert len(u.groups) == 1
            assert u.groups[0].name == "user"

    def test_detached_user_has_scope(self):
        """UserInfo returned by service should support has_scope."""
        user = self.svc.create_user("admin", "pw", group_name="admin")
        assert isinstance(user, UserInfo)
        assert user.has_scope("users:manage") is True
        assert user.has_scope("anything") is True  # admin has wildcard

    def test_detached_user_has_scope_limited(self):
        """Non-admin UserInfo should not have admin scopes."""
        user = self.svc.create_user("viewer", "pw", group_name="user")
        assert isinstance(user, UserInfo)
        assert user.has_scope("jobs:read") is True
        assert user.has_scope("users:manage") is False

    def test_scope_list_corrupted_json(self):
        """Group with invalid JSON scopes should return empty list."""
        with self.db.session() as s:
            group = Group(name="broken", scopes="not valid json")
            s.add(group)
            s.flush()
            assert group.scope_list == []


class TestCLIFreshDB:
    def test_add_user_cli_fresh_db(self, tmp_path):
        """add-user on a path with no existing DB should work (create_all)."""
        from click.testing import CliRunner
        from arm_auth.cli import main

        db_path = str(tmp_path / "fresh.db")
        users_file = str(tmp_path / "users.txt")

        runner = CliRunner()
        # First init to seed groups
        result = runner.invoke(main, [
            "init", "--db-path", db_path,
            "--admin-password", "secret", "--users-file", users_file,
        ])
        assert result.exit_code == 0

        # Remove the DB to simulate fresh state
        import os
        os.unlink(db_path)

        # add-user on fresh DB should call create_all and then fail
        # because no groups exist (tables created but not seeded)
        result = runner.invoke(main, [
            "add-user", "--db-path", db_path,
            "--username", "newuser", "--password", "pw",
            "--users-file", users_file,
        ])
        # Should fail because groups don't exist yet (no seed_defaults)
        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_add_user_cli_fresh_db_after_init(self, tmp_path):
        """add-user after init should work on a fresh DB path."""
        from click.testing import CliRunner
        from arm_auth.cli import main

        db_path = str(tmp_path / "new.db")
        users_file = str(tmp_path / "users.txt")

        runner = CliRunner()
        # Init creates tables + seeds groups + creates admin
        result = runner.invoke(main, [
            "init", "--db-path", db_path,
            "--admin-password", "secret", "--users-file", users_file,
        ])
        assert result.exit_code == 0

        # Now add-user should work
        result = runner.invoke(main, [
            "add-user", "--db-path", db_path,
            "--username", "viewer", "--password", "pw",
            "--users-file", users_file,
        ])
        assert result.exit_code == 0
        assert "Created user" in result.output
