"""Tests for the arm-auth CLI."""

import pytest
from click.testing import CliRunner

from arm_auth.cli import main


class TestInitCommand:
    def test_init_creates_db_and_admin(self, tmp_path):
        db_path = str(tmp_path / "auth.db")
        users_file = str(tmp_path / "users.txt")

        runner = CliRunner()
        result = runner.invoke(main, [
            "init",
            "--db-path", db_path,
            "--admin-password", "secret",
            "--users-file", users_file,
        ])

        assert result.exit_code == 0
        assert "Initialized" in result.output
        assert (tmp_path / "auth.db").exists()
        assert (tmp_path / "users.txt").exists()

        content = (tmp_path / "users.txt").read_text()
        assert "admin:" in content

    def test_init_idempotent(self, tmp_path):
        db_path = str(tmp_path / "auth.db")
        users_file = str(tmp_path / "users.txt")

        runner = CliRunner()
        runner.invoke(main, [
            "init", "--db-path", db_path,
            "--admin-password", "secret", "--users-file", users_file,
        ])
        result = runner.invoke(main, [
            "init", "--db-path", db_path,
            "--admin-password", "other", "--users-file", users_file,
        ])

        assert result.exit_code == 0
        assert "already exists" in result.output


class TestAddUserCommand:
    def test_add_user(self, tmp_path):
        db_path = str(tmp_path / "auth.db")
        users_file = str(tmp_path / "users.txt")

        runner = CliRunner()
        runner.invoke(main, [
            "init", "--db-path", db_path,
            "--admin-password", "secret", "--users-file", users_file,
        ])
        result = runner.invoke(main, [
            "add-user",
            "--db-path", db_path,
            "--username", "viewer",
            "--password", "viewpw",
            "--group", "user",
            "--users-file", users_file,
        ])

        assert result.exit_code == 0
        assert "Created user" in result.output

        content = (tmp_path / "users.txt").read_text()
        assert "admin:" in content
        assert "viewer:" in content

    def test_add_duplicate_user_fails(self, tmp_path):
        db_path = str(tmp_path / "auth.db")
        users_file = str(tmp_path / "users.txt")

        runner = CliRunner()
        runner.invoke(main, [
            "init", "--db-path", db_path,
            "--admin-password", "secret", "--users-file", users_file,
        ])
        result = runner.invoke(main, [
            "add-user", "--db-path", db_path,
            "--username", "admin", "--password", "pw",
            "--users-file", users_file,
        ])

        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_add_user_nonexistent_group(self, tmp_path):
        db_path = str(tmp_path / "auth.db")
        users_file = str(tmp_path / "users.txt")

        runner = CliRunner()
        runner.invoke(main, [
            "init", "--db-path", db_path,
            "--admin-password", "secret", "--users-file", users_file,
        ])
        result = runner.invoke(main, [
            "add-user", "--db-path", db_path,
            "--username", "newuser", "--password", "pw",
            "--group", "nonexistent",
            "--users-file", users_file,
        ])

        assert result.exit_code != 0
        assert "does not exist" in result.output
