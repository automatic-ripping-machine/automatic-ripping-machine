import os

import pytest

from backend.config import Settings


def test_transcoder_enabled_default_true(monkeypatch):
    monkeypatch.delenv("ARM_UI_TRANSCODER_ENABLED", raising=False)
    s = Settings()
    assert s.transcoder_enabled is True


def test_transcoder_enabled_false_from_env(monkeypatch):
    monkeypatch.setenv("ARM_UI_TRANSCODER_ENABLED", "false")
    s = Settings()
    assert s.transcoder_enabled is False


def test_transcoder_enabled_true_from_env(monkeypatch):
    monkeypatch.setenv("ARM_UI_TRANSCODER_ENABLED", "true")
    s = Settings()
    assert s.transcoder_enabled is True
