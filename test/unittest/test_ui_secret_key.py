"""Tests for the Flask SECRET_KEY generation (issue #1834)"""
import logging
import os
import stat

import pytest

import arm.ui

OLD_CONSTANT_KEY = "Big secret key"


@pytest.fixture
def secret_key(monkeypatch):
    """The secret_key module, with no ARM_SECRET_KEY override in the environment"""
    from arm.ui import secret_key as module
    monkeypatch.delenv(module.SECRET_KEY_ENV, raising=False)
    return module


def test_app_does_not_use_hard_coded_key():
    assert arm.ui.app.config['SECRET_KEY'] != OLD_CONSTANT_KEY
    assert len(arm.ui.app.config['SECRET_KEY']) >= 32


def test_debug_pin_not_hard_coded():
    assert os.environ.get("WERKZEUG_DEBUG_PIN") != "12345"


def test_key_is_persisted_and_reused(secret_key, tmp_path):
    first = secret_key.load_secret_key(str(tmp_path))
    second = secret_key.load_secret_key(str(tmp_path))

    assert first == second
    assert first != OLD_CONSTANT_KEY
    assert len(first) == 64
    key_file = tmp_path / secret_key.SECRET_KEY_FILENAME
    assert key_file.read_text() == first
    assert stat.S_IMODE(key_file.stat().st_mode) == 0o600


def test_existing_key_file_is_used(secret_key, tmp_path):
    (tmp_path / secret_key.SECRET_KEY_FILENAME).write_text("key-from-another-process\n")

    assert secret_key.load_secret_key(str(tmp_path)) == "key-from-another-process"


def test_env_override_wins(secret_key, tmp_path, monkeypatch):
    secret_key.load_secret_key(str(tmp_path))
    monkeypatch.setenv(secret_key.SECRET_KEY_ENV, "key-from-environment")

    assert secret_key.load_secret_key(str(tmp_path)) == "key-from-environment"


def test_missing_dir_falls_back_to_random_key(secret_key, tmp_path, caplog):
    missing = tmp_path / "does-not-exist"
    with caplog.at_level(logging.WARNING):
        first = secret_key.load_secret_key(str(missing))
        second = secret_key.load_secret_key(str(missing))

    assert first != OLD_CONSTANT_KEY
    assert len(first) == 64
    assert first != second
    assert not missing.exists()
    assert "temporary secret key" in caplog.text


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores directory permissions")
def test_unwritable_dir_falls_back_to_random_key(secret_key, tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        key = secret_key.load_secret_key(str(locked))
    finally:
        locked.chmod(0o700)

    assert key != OLD_CONSTANT_KEY
    assert len(key) == 64
    assert not (locked / secret_key.SECRET_KEY_FILENAME).exists()
