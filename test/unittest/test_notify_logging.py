"""Unconfigured notification services are a normal setup, not an error."""

import logging

import pytest


@pytest.fixture
def unconfigured(monkeypatch):
    import arm.config.config as cfg
    from arm.ripper import utils

    for key in ("PB_KEY", "IFTTT_KEY", "PO_USER_KEY", "JSON_URL", "APPRISE", "BASH_SCRIPT", "ARM_NAME"):
        monkeypatch.setitem(cfg.arm_config, key, "")
    monkeypatch.setattr(utils, "database_adder", lambda value: None)
    # The ripper's job log receives apprise's own records (that is where the error appeared).
    monkeypatch.setattr(logging.getLogger("apprise"), "disabled", False)
    return utils


def test_no_configured_services_logs_no_error(unconfigured, caplog):
    with caplog.at_level(logging.DEBUG):
        unconfigured.notify(None, "ARM notification", "Found disc: Hercules")
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


def test_configured_service_is_still_notified(unconfigured, monkeypatch):
    import apprise
    import arm.config.config as cfg

    sent = []
    monkeypatch.setitem(cfg.arm_config, "JSON_URL", "https://127.0.0.1:9/hook")
    monkeypatch.setattr(apprise.Apprise, "notify", lambda self, body, title=None: sent.append((title, body)))
    unconfigured.notify(None, "ARM notification", "Found disc")
    assert sent == [("ARM notification", "Found disc")]
