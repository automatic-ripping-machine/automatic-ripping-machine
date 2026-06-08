"""Tests for Tinyauth user file generation."""

import pytest

from arm_auth.service import AuthService
from arm_auth.tinyauth.sync import generate_users_file, sync_users


class TestGenerateUsersFile:
    @pytest.fixture(autouse=True)
    def setup(self, auth_db):
        self.db = auth_db
        self.svc = AuthService(auth_db)
        self.svc.seed_defaults()

    def test_generates_users_file_content(self):
        self.svc.create_user("admin", "secret", group_name="admin")
        self.svc.create_user("viewer", "viewpw", group_name="user")

        content = generate_users_file(self.db)
        lines = content.strip().split("\n")

        assert len(lines) == 2
        usernames = {line.split(":")[0] for line in lines}
        assert usernames == {"admin", "viewer"}
        for line in lines:
            parts = line.split(":")
            assert len(parts) >= 2
            assert parts[1].startswith("$2b$")

    def test_skips_inactive_users(self):
        self.svc.create_user("inactive", "pw")
        inactive = self.svc.get_user("inactive")
        self.svc.update_user(inactive.id, active=False)
        self.svc.create_user("active", "pw")

        content = generate_users_file(self.db)
        lines = content.strip().split("\n")

        assert len(lines) == 1
        assert lines[0].startswith("active:")

    def test_empty_when_no_users(self):
        content = generate_users_file(self.db)
        assert content == "# no active users\n"

    def test_sync_writes_file(self, tmp_path):
        self.svc.create_user("admin", "secret")
        filepath = tmp_path / "users.txt"

        sync_users(self.db, str(filepath))

        assert filepath.exists()
        content = filepath.read_text()
        assert "admin:" in content

    def test_sync_overwrites_existing(self, tmp_path):
        filepath = tmp_path / "users.txt"
        filepath.write_text("stale data")

        self.svc.create_user("fresh", "pw")
        sync_users(self.db, str(filepath))

        content = filepath.read_text()
        assert "fresh:" in content
        assert "stale" not in content

    def test_sync_creates_parent_dirs(self, tmp_path):
        filepath = tmp_path / "nested" / "dir" / "users.txt"

        self.svc.create_user("admin", "pw")
        sync_users(self.db, str(filepath))

        assert filepath.exists()

    def test_username_with_special_characters(self):
        self.svc.create_user("user.name", "pw1")
        self.svc.create_user("user@domain", "pw2")

        content = generate_users_file(self.db)
        lines = content.strip().split("\n")

        assert len(lines) == 2
        usernames = {line.split(":")[0] for line in lines}
        assert usernames == {"user.name", "user@domain"}
        for line in lines:
            # bcrypt hashes contain $, so split on first : only
            parts = line.split(":", 1)
            assert len(parts) == 2
            assert parts[1].startswith("$2b$")
